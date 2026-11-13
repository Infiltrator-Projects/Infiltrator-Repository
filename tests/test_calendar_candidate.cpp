// SPDX-License-Identifier: GPL-3.0-or-later
// Real APT policy regression against isolated, local file:// repositories.
// No host APT lists, package databases or installed software are modified.
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <pwd.h>
#include <stdexcept>
#include <string>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>
namespace fs=std::filesystem;
static void demand(bool yes,const std::string& why){
    if(!yes)throw std::runtime_error(why);
}
static void write(const fs::path& path,const std::string& content){
    fs::create_directories(path.parent_path());
    std::ofstream out(path,std::ios::binary|std::ios::trunc);
    demand(bool(out),"Cannot open fixture "+path.string());
    out<<content;out.close();
    demand(bool(out),"Cannot write fixture "+path.string());
}
static std::string read(const fs::path& path){
    std::ifstream in(path,std::ios::binary);
    demand(bool(in),"Cannot read fixture "+path.string());
    return {std::istreambuf_iterator<char>(in),std::istreambuf_iterator<char>()};
}
struct Temp{
    fs::path root;
    Temp(){
        auto pattern=(fs::temp_directory_path()/"infiltrator-calendar-apt-XXXXXXXX").string();
        std::vector<char> mutable_path(pattern.begin(),pattern.end());
        mutable_path.push_back('\0');
        char* made=mkdtemp(mutable_path.data());
        demand(made!=nullptr,"Cannot create isolated Calendar APT test root");
        root=made;
    }
    ~Temp(){std::error_code ec;if(!root.empty())fs::remove_all(root,ec);}
    Temp(const Temp&)=delete;
    Temp& operator=(const Temp&)=delete;
};
static std::string command(const std::vector<std::string>& cmd){
    demand(!cmd.empty(),"Empty APT test command");
    int pipes[2];
    demand(pipe(pipes)==0,"Cannot create APT capture pipe");
    const auto child=fork();
    if(child<0){close(pipes[0]);close(pipes[1]);throw std::runtime_error("Cannot fork APT");}
    if(child==0){
        close(pipes[0]);
        if(dup2(pipes[1],STDOUT_FILENO)<0)_exit(127);
        close(pipes[1]);
        std::vector<char*> argv;
        for(const auto& a:cmd)argv.push_back(const_cast<char*>(a.c_str()));
        argv.push_back(nullptr);
        execvp(argv[0],argv.data());
        _exit(127);
    }
    close(pipes[1]);
    std::string output;
    char buf[8192];
    while(true){
        const auto n=::read(pipes[0],buf,sizeof(buf));
        if(n==0)break;
        if(n<0){
            if(errno==EINTR)continue;
            close(pipes[0]);
            throw std::runtime_error("APT capture pipe failed");
        }
        demand(output.size()+std::size_t(n)<1024*1024,
               "APT fixture output exceeds memory bound");
        output.append(buf,std::size_t(n));
    }
    close(pipes[0]);
    int status=0;
    while(waitpid(child,&status,0)<0){
        if(errno==EINTR)continue;
        throw std::runtime_error("Cannot reap APT child");
    }
    demand(WIFEXITED(status)&&WEXITSTATUS(status)==0,
           "APT subprocess failed: "+cmd.front()+"\n"+output);
    return output;
}
static std::string trim(const std::string& s){
    const auto start=s.find_first_not_of(" \t\r\n");
    if(start==std::string::npos)return {};
    return s.substr(start,s.find_last_not_of(" \t\r\n")-start+1);
}
static std::string digest(const fs::path& file){
    const auto output=command({"sha256sum","--",file.string()});
    demand(output.size()>=66&&output[64]==' ',"Missing sha256sum output");
    const auto hex=output.substr(0,64);
    for(unsigned char ch:hex)
        demand((ch>='0'&&ch<='9')||(ch>='a'&&ch<='f'),
               "Invalid SHA-256 digest");
    return hex;
}
static std::string archive(const fs::path& root,const std::string& name,
                           const std::string& origin,const std::string& version){
    const auto dir=root/name;
    const auto binary=dir/"dists/beta/main/binary-amd64";
    const auto packages="Package: calendar\nArchitecture: amd64\nVersion: "+version+
        "\nMaintainer: Fixture <test@example.invalid>\nFilename: pool/calendar_"+
        version+"_amd64.deb\nSize: 1\nDescription: resolver fixture\n\n";
    const auto path=binary/"Packages";
    write(path,packages);
    write(dir/"dists/beta/Release",
          "Origin: "+origin+"\nLabel: "+origin+
          "\nSuite: beta\nCodename: beta\nArchitectures: amd64\n"
          "Components: main\nSHA256:\n "+digest(path)+" "+
          std::to_string(packages.size())+" main/binary-amd64/Packages\n");
    return "deb [trusted=yes arch=amd64] file://"+dir.generic_string()+" beta main\n";
}
int main(int argc,char**argv){
    try{
        demand(argc<=2,"Usage: test-calendar-candidate [REPOSITORY_ROOT]");
        const auto source=fs::absolute(argc==2?argv[1]:".");
        const auto preference=source/"site/infiltrator-calendar.pref";
        demand(fs::is_regular_file(preference),"Canonical Calendar APT pin is absent");
        Temp t;
        const auto apt=t.root/"apt";
        for(const auto& path:{"etc/apt/preferences.d","var/lib/dpkg",
                              "var/lib/apt/lists/partial",
                              "var/cache/apt/archives/partial"})
            fs::create_directories(apt/path);
        const auto status=apt/"var/lib/dpkg/status";
        const auto sources=apt/"etc/apt/sources.list";
        write(status,"");
        write(sources,archive(t.root,"mint","Ubuntu","12.1.8")+
                      archive(t.root,"infiltrator","Infiltrator","1.0.116"));
        auto* user=getpwuid(getuid());
        demand(user&&user->pw_name,"Cannot identify current APT test user");
        const std::vector<std::string> options={
            "-o","Dir="+apt.string(),
            "-o","Dir::Etc::sourcelist="+sources.string(),
            "-o","Dir::Etc::sourceparts=-",
            "-o","Dir::Etc::preferences="+(apt/"etc/apt/preferences").string(),
            "-o","Dir::Etc::preferencesparts="+(apt/"etc/apt/preferences.d").string(),
            "-o","Dir::State::status="+status.string(),
            "-o","Dir::Cache::pkgcache=",
            "-o","Dir::Cache::srcpkgcache=",
            "-o","Debug::NoLocking=true",
            "-o","APT::Sandbox::User="+std::string(user->pw_name),
            "-o","Acquire::Languages=none"
        };
        auto make_command=[&](const std::string& program,const std::vector<std::string>& tail){
            std::vector<std::string> result{program};
            result.insert(result.end(),options.begin(),options.end());
            result.insert(result.end(),tail.begin(),tail.end());
            return result;
        };
        command(make_command("/usr/bin/apt-get",{"update"}));
        const auto candidate=[&](){
            const auto policy=command(make_command("/usr/bin/apt-cache",{"policy","calendar"}));
            const auto key=policy.find("Candidate:");
            demand(key!=std::string::npos,"APT policy emitted no candidate");
            const auto end=policy.find('\n',key);
            return trim(policy.substr(key+10,end==std::string::npos?
                                            std::string::npos:end-key-10));
        };
        demand(candidate()=="12.1.8","Mint collision was not reproduced");
        fs::copy_file(preference,apt/"etc/apt/preferences.d/infiltrator-calendar",
                      fs::copy_options::none);
        demand(candidate()=="1.0.116",
               "Infiltrator Calendar pin does not select the approved version");
        for(const auto& installed:{"12.1.8","1.0.116+nativepgo1"}){
            write(status,"Package: calendar\nStatus: install ok installed\n"
                         "Architecture: amd64\nVersion: "+std::string(installed)+
                         "\nMaintainer: Fixture <test@example.invalid>\n"
                         "Description: installed calendar\n\n");
            demand(candidate()==installed,
                   "APT pin replaced deliberately installed newer/local Calendar: "+
                   std::string(installed));
        }
        demand(!fs::exists(source/"tests/test_calendar_candidate.py"),
               "Retired Python Calendar APT test returned");
        std::cout<<"APT selects Infiltrator Calendar without replacing newer installed versions (C++17)\n";
        return 0;
    }catch(const std::exception& error){
        std::cerr<<"Native APT Calendar candidate regression failed: "<<error.what()<<'\n';
        return 1;
    }
}
