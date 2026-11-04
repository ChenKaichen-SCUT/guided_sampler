#pragma once
#include <z3++.h>
#include <boost/multiprecision/cpp_int.hpp>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <cstdint>
#include <map>
#include <memory>
#include <set>
#include <unordered_map>
#include <vector>
#include <stdexcept>

namespace esg {
using Int=boost::multiprecision::cpp_int;
using Json=nlohmann::json;
inline std::string decimal(Int const& v){return v.convert_to<std::string>();}
inline Int parse_integer(std::string s){
    if(s.size()>3&&s.substr(0,2)=="(-"){
        s=s.substr(2,s.size()-3);s.erase(std::remove(s.begin(),s.end(),' '),s.end());return -Int(s);
    }
    return Int(s);
}
inline uint64_t low64(Int const& v){Int p=Int(1)<<64;Int r=v%p;if(r<0)r+=p;return r.convert_to<uint64_t>();}
inline unsigned pop(uint64_t x){return __builtin_popcountll(x);}
struct Node {
    z3::expr expr;
    std::vector<unsigned> children;
    unsigned kind;
    bool boolean, constant, symbol;
    std::string name;
    uint64_t seen0=0,seen1=0;
    explicit Node(z3::expr e):expr(e),kind(e.decl().decl_kind()),boolean(e.is_bool()),
        constant(e.is_numeral()||e.is_true()||e.is_false()),
        symbol(e.is_const()&&e.decl().decl_kind()==Z3_OP_UNINTERPRETED){
        if(!e.is_bool()&&!e.is_int())throw std::runtime_error("only original Bool/Int expressions supported");
        if(symbol)name=e.decl().name().str();
    }
};
struct Evaluation {std::vector<Int> values;std::vector<unsigned char> visited;bool legal=false;};
class Observer {
    std::unordered_map<unsigned,unsigned> ids;
public:
    z3::context context;
    std::vector<Node> nodes;
    std::vector<unsigned> variables;
    std::vector<std::vector<unsigned>> dependencies;
    std::vector<std::vector<std::pair<unsigned,unsigned>>> parents;
    std::vector<signed char> forced_boolean;
    uint64_t covered=0,total=0;
    explicit Observer(z3::expr const& formula) {
        z3::expr root(context,Z3_translate(formula.ctx(),formula,context));
        std::vector<z3::expr> todo{root};
        while(!todo.empty()){
            auto e=todo.back();todo.pop_back();if(ids.count(e.id()))continue;
            ids[e.id()]=nodes.size();nodes.emplace_back(e);
            for(unsigned j=e.num_args();j>0;--j)todo.push_back(e.arg(j-1));
        }
        for(unsigned i=0;i<nodes.size();++i){auto& n=nodes[i];total+=n.boolean?1:64;
            for(unsigned j=0;j<n.expr.num_args();++j)n.children.push_back(ids.at(n.expr.arg(j).id()));
            if(n.symbol)variables.push_back(i);
        }
        std::sort(variables.begin(),variables.end(),[&](unsigned a,unsigned b){return nodes[a].name<nodes[b].name;});
        parents.resize(nodes.size());
        for(unsigned p=0;p<nodes.size();++p)for(unsigned j=0;j<nodes[p].children.size();++j)parents[nodes[p].children[j]].push_back({p,j});
        dependencies.resize(nodes.size());
        // Explicit DFS supports shared DAG children whose discovery id precedes a parent.
        std::vector<unsigned char> done(nodes.size());
        for(unsigned start=0;start<nodes.size();++start){
            std::vector<std::pair<unsigned,bool>> stack{{start,false}};
            while(!stack.empty()){
                auto [id,finish]=stack.back();stack.pop_back();if(done[id])continue;
                if(!finish){stack.push_back({id,true});for(auto c:nodes[id].children)if(!done[c])stack.push_back({c,false});continue;}
                auto& d=dependencies[id];if(nodes[id].symbol)d.push_back(id);
                for(auto c:nodes[id].children)d.insert(d.end(),dependencies[c].begin(),dependencies[c].end());
                std::sort(d.begin(),d.end());d.erase(std::unique(d.begin(),d.end()),d.end());done[id]=1;
            }
        }
        // Exact structural consequences of asserting the original formula.
        // Do not spend coverage decisions asking a mandatory conjunct to be false.
        forced_boolean.assign(nodes.size(),-1);std::vector<std::pair<unsigned,bool>> known{{0,true}};
        while(!known.empty()){auto [id,value]=known.back();known.pop_back();if(forced_boolean[id]!=-1)continue;forced_boolean[id]=value;
            auto const& n=nodes[id];
            if(n.kind==Z3_OP_NOT)known.push_back({n.children[0],!value});
            if((n.kind==Z3_OP_AND&&value)||(n.kind==Z3_OP_OR&&!value))for(auto child:n.children)known.push_back({child,value});}
    }
    Evaluation evaluate(std::map<std::string,Int> const& assignment) const {
        Evaluation result;result.values.resize(nodes.size());result.visited.resize(nodes.size());
        struct Frame{unsigned id,next;};std::vector<Frame> stack{{0,0}};
        while(!stack.empty()){
            auto& f=stack.back();auto const& n=nodes[f.id];auto& value=result.values[f.id];
            if(result.visited[f.id]){stack.pop_back();continue;}
            if(n.symbol){auto it=assignment.find(n.name);if(it==assignment.end())throw std::runtime_error("missing original variable: "+n.name);value=it->second;}
            else if(n.constant){value=n.boolean?Int(n.expr.is_true()?1:0):parse_integer(n.expr.to_string());}
            else {
                bool finish=false;
                if(n.kind==Z3_OP_AND||n.kind==Z3_OP_OR){
                    bool is_and=n.kind==Z3_OP_AND;
                    if(f.next&&bool(result.values[n.children[f.next-1]])!=is_and){value=is_and?0:1;finish=true;}
                    else if(f.next==n.children.size()){value=is_and?1:0;finish=true;}
                }
                if(n.kind==Z3_OP_ITE){
                    if(f.next==0){f.next=1;stack.push_back({n.children[0],0});continue;}
                    unsigned child=n.children[bool(result.values[n.children[0]])?1:2];
                    if(f.next==1){f.next=2;stack.push_back({child,0});continue;}
                    value=result.values[child];finish=true;
                }
                if(!finish&&f.next<n.children.size()){unsigned child=n.children[f.next++];stack.push_back({child,0});continue;}
                if(!finish){
                    auto at=[&](unsigned j)->Int const&{return result.values[n.children.at(j)];};
                    switch(n.kind){
                    case Z3_OP_ADD:value=0;for(auto c:n.children)value+=result.values[c];break;
                    case Z3_OP_MUL:value=1;for(auto c:n.children)value*=result.values[c];break;
                    case Z3_OP_SUB:value=at(0);for(unsigned j=1;j<n.children.size();++j)value-=at(j);break;
                    case Z3_OP_UMINUS:value=-at(0);break;
                    case Z3_OP_NOT:value=!bool(at(0));break;
                    case Z3_OP_EQ:value=at(0)==at(1);break;
                    case Z3_OP_LE:value=at(0)<=at(1);break;
                    case Z3_OP_LT:value=at(0)<at(1);break;
                    case Z3_OP_GE:value=at(0)>=at(1);break;
                    case Z3_OP_GT:value=at(0)>at(1);break;
                    case Z3_OP_IMPLIES:value=!bool(at(0))||bool(at(1));break;
                    case Z3_OP_XOR:value=bool(at(0))!=bool(at(1));break;
                    case Z3_OP_DISTINCT:{value=1;std::set<Int> seen;for(auto c:n.children)if(!seen.insert(result.values[c]).second)value=0;break;}
                    default:throw std::runtime_error("unsupported original operator: "+n.expr.decl().name().str());
                    }
                }
            }
            result.visited[f.id]=1;stack.pop_back();
        }
        result.legal=bool(result.values[0]);return result;
    }
    uint64_t commit(Evaluation const& ev){
        uint64_t gain=0;
        for(unsigned i=0;i<nodes.size();++i)if(ev.visited[i]){
            auto& n=nodes[i];uint64_t mask=n.boolean?1:UINT64_MAX,v=low64(ev.values[i])&mask;
            auto before=n.seen0&n.seen1;n.seen1|=v;n.seen0|=(~v)&mask;
            gain+=pop((n.seen0&n.seen1)&~before);
        }
        covered+=gain;return gain;
    }
    z3::expr translate(unsigned id,z3::context& to) const {if(Z3_context(context)==Z3_context(to))return nodes.at(id).expr;return z3::expr(to,Z3_translate(context,nodes.at(id).expr,to));}
    z3::expr reach(unsigned target,z3::context& to,unsigned max_operations=20000) const {
        // Child -> parent edges; memoized symbolic recursion is evaluated using a stack.
        std::vector<std::unique_ptr<z3::expr>> cache(nodes.size());cache[0]=std::make_unique<z3::expr>(to.bool_val(true));
        std::vector<std::pair<unsigned,bool>> stack{{target,false}};unsigned ops=0;
        while(!stack.empty()){
            auto [id,finish]=stack.back();stack.pop_back();if(cache[id])continue;
            if(++ops>max_operations)throw std::runtime_error("reach construction budget");
            if(!finish){stack.push_back({id,true});for(auto [p,j]:parents[id])if(!cache[p])stack.push_back({p,false});continue;}
            auto reach=to.bool_val(false);
            for(auto [p,j]:parents[id]){
                auto edge=*cache[p];auto const& n=nodes[p];
                if(n.kind==Z3_OP_AND||n.kind==Z3_OP_OR)for(unsigned k=0;k<j;++k){
                    // Reach is used only together with F. Mandatory original
                    // conjuncts are already true under F; do not rebuild and
                    // simplify an enormous prefix of the root conjunction.
                    auto forced=forced_boolean[n.children[k]];
                    if(forced!=-1){if(bool(forced)==(n.kind==Z3_OP_AND))continue;edge=to.bool_val(false);break;}
                    if(++ops>max_operations)throw std::runtime_error("reach construction budget");
                    auto e=translate(n.children[k],to);edge=edge&&(n.kind==Z3_OP_AND?e:!e);
                }
                if(n.kind==Z3_OP_ITE&&j>0){auto c=translate(n.children[0],to);edge=edge&&(j==1?c:!c);}
                reach=reach||edge;
            }
            cache[id]=std::make_unique<z3::expr>(reach.simplify());
        }
        return *cache[target];
    }
};
}
