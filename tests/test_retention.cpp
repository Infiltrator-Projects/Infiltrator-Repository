// SPDX-License-Identifier: GPL-3.0-or-later
// Read-only host policy, destructive only inside a disposable fixture tree.
// Verify real DEB fixtures against the production native APT publisher.
#include <array>
#include <cerrno>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
namespace fs=std::filesystem;
static void demand(bool ok,const std::string& reason){
    if(!ok)throw std::runtime_error(reason);
}
static void save(const fs::path& path,const std::string& contents){
    fs::create_directories(path.parent_path());
    std::ofstream f(path,std::ios::binary|std::ios::trunc);
    demand(bool(f),"Cannot write "+path.string());
    f<<contents;f.close();
    demand(bool(f),"Incomplete fixture "+path.string());
}
static std::string contents(const fs::path& path){
    std::ifstream f(path,std::ios::binary);
    demand(bool(f),"Cannot read "+path.string());
    return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};
}
struct Disposable{
    fs::path root;
    Disposable(){
        auto pattern=(fs::temp_directory_path()/"infiltrator-retention-XXXXXXXX").string();
        std::vector<char> data(pattern.begin(),pattern.end());data.push_back(0);
        const char* made=mkdtemp(data.data());
        demand(made!=nullptr,"Cannot create test fixture root");
        root=made;
    }
    ~Disposable(){std::error_code error;if(!root.empty())fs::remove_all(root,error);}
    Disposable(const Disposable&)=delete;
    Disposable& operator=(const Disposable&)=delete;
};
struct Result{int code;std::string output;};
static Result run(const std::vector<std::string>& command,const fs::path& cwd={},
                  bool no_signing=false){
    demand(!command.empty(),"Empty fixture command");
    int pipes[2];
    demand(pipe(pipes)==0,"Cannot open command output pipe");
    const auto pid=fork();
    if(pid<0){close(pipes[0]);close(pipes[1]);throw std::runtime_error("fork failed");}
    if(pid==0){
        close(pipes[0]);
        if(!cwd.empty()&&chdir(cwd.c_str())!=0)_exit(127);
        if(no_signing){
            unsetenv("APT_SIGNING_KEY_B64");
            unsetenv("APT_SIGNING_KEY_FINGERPRINT");
            unsetenv("APT_SIGNING_PASSPHRASE");
            if(setenv("REPOSITORY_ROOT",cwd.c_str(),1)!=0)_exit(127);
        }
        if(dup2(pipes[1],STDOUT_FILENO)<0)_exit(127);
        close(pipes[1]);
        std::vector<char*> args;
        for(const auto& s:command)args.push_back(const_cast<char*>(s.c_str()));
        args.push_back(nullptr);
        execvp(args[0],args.data());
        _exit(127);
    }
    close(pipes[1]);
    std::array<char,32768> buffer{};
    std::string output;
    bool error=false;
    while(true){
        const auto n=::read(pipes[0],buffer.data(),buffer.size());
        if(n==0)break;
        if(n<0){if(errno==EINTR)continue;error=true;break;}
        if(output.size()+std::size_t(n)>8*1024*1024){error=true;break;}
        output.append(buffer.data(),std::size_t(n));
    }
    close(pipes[0]);
    int status=0;
    while(waitpid(pid,&status,0)<0){
        if(errno==EINTR)continue;
        throw std::runtime_error("waitpid failed");
    }
    demand(!error,"Fixture process output limit exceeded");
    return {WIFEXITED(status)?WEXITSTATUS(status):128+WTERMSIG(status),output};
}
static std::size_t occurrences(const std::string& data,const std::string& token){
    std::size_t count=0,offset=0;
    while((offset=data.find(token,offset))!=std::string::npos){
        ++count;offset+=token.size();
    }
    return count;
}
int main(int argc,char**argv){
    try{
        demand(argc==2,"Usage: test-retention PATH_TO_REPOSITORY_TOOL");
        const auto publisher=fs::absolute(argv[1]);
        demand(fs::is_regular_file(publisher),"Native publisher executable missing");
        Disposable test;
        const auto root=test.root,mirrors=root/"mirrors";
        save(root/"site/index.html","<!doctype html><title>fixture</title>\n");
        fs::create_directories(mirrors);
        const std::vector<std::string> versions={"1.1","1.2","1.3","1.4","1.5","1.9","1.10"};
        for(const auto& version:versions){
            const auto stage=root/("build-"+version);
            save(stage/"DEBIAN/control",
                "Package: retention-test\nVersion: "+version+
                "\nArchitecture: amd64\nMaintainer: Test <test@example.invalid>\n"
                "Description: retention fixture\n");
            auto produced=run({"dpkg-deb","--build","--root-owner-group",
                stage.string(),(mirrors/("retention-test_"+version+"_amd64.deb")).string()});
            demand(produced.code==0,"Cannot build retention fixture version "+version);
        }
        save(root/"catalogue/apps-source.json",
            R"JSON([{"id":"retention-test","name":"Retention Test","repo":"retention-test","category":"Test","description":"C++ retention fixture.","local_deb_glob":"mirrors/*.deb","icon":"test","expected_package_regex":"^retention-test$","expected_architecture":"amd64"}])JSON");
        const auto result=run({publisher.string(),"publish"},root,true);
        demand(result.code==0,"Native publisher rejected independent retention fixture");
        const auto apps=root/"public/catalogue/apps.json";
        const auto latest=run({"jq","-r",
            R"JQ(.[] | select(.id=="retention-test") | .version)JQ",apps.string()});
        demand(latest.code==0&&latest.output=="1.10\n",
               "Publisher did not select Debian version 1.10");
        const auto history=run({"jq","-r",
            R"JQ(.[] | select(.id=="retention-test") | .history[].version)JQ",apps.string()});
        demand(history.code==0&&history.output=="1.10\n1.9\n1.5\n1.4\n1.3\n",
               "Publisher did not retain newest five versions in Debian order");
        std::set<std::string> kept;
        for(const auto& entry:fs::directory_iterator(root/"public/pool/main")){
            if(!entry.is_regular_file()||entry.path().extension()!=".deb")continue;
            const auto version=run({"dpkg-deb","-f",entry.path().string(),"Version"});
            demand(version.code==0,"Cannot inspect retained DEB");
            std::string v=version.output;
            while(!v.empty()&&(v.back()=='\n'||v.back()=='\r'))v.pop_back();
            kept.insert(v);
        }
        demand(kept==std::set<std::string>{"1.10","1.9","1.5","1.4","1.3"},
               "Published pool is missing or retaining wrong versions");
        std::size_t source_count=0;
        for(const auto& entry:fs::directory_iterator(mirrors))
            if(entry.is_regular_file()&&entry.path().extension()==".deb")++source_count;
        demand(source_count==7,"Publisher changed the seven source packages");
        for(const auto& suite:{std::pair{"alpha","Alpha"},std::pair{"beta","Beta"}}){
            const auto packages=contents(root/"public/dists"/suite.first/"main/binary-amd64/Packages");
            demand(occurrences(packages,"Package: retention-test\n")==5,
                   "Published "+std::string(suite.first)+" index lost retained packages");
            const auto release=contents(root/"public/dists"/suite.first/"Release");
            demand(release.find("Label: Infiltrator "+std::string(suite.second)+"\n")!=
                   std::string::npos,"Incorrect APT release label");
        }
        demand(!fs::exists(root/"public/dists/stable"),"Stable is reserved, not an alias");
        std::cout<<"PASS: native publisher keeps five versions in alpha/beta; stable reserved\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"Native package retention test failed: "<<e.what()<<'\n';
        return 1;
    }
}
