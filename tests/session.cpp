#include "session.hpp"
#include <filesystem>
#include <iostream>
void require(bool b,char const* m){if(!b)throw std::runtime_error(m);}
int main(int argc,char**argv){try{
 if(argc!=2)return 2;std::string dir=argv[1];std::filesystem::create_directories(dir);z3::context c;auto x=c.int_const("x"),aux=c.int_const("__guided_aux");auto f=x>=0;
 {
  guided::Session s(c,10,2,dir);s.load(f,0);std::ofstream out(dir+"/samples.raw");
  auto model=[&](int a,int b){z3::model m(c);auto xd=x.decl(),ad=aux.decl();auto av=c.int_val(a),bv=c.int_val(b);m.add_const_interp(xd,av);m.add_const_interp(ad,bv);return m;};
  require(s.commit(model(1,0),f,out),"first model missing");require(!s.commit(model(1,1),f,out),"auxiliary polluted identity");require(s.formal==1,"duplicate count");require(s.commit(model(2,0),f,out),"second model missing");require(!s.commit(model(3,0),f,out),"count cap exceeded");require(s.formal==2,"incorrect cap");s.finish();
 }
 auto late=dir+"/late";std::filesystem::create_directory(late);
 {
  guided::Session s(c,0,std::nullopt,late);s.load(f,0);z3::model m(c);auto xd=x.decl();auto v=c.int_val(0);m.add_const_interp(xd,v);std::ofstream out(late+"/samples.raw");require(!s.commit(m,f,out),"late sample committed");s.finish();
 }
 std::cout<<"{\"passed\":true,\"auxiliary_projection\":true,\"count_cap\":true,\"late_rejection\":true}\n";
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
