#include "session.hpp"
#include <filesystem>
#include <iostream>
#define REQUIRE(x) do{if(!(x))throw std::runtime_error(#x);}while(false)
int main(int argc,char** argv){REQUIRE(argc==2);std::string root=argv[1];std::filesystem::create_directories(root);setenv("REFINEMENT_MODE","off",1);
    for(auto name:{"completion","io_failure","cancelled","late"}){
        guided::interrupted=0;std::string dir=root+"/"+name;std::filesystem::create_directories(dir);z3::context c;auto x=c.int_const("x");auto b=c.bool_const("b");auto f=(c.bool_val(true)||(x==1))&&(c.bool_val(true)||b);guided::Session s(c,60,std::nullopt,dir);s.load(f,0);s.done=true;s.watchdog.join();if(std::string(name)=="late")s.wall=0;z3::model m(c);
        std::ofstream raw;if(std::string(name)!="io_failure")raw.open(dir+"/samples.raw");if(std::string(name)=="cancelled")guided::interrupted=1;
        bool failed=false;try{s.commit(m,f,raw);}catch(std::runtime_error const&){failed=true;}REQUIRE(failed==(std::string(name)=="io_failure"));REQUIRE(s.split->native.accepted_count==1);REQUIRE(s.formal==(std::string(name)=="completion"?1:0));REQUIRE(m.size()==0);s.finish();
    }guided::interrupted=0;std::cout<<"PASS independent undefined-variable completion, I/O failure, cancellation, late-ready ledgers\n";
}
