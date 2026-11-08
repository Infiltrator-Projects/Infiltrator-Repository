// SPDX-License-Identifier: GPL-3.0-or-later
// Repository publication and Software Centre presentation regression contracts.
// The native test is deliberately read-only. It does not run APT or publish.
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <initializer_list>
namespace fs=std::filesystem;

static void check(bool condition,const std::string& detail) {
    if(!condition)throw std::runtime_error(detail);
}
static std::string read(const fs::path& path) {
    std::ifstream file(path,std::ios::binary);
    check(bool(file),"unable to read "+path.string());
    return {std::istreambuf_iterator<char>(file),std::istreambuf_iterator<char>()};
}
static bool has(const std::string& text,const std::string& needle) {
    return text.find(needle)!=std::string::npos;
}
static void require(const std::string& text,const std::string& needle,
                    const char* contract) {
    check(has(text,needle),std::string(contract)+" missing: "+needle);
}
static void reject(const std::string& text,const std::string& needle,
                   const char* contract) {
    check(!has(text,needle),std::string(contract)+" contains forbidden: "+needle);
}
static void publication_contract(const fs::path& root) {
    const std::string wf=read(root/".github/workflows/publish.yml");
    const char* contract="Publication concurrency";
    for(const char* needle:{
        "group: pages",
        "cancel-in-progress: false",
        "on:\n  push:\n    branches: [main]\n",
        "  workflow_dispatch:\n",
        "repository_dispatch:",
        "types: [application-release]",
        "cron: '*/5 * * * *'",
        "expected_marker=\"$(sed -n",
        "site/index.html)",
        "grep -Fq \"$expected_marker\""
    })require(wf,needle,contract);
    for(const char* needle:{
        "cancel-in-progress: true",
        "/dispatches",
        "cron: '2-57/5 * * * *'",
        "mb-corpo-card-type-v1"
    })reject(wf,needle,contract);
    const auto a=wf.find("name: Publish Beta Repository");
    check(a!=std::string::npos,"publication workflow identity missing");
    const auto b=wf.find("concurrency:",a);
    check(b!=std::string::npos,"publication serialization missing");
    const auto c=wf.find("cancel-in-progress: false",b);
    check(c!=std::string::npos&&a<b&&b<c,"publication concurrency configuration altered");
    std::cout<<"Repository publication concurrency contract passed\n";
}
static void private_mirror_contract(const fs::path& root) {
    const std::string catalog=read(root/"catalogue/apps-source.json");
    const std::string identity=R"JSON("id": "intune-zabbix-bridge")JSON";
    const auto match=catalog.find(identity);
    check(match!=std::string::npos,"Intune-Zabbix-Bridge catalogue identity missing");
    const auto begin=catalog.rfind('{',match),end=catalog.find('}',match);
    check(begin!=std::string::npos&&end!=std::string::npos&&begin<match,
          "Intune-Zabbix-Bridge catalogue entry malformed");
    const std::string item=catalog.substr(begin,end+1-begin);
    require(item,R"JSON("local_deb_glob": "mirrored-packages/intune-zabbix-bridge_*_all.deb")JSON",
            "Version-dynamic private mirror");
    for(const char* obsolete:{
        R"JSON("local_deb")JSON",
        R"JSON("release_tag")JSON",
        R"JSON("published_at")JSON"
    })reject(item,obsolete,"Version-dynamic private mirror");
    const std::string tool=read(root/"scripts/repository-tool.cpp");
    for(const char* required_token:{
        R"CPP((.local_deb_glob // \"\"))CPP",
        "dpkg --compare-versions",
        "if (result.size() > 5) result.resize(5);",
        "https://infiltrator-projects.github.io/Infiltrator-Repository/pool/main/",
        "GITHUB_TOKEN",
        "#include <infiltratr/escape.h>",
        "#include <infiltratr/posix.h>",
        "infiltratr_escape_json",
        "infiltratr_escape_uri_component",
        "infiltratr_atomic_file_write_bytes"
    })require(tool,required_token,"Native private mirror publisher");
    reject(tool,"std::uppercase","Private mirror URI escaping must be COMMON-owned");
    std::cout<<"Private mirror publication policy is version-dynamic and COMMON-backed.\n";
}
static void site_setup_contract(const fs::path& root) {
    const std::string site=read(root/"site/index.html");
    const auto a=site.find("function setupCommand()");
    check(a!=std::string::npos,"Software Centre setupCommand missing");
    const auto b=site.find("function updateRepoInfo()",a);
    check(b!=std::string::npos,"Software Centre updateRepoInfo missing");
    const std::string block=site.substr(a,b-a);
    const char* contract="Software Centre setup";
    reject(block,R"JS(\\n)JS",contract);
    for(const char* needle:{
        R"JS(infiltrator-beta.list\n)JS",
        R"JS(infiltrator.list\n)JS",
        "sudo apt update",
        "/infiltrator-calendar.pref",
        "return clean+preference+",
        "sudo rm -f /var/cache/mintinstall/pkginfo.json",
        "mintinstall/pkginfo.json",
        R"JS(\#"+base+"#d)JS",
        "if(!repoReady||!repoInfo)return",
    })require(block,needle,contract);
    for(const char* needle:{
        "s# alpha main# beta main#g",
        "s# stable main# beta main#g",
    })reject(block,needle,contract);
    for(const char* needle:{
        R"JS(var cmd="sudo apt install "+a.package+"="+a.version;)JS",
        R"JS(var base="https://infiltrator-projects.github.io/Infiltrator-Repository";)JS",
        "assets/infiltrator-web-v1.css?v=common-1.19.42",
        "assets/site.css?v=family-20261016-refined",
        "assets/site-overrides.css?v=family-20261016-refined",
        R"JS(id="copyRepo" disabled)JS",
        R"JS(aria-labelledby="modalName")JS",
        R"JS(setAttribute("aria-pressed")JS",
        "Repository configuration could not be verified. Setup copying is disabled.",
        "function appIcon(a)",
        "a.icon_url",
        R"JS(function isAutomotive(a){return a.category==="Automotive";})JS",
        "return isAutomotive(a)&&a.icon_url?",
        ":iconSvg(a.icon);}",
        "software:",
        "font:400 30px/1.15 var(--display)",
        "calculator:",
        "var visible=apps.filter(matches).sort(compareApps);",
        "function compareApps(a,b){return compareLabels(a.name,b.name)",
        R"JS(var categoryOrder=["System","Productivity","Filesystems","Development","Automotive","Infrastructure","Games"];)JS",
        ".sort(compareCategories)",
        "if(ai<0)ai=categoryOrder.length;",
        "if(bi<0)bi=categoryOrder.length;"
    })require(site,needle,contract);
    for(const char* needle:{
        "activeCategory=cat;buildFilters()",
        R"JS("raster-card")JS",
        R"JS("raster-dialog")JS",
        R"JS("Cascadia Mono")JS",
        R"JS("DejaVu Sans Mono")JS",
        R"JS("Liberation Mono")JS",
        ":appIcon(a);}"
    })reject(site,needle,contract);
    const std::string preference=read(root/"site/infiltrator-calendar.pref");
    for(const char* needle:{
        "Package: calendar\n",
        "Pin: release o=Infiltrator\n",
        "Pin-Priority: 999\n"
    })require(preference,needle,"APT Calendar preference");
    std::cout<<"Software Centre setup, accessibility and family-source regression tests passed\n";
}
int main(int argc,char**argv){
    try{
        check(argc<=2,"Usage: native-source-contracts [REPOSITORY_ROOT]");
        const fs::path root=argc==2?fs::path(argv[1]):fs::path(".");
        publication_contract(root);
        private_mirror_contract(root);
        site_setup_contract(root);
        for(const char* retired:{"tests/test_publish_workflow.py","tests/test_site_setup.py",
                                 "tests/test_private_mirror_policy.py"})
            check(!fs::exists(root/retired),std::string("Retired Python regression still tracked: ")+retired);
        return 0;
    }catch(const std::exception&error){
        std::cerr<<"Repository native source contract failed: "<<error.what()<<'\n';
        return 1;
    }
}
