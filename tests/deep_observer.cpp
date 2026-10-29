#include "observation.hpp"
#include <iostream>
int main(){try {
 z3::context c;auto x=c.int_const("x"),e=x;
 for(unsigned i=0;i<3000;++i)e=e+c.int_val(1);
 guided::OriginalAst ast(e==3000);auto ev=ast.evaluate({{"x",0}});
 if(!ev.values[0]||*ev.values[0]!=1||ast.nodes.size()<3000)throw std::runtime_error("deep evaluation failed");
 ast.commit(ev);auto win=ast.select_window();if(win.empty())throw std::runtime_error("missing demands");
 // Shared DAG exact arithmetic, beyond any machine integer.
 auto huge=c.int_val("1208925819614629174706179");guided::OriginalAst large(x*huge==x*huge);auto v=large.evaluate({{"x",guided::Big(-1)}});large.commit(v);
 std::cout<<guided::Json({{"passed",true},{"deep_nodes",ast.nodes.size()},{"covered",ast.covered},{"observed",ast.observed}}).dump()<<'\n';
 return 0;
}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
