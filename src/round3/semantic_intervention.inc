// D3 ONLY: installed exclusively in a separate diagnostic library.
// No fork. Each process reconstructs F + original assumptions and coverage,
// explicitly same_query_not_same_state. No additional logical assertion.
namespace d3 {
struct State {bool enabled=false,fired=false,handoff=false;std::string cell;a2::Json spec;State(){auto p=std::getenv("GUIDED_D3_CASE");auto c=std::getenv("GUIDED_D3_CELL");if(p&&c){std::ifstream f(p);f>>spec;cell=c;enabled=true;if(cell!="N0"&&cell!="A0"&&cell!="N1"&&cell!="A1")throw std::runtime_error("invalid D3 cell");}}};
inline State& state(){static thread_local State s;return s;}
inline uint64_t trace_size(char const* key){auto p=std::getenv(key);if(!p)return 0;std::ifstream f(p,std::ios::binary|std::ios::ate);return f?static_cast<uint64_t>(f.tellg()):0;}
inline unsigned task_count(){unsigned n=0;if(auto* d=::opendir("/proc/self/task")){while(auto* e=::readdir(d))if(e->d_name[0]!='.')++n;::closedir(d);}return n;}
}
