// SPDX-License-Identifier: GPL-3.0-or-later
// Verify the production DEB identity validator using disposable real .deb
// fixtures. Nothing in the host's installed package database is modified.
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
namespace fs=std::filesystem;

static void require(bool ok,const std::string& explanation){
    if(!ok)throw std::runtime_error(explanation);
}
static int execute(const std::vector<std::string>& command,
                   std::chrono::seconds timeout=std::chrono::seconds(30)){
    require(!command.empty(),"empty subprocess");
    const pid_t child=fork();
    require(child>=0,"failed to fork fixture subprocess");
    if(child==0){
        const int nullfd=open("/dev/null",O_RDWR|O_CLOEXEC);
        if(nullfd<0)_exit(127);
        if(dup2(nullfd,STDOUT_FILENO)<0||dup2(nullfd,STDERR_FILENO)<0)
            _exit(127);
        if(nullfd>STDERR_FILENO)close(nullfd);
        std::vector<char*> argv;
        for(const auto& part:command)argv.push_back(const_cast<char*>(part.c_str()));
        argv.push_back(nullptr);
        execvp(argv[0],argv.data());
        _exit(127);
    }
    const auto deadline=std::chrono::steady_clock::now()+timeout;
    int status=0;
    while(true){
        const pid_t completed=waitpid(child,&status,WNOHANG);
        if(completed==child)break;
        if(completed<0){
            if(errno==EINTR)continue;
            kill(child,SIGKILL);
            while(waitpid(child,&status,0)<0&&errno==EINTR){}
            throw std::runtime_error("waitpid failed");
        }
        if(std::chrono::steady_clock::now()>=deadline){
            kill(child,SIGKILL);
            while(waitpid(child,&status,0)<0&&errno==EINTR){}
            throw std::runtime_error("fixture subprocess timed out: "+command.front());
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
    require(WIFEXITED(status),"fixture subprocess was terminated by a signal");
    return WEXITSTATUS(status);
}
struct FixtureDirectory{
    fs::path root;
    FixtureDirectory(){
        std::string name=(fs::temp_directory_path()/"infiltrator-release-identity-XXXXXX").string();
        std::vector<char> path(name.begin(),name.end());
        path.push_back('\0');
        char* made=mkdtemp(path.data());
        require(made!=nullptr,"could not make disposable Debian fixture directory");
        root=made;
    }
    ~FixtureDirectory(){
        std::error_code error;
        if(!root.empty())fs::remove_all(root,error);
    }
    FixtureDirectory(const FixtureDirectory&)=delete;
    FixtureDirectory& operator=(const FixtureDirectory&)=delete;
};
static fs::path build(const FixtureDirectory& fixture,
                      const std::string& name,const std::string& version,
                      const std::string& architecture){
    const fs::path stage=fixture.root/(name+"-"+version+"-"+architecture);
    fs::create_directories(stage/"DEBIAN");
    std::ofstream control(stage/"DEBIAN/control",std::ios::binary|std::ios::trunc);
    require(bool(control),"cannot create Debian control fixture");
    control<<"Package: "<<name<<"\nVersion: "<<version
           <<"\nArchitecture: "<<architecture
           <<"\nMaintainer: CI <ci@example.invalid>\n"
           <<"Description: identity fixture\n";
    control.close();
    require(bool(control),"cannot write Debian control fixture");
    const fs::path output=fixture.root/(name+"_"+version+"_"+architecture+".deb");
    require(execute({"dpkg-deb","--build","--root-owner-group",stage.string(),output.string()})==0,
            "dpkg-deb could not build "+output.filename().string());
    require(fs::is_regular_file(output)&&fs::file_size(output)>0,
            "Debian fixture did not produce a package");
    return output;
}
static void expected(const std::string& description,int actual,bool should_succeed){
    require((actual==0)==should_succeed,
            description+(should_succeed?" was rejected unexpectedly":" was accepted unexpectedly"));
}
int main(int argc,char**argv){
    try{
        require(argc==2,"Usage: test-release-identity PATH_TO_NATIVE_REPOSITORY_TOOL");
        const fs::path tool=fs::absolute(argv[1]);
        require(fs::is_regular_file(tool)&&access(tool.c_str(),X_OK)==0,
                "compiled native repository tool is missing");
        FixtureDirectory fixture;
        const auto good=build(fixture,"expected-app","1.0","amd64");
        const auto wrong_name=build(fixture,"wrong-app","1.0","amd64");
        const auto wrong_version=build(fixture,"expected-app","9.9","amd64");
        const auto wrong_arch=build(fixture,"expected-app","1.0","all");
        const auto validate=[&](const fs::path& package) {
            return execute({tool.string(),"validate-deb",package.string(),
                            "v1.0","^expected-app$","amd64"});
        };
        expected("valid package identity",validate(good),true);
        expected("incorrect package name",validate(wrong_name),false);
        expected("incorrect package version",validate(wrong_version),false);
        expected("incorrect package architecture",validate(wrong_arch),false);
        const auto component=build(fixture,"runtime-component",
                                   "3.1.1-1ubuntu0.1+infiltratorfs1","amd64");
        const auto validate_component=[&](const std::string& filename){
            return execute({tool.string(),"validate-deb",component.string(),
                            "v0.18.65","^runtime-component$","amd64",
                            filename,R"(^runtime-component_([^_]+)_amd64\.deb$)"});
        };
        expected("valid bundled component",
            validate_component("runtime-component_3.1.1-1ubuntu0.1+infiltratorfs1_amd64.deb"),true);
        expected("incorrect bundled component identity",
            validate_component("runtime-component_wrong_amd64.deb"),false);
        std::cout<<"Independent release/package and bundled-asset identity validation passed\n";
        return 0;
    }catch(const std::exception& error){
        std::cerr<<"Native package-identity regression failed: "<<error.what()<<'\n';
        return 1;
    }
}
