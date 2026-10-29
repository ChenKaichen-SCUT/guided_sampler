#pragma once
#include <z3++.h>
#include <boost/multiprecision/cpp_int.hpp>
#include <nlohmann/json.hpp>
#include <bit>
#include <optional>
#include <map>
#include <set>
#include <unordered_map>
#include <vector>
#include <chrono>
namespace guided {
using Big=boost::multiprecision::cpp_int;
using Json=nlohmann::json;
using Clock=std::chrono::steady_clock;
inline uint64_t low64(Big v) { const Big p=Big(1)<<64;v%=p;if(v<0)v+=p;return v.convert_to<uint64_t>(); }
inline Big numeral(z3::expr const& e) {return Big(Z3_get_numeral_string(e.ctx(),e));}
struct Node {
    z3::expr e; std::vector<unsigned> children;std::vector<std::pair<unsigned,unsigned>> parents;
    uint64_t seen0=0,seen1=0; bool boolean,literal;
    Node(z3::expr e):e(e),boolean(e.is_bool()),literal(e.is_numeral()||e.is_true()||e.is_false()) {}
    uint64_t mask()const{return boolean?1:UINT64_MAX;}
};
struct Evaluation { std::vector<std::optional<Big>> values;uint64_t observed=0,covered=0;std::vector<unsigned> changed; };
struct Target {unsigned node,bit;bool desired;unsigned id()const{return node*128+bit*2+desired;} };
class OriginalAst {
public:
    z3::context& c;std::vector<Node> nodes;std::vector<z3::expr> vars;
    std::unordered_map<unsigned,unsigned> ids;uint64_t total=0,covered=0,observed=0;unsigned version=0;
    unsigned cursor_node=0,cursor_bit=0;
    explicit OriginalAst(z3::expr const& root):c(root.ctx()) {
        std::vector<z3::expr> todo{root};
        while(!todo.empty()) {
            auto e=todo.back();todo.pop_back();
            if(ids.count(e.id()))continue;
            if(!e.is_app() || (!e.is_int()&&!e.is_bool()))throw std::runtime_error("Only original Bool/Int applications supported");
            ids[e.id()]=nodes.size();nodes.emplace_back(e);
            if(e.is_const()&&e.decl().decl_kind()==Z3_OP_UNINTERPRETED)vars.push_back(e);
            for(unsigned j=e.num_args();j>0;--j)todo.push_back(e.arg(j-1));
        }
        for(unsigned i=0;i<nodes.size();++i) {
            auto& n=nodes[i];total+=n.boolean?1:64;
            for(unsigned j=0;j<n.e.num_args();++j){unsigned k=ids.at(n.e.arg(j).id());n.children.push_back(k);nodes[k].parents.emplace_back(i,j);}
        }
        std::sort(vars.begin(),vars.end(),[](auto const& a,auto const& b){return std::pair(a.decl().name().str(),a.is_int())<std::pair(b.decl().name().str(),b.is_int());});
        std::set<std::string> names;
        for(auto const& v:vars)if(!names.insert(v.decl().name().str()).second)throw std::runtime_error("Same name with different sorts is unsupported by official metric");
    }
    Evaluation evaluate(std::map<std::string,Big> const& assignment)const {
        Evaluation r;r.values.resize(nodes.size());
        struct Frame{unsigned n,k;};std::vector<Frame> stack{{0,0}};
        while(!stack.empty()) {
            auto& f=stack.back();auto const& n=nodes[f.n];auto op=n.e.decl().decl_kind();
            if(r.values[f.n]){stack.pop_back();continue;}
            if(n.children.empty()) {
                if(n.e.is_numeral())r.values[f.n]=numeral(n.e);
                else if(n.e.is_true())r.values[f.n]=1;
                else if(n.e.is_false())r.values[f.n]=0;
                else r.values[f.n]=assignment.at(n.e.decl().name().str());
                stack.pop_back();continue;
            }
            if(op==Z3_OP_ITE) {
                unsigned cond=n.children[0];
                if(!r.values[cond]){stack.push_back({cond,0});continue;}
                unsigned chosen=n.children[*r.values[cond]!=0?1:2];
                if(!r.values[chosen]){stack.push_back({chosen,0});continue;}
                r.values[f.n]=*r.values[chosen];stack.pop_back();continue;
            }
            if(f.k && (op==Z3_OP_AND||op==Z3_OP_OR)) {
                bool v=*r.values[n.children[f.k-1]]!=0;
                if((op==Z3_OP_AND&&!v)||(op==Z3_OP_OR&&v)){r.values[f.n]=v;stack.pop_back();continue;}
            }
            if(f.k<n.children.size()) {
                unsigned child=n.children[f.k++];
                if(!r.values[child])stack.push_back({child,0});
                continue;
            }
            auto v=[&](unsigned k)->Big const&{return *r.values[n.children.at(k)];};Big value=0;
            switch(op) {
            case Z3_OP_AND:value=1;break;case Z3_OP_OR:value=0;break;
            case Z3_OP_NOT:value=v(0)==0;break;
            case Z3_OP_EQ:value=v(0)==v(1);break;
            case Z3_OP_LE:value=v(0)<=v(1);break;case Z3_OP_LT:value=v(0)<v(1);break;
            case Z3_OP_GE:value=v(0)>=v(1);break;case Z3_OP_GT:value=v(0)>v(1);break;
            case Z3_OP_ADD:for(unsigned k=0;k<n.children.size();++k)value+=v(k);break;
            case Z3_OP_MUL:value=1;for(unsigned k=0;k<n.children.size();++k)value*=v(k);break;
            case Z3_OP_SUB:if(n.children.size()!=2)throw std::runtime_error("Official SUB expects binary");value=v(0)-v(1);break;
            case Z3_OP_UMINUS:value=-v(0);break;
            default:throw std::runtime_error("Original operation unsupported by official observer: "+std::to_string(op));
            }
            r.values[f.n]=value;stack.pop_back();
        }
        for(unsigned i=0;i<nodes.size();++i)if(r.values[i]) {
            auto const& n=nodes[i];uint64_t one=low64(*r.values[i])&n.mask(),zero=(~one)&n.mask();
            auto no=std::popcount(one&~n.seen1)+std::popcount(zero&~n.seen0);
            r.observed+=no;r.covered+=std::popcount((n.seen1|one)&(n.seen0|zero))-std::popcount(n.seen1&n.seen0);
            if(no)r.changed.push_back(i);
        }
        return r;
    }
    void commit(Evaluation const& r) {
        for(auto i:r.changed){auto& n=nodes[i];uint64_t v=low64(*r.values[i])&n.mask();n.seen1|=v;n.seen0|=(~v)&n.mask();}
        covered+=r.covered;observed+=r.observed;++version;
    }
    std::vector<Target> select_window() {
        std::vector<Target> r;unsigned steps=0;
        while(r.size()<8 && steps<nodes.size()+1) {
            auto const& n=nodes[cursor_node];uint64_t demand=(n.seen0^n.seen1)&n.mask();
            if(n.literal)demand=0;
            demand &= UINT64_MAX<<cursor_bit;
            while(demand && r.size()<8) {
                unsigned b=std::countr_zero(demand);r.push_back({cursor_node,b,bool((n.seen0>>b)&1)});
                demand&=demand-1;cursor_bit=b+1;
            }
            if(r.size()==8 && cursor_bit<64)break;
            cursor_bit=0;cursor_node=(cursor_node+1)%nodes.size();++steps;
        }
        // Cursor wrap can encounter the same target when fewer than 8 exist.
        std::set<unsigned> seen;std::vector<Target> out;
        for(auto t:r)if(seen.insert(t.id()).second)out.push_back(t);
        return out;
    }
};
class ReachBuilder {
    OriginalAst& ast;std::vector<std::optional<z3::expr>> cache;
    std::map<unsigned,std::vector<z3::expr>> prefixes;
public:
    explicit ReachBuilder(OriginalAst& a):ast(a),cache(a.nodes.size()){cache[0]=a.c.bool_val(true);}
    z3::expr reach(unsigned id,unsigned& cost) {
        std::vector<std::pair<unsigned,bool>> stack{{id,false}};
        auto charge=[&](){if(++cost>4096)throw std::runtime_error("encoding_incomplete");};
        while(!stack.empty()) {
            auto [i,ready]=stack.back();stack.pop_back();if(cache[i])continue;
            if(!ready){stack.emplace_back(i,true);for(auto [p,k]:ast.nodes[i].parents)if(!cache[p])stack.emplace_back(p,false);continue;}
            z3::expr result=ast.c.bool_val(false);
            for(auto [p,k]:ast.nodes[i].parents) {
                auto const& parent=ast.nodes[p];auto op=parent.e.decl().decl_kind();z3::expr edge=*cache[p];
                if(op==Z3_OP_AND||op==Z3_OP_OR) {
                    auto& pre=prefixes[p];if(pre.empty())pre.push_back(*cache[p]);
                    while(pre.size()<=k){unsigned j=pre.size()-1;charge();auto child=ast.nodes[parent.children[j]].e;pre.push_back(pre.back()&&(op==Z3_OP_AND?child:!child));}
                    edge=pre[k];
                } else if(op==Z3_OP_ITE&&k>0){charge();auto cond=ast.nodes[parent.children[0]].e;edge=edge&&(k==1?cond:!cond);}
                charge();result=result||edge;
            }
            cache[i]=result;
        }
        return *cache[id];
    }
};
class TargetEncoder {
    OriginalAst& ast;ReachBuilder reach;
public:
    explicit TargetEncoder(OriginalAst& a):ast(a),reach(a){}
    z3::expr make(Target t) {
        unsigned cost=0;auto r=reach.reach(t.node,cost);auto e=ast.nodes[t.node].e;
        if(e.is_bool())return r&&(t.desired?e:!e);
        std::string ps=(Big(1)<<(t.bit+1)).convert_to<std::string>(),hs=(Big(1)<<t.bit).convert_to<std::string>();
        auto rem=z3::mod(e,ast.c.int_val(ps.c_str()));auto half=ast.c.int_val(hs.c_str());
        return r&&(t.desired?rem>=half:rem<half);
    }
};
struct Hint {z3::expr atom;bool phase;unsigned node;std::optional<uint64_t> constant;};
class AtomHintCatalog {
    OriginalAst& ast;
public:
    std::vector<std::vector<Hint>> by_node;
    explicit AtomHintCatalog(OriginalAst& a):ast(a),by_node(a.nodes.size()) {
        for(unsigned i=0;i<a.nodes.size();++i) {
            auto e=a.nodes[i].e;auto op=e.decl().decl_kind();
            if(!e.is_bool()||a.nodes[i].literal)continue;
            if(op==Z3_OP_AND||op==Z3_OP_OR||op==Z3_OP_ITE)continue;
            bool phase=true;auto atom=e;
            while(atom.is_not()){phase=!phase;atom=atom.arg(0);}
            if(!atom.is_and()&&!atom.is_or()&&!atom.is_true()&&!atom.is_false())by_node[i].push_back({atom,phase,i,{}});
            if(e.is_eq()&&e.arg(0).is_int())for(unsigned side=0;side<2;++side) {
                auto term=e.arg(side),val=e.arg(1-side);
                if(!val.is_numeral())continue;
                unsigned ni=a.ids.at(term.id());
                by_node[ni].push_back({e,true,ni,low64(numeral(val))});
                by_node[ni].push_back({val==term,true,ni,low64(numeral(val))});
            }
        }
    }
    std::vector<Hint> lookup(Target t)const {
        std::vector<Hint> r;
        for(auto h:by_node[t.node]) {
            if(h.constant){if(bool((*h.constant>>t.bit)&1)==t.desired)r.push_back(h);}
            else {h.phase=t.desired?h.phase:!h.phase;r.push_back(h);}
        }
        return r;
    }
};
}
