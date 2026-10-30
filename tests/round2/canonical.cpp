#include "a_host_view.hpp"
#include <cassert>
#include <iostream>
a2::Norm norm(z3::expr const& e){a2::Work w;w.deadline=a2::Clock::now()+std::chrono::seconds(5);auto n=a2::canonical(a2::HostView{},e,w);assert(n.complete);return n;}
int main(){z3::context c;auto x=c.int_const("x"),y=c.int_const("y");auto p=c.bool_const("p");
 auto equal=[&](z3::expr a,z3::expr b){auto na=norm(a),nb=norm(b);assert(na.key==nb.key&&na.negated==nb.negated);z3::solver s(c);s.add(a!=b);assert(s.check()==z3::unsat);};
 equal(x==10,10==x);equal(x==10,x-10==0);equal(x==10,2*x==20);equal(x>2,x>=3);equal(!(x<=2),x>=3);equal(x<2,x<=1);equal(!(!p),p);equal(x==-100,x+100==0);equal(x-y==3,3+y==x);
 auto big=c.int_val("18446744073709551617");equal(x==big,x-big==0);
 assert(norm(x==10).key!=norm(x>=10).key);assert(norm(x==10).key!=norm(y==10).key);
 auto a=norm(x<=2),b=norm(x>2);assert(a.key==b.key&&a.negated!=b.negated);
 a2::Work limited;limited.limit=1;assert(!a2::canonical(a2::HostView{},x+y==3,limited).complete);
 std::cout<<"Canonical exactness, sign, strictness, variable identity and incomplete-work tests passed\n";
}
