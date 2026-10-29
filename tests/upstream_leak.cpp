// Independent native-Z3 reproducer: no guidance headers or guidance API calls.
#include <z3++.h>
#include <iostream>
int main(int argc,char**argv){z3::context c;z3::solver s(c);auto x=c.int_const("x");bool large=argc>1;
 auto p=c.int_val(large?"18446744073709551616":"16");auto h=c.int_val(large?"9223372036854775808":"8");
 s.add(x>=-20&&x<=20);s.add(z3::mod(x,p)>=h);
 z3::expr_vector a(c);a.push_back(x>=-20);auto r=s.check(a);std::cout<<r<<'\n';return r==z3::sat?0:1;}
