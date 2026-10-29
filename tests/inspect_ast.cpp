#include "observation.hpp"
#include <iostream>
int main(int argc,char**argv){try {for(int i=1;i<argc;++i){z3::context c;auto f=c.parse_file(argv[i]);guided::OriginalAst a(z3::mk_and(f));std::cout<<guided::Json({{"path",argv[i]},{"nodes",a.nodes.size()},{"variables",a.vars.size()},{"total",a.total}}).dump()<<'\n';}return 0;}catch(std::exception const& e){std::cerr<<e.what()<<'\n';return 1;}}
