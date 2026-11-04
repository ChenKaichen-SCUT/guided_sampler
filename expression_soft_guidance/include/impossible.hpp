#pragma once
#include "pattern.hpp"
#include <chrono>
#include <fstream>
#include <optional>

namespace esg {
// Sound, deliberately incomplete facts. k/r means e = r (mod 2^k).
// Bounds are consequences of F, never of the current inherited assignment.
struct BitFacts {
    unsigned k=0;
    uint64_t residue=0,mask=0,value=0;
    std::optional<Int> lower,upper;
};
inline uint64_t low_mask(unsigned k){return k==64?UINT64_MAX:(uint64_t(1)<<k)-1;}
inline unsigned zeros(uint64_t v){return v?__builtin_ctzll(v):64;}
inline Int floor_power(Int const& v,unsigned bit){Int divisor=Int(1)<<bit,q=v/divisor;if(v<0&&v%divisor!=0)--q;return q;}
class ImpossibleBits {
    Observer& o;
    std::vector<BitFacts> facts,direct;
    std::vector<unsigned char> ready,logged;
    std::vector<uint64_t> impossible0,impossible1,probed0,probed1;
    std::unique_ptr<z3::solver> proof;
    std::ofstream log;
    double allowance;
    static void lower(BitFacts& f,Int const& v){if(!f.lower||*f.lower<v)f.lower=v;}
    static void upper(BitFacts& f,Int const& v){if(!f.upper||*f.upper>v)f.upper=v;}
    static BitFacts sum(BitFacts a,BitFacts const& b,bool subtract=false){
        a.k=std::min(a.k,b.k);a.residue=subtract?a.residue-b.residue:a.residue+b.residue;
        if(subtract){a.lower=a.lower&&b.upper?std::optional<Int>(*a.lower-*b.upper):std::nullopt;a.upper=a.upper&&b.lower?std::optional<Int>(*a.upper-*b.lower):std::nullopt;}
        else{a.lower=a.lower&&b.lower?std::optional<Int>(*a.lower+*b.lower):std::nullopt;a.upper=a.upper&&b.upper?std::optional<Int>(*a.upper+*b.upper):std::nullopt;}
        return a;
    }
    static BitFacts multiply(BitFacts const& a,BitFacts const& b){
        BitFacts f;f.k=std::min({64u,a.k+zeros(b.residue),b.k+zeros(a.residue),a.k+b.k});f.residue=a.residue*b.residue;
        if(a.lower&&a.upper&&b.lower&&b.upper){std::vector<Int> v{*a.lower**b.lower,*a.lower**b.upper,*a.upper**b.lower,*a.upper**b.upper};f.lower=*std::min_element(v.begin(),v.end());f.upper=*std::max_element(v.begin(),v.end());}
        return f;
    }
    BitFacts compute(unsigned id){
        auto const& n=o.nodes[id];BitFacts f;
        auto child=[&](unsigned j)->BitFacts const&{return facts[n.children[j]];};
        if(n.constant){Int v=n.boolean?Int(n.expr.is_true()):parse_integer(n.expr.to_string());f.k=64;f.residue=low64(v);f.lower=v;f.upper=v;}
        else if(n.boolean){if(o.forced_boolean[id]!=-1){f.k=64;f.residue=o.forced_boolean[id];f.lower=Int(f.residue);f.upper=f.lower;}}
        else switch(n.kind){
            case Z3_OP_ADD: f.k=64;f.lower=0;f.upper=0;for(auto c:n.children)f=sum(f,facts[c]);break;
            case Z3_OP_SUB: f=child(0);for(unsigned j=1;j<n.children.size();++j)f=sum(f,child(j),true);break;
            case Z3_OP_UMINUS:{BitFacts z;z.k=64;z.lower=0;z.upper=0;f=sum(z,child(0),true);break;}
            case Z3_OP_MUL: f.k=64;f.residue=1;f.lower=1;f.upper=1;for(auto c:n.children)f=multiply(f,facts[c]);break;
            case Z3_OP_ITE:{auto a=child(1),b=child(2);f.k=std::min({a.k,b.k,zeros(a.residue^b.residue)});f.residue=a.residue;
                if(a.lower&&b.lower)f.lower=std::min(*a.lower,*b.lower);if(a.upper&&b.upper)f.upper=std::max(*a.upper,*b.upper);break;}
            default:break;
        }
        if(direct[id].lower)lower(f,*direct[id].lower);if(direct[id].upper)upper(f,*direct[id].upper);
        f.residue&=low_mask(f.k);f.mask=low_mask(f.k);f.value=f.residue;
        if(f.lower&&f.upper&&*f.lower<=*f.upper)for(unsigned bit=0;bit<64;++bit){
            auto a=floor_power(*f.lower,bit),b=floor_power(*f.upper,bit);
            if(a==b){uint64_t mask=uint64_t(1)<<bit;f.mask|=mask;if(low64(a)&1)f.value|=mask;else f.value&=~mask;}}
        if(n.boolean){f.mask&=1;f.value&=1;}return f;
    }
public:
    double proof_wall=0;
    uint64_t static_bits=0,unsat_bits=0,filtered_occurrences=0,proof_calls=0;
    explicit ImpossibleBits(Observer& observer,std::string const& directory,double budget):o(observer),allowance(budget){
        auto n=o.nodes.size();facts.resize(n);direct.resize(n);ready.resize(n);logged.resize(n);impossible0.resize(n);impossible1.resize(n);probed0.resize(n);probed1.resize(n);log.open(directory+"/impossible.jsonl");
        // Only structurally forced comparisons from the original F are usable.
        for(unsigned id=0;id<n;++id){auto const& node=o.nodes[id];if(o.forced_boolean[id]==-1||node.children.size()!=2)continue;
            unsigned kind=node.kind;if(kind!=Z3_OP_EQ&&kind!=Z3_OP_LE&&kind!=Z3_OP_LT&&kind!=Z3_OP_GE&&kind!=Z3_OP_GT)continue;
            bool truth=o.forced_boolean[id];if(kind==Z3_OP_EQ&&!truth)continue;
            for(unsigned side=0;side<2;++side){auto target=node.children[side],literal=node.children[1-side];
                if(o.nodes[target].boolean||!o.nodes[literal].expr.is_int())continue;
                auto e=o.nodes[literal].expr.simplify();if(!e.is_numeral())continue;Int v=parse_integer(e.to_string());unsigned k=kind;
                if(side){if(k==Z3_OP_LE)k=Z3_OP_GE;else if(k==Z3_OP_LT)k=Z3_OP_GT;else if(k==Z3_OP_GE)k=Z3_OP_LE;else if(k==Z3_OP_GT)k=Z3_OP_LT;}
                if(!truth){if(k==Z3_OP_LE)k=Z3_OP_GT;else if(k==Z3_OP_LT)k=Z3_OP_GE;else if(k==Z3_OP_GE)k=Z3_OP_LT;else if(k==Z3_OP_GT)k=Z3_OP_LE;}
                if(k==Z3_OP_EQ||k==Z3_OP_LE)upper(direct[target],v);if(k==Z3_OP_LT)upper(direct[target],v-1);
                if(k==Z3_OP_EQ||k==Z3_OP_GE)lower(direct[target],v);if(k==Z3_OP_GT)lower(direct[target],v+1);
            }
        }
    }
    BitFacts const& get(unsigned id){
        std::vector<std::pair<unsigned,bool>> stack{{id,false}};
        while(!stack.empty()){auto [n,finish]=stack.back();stack.pop_back();if(ready[n])continue;
            if(!finish){stack.push_back({n,true});for(auto c:o.nodes[n].children)if(!ready[c])stack.push_back({c,false});continue;}
            facts[n]=compute(n);ready[n]=1;}
        return facts[id];
    }
    uint64_t eligible(unsigned id,uint64_t demand,uint64_t desired,unsigned query){
        auto const& f=get(id);
        if(!logged[id]&&f.mask){logged[id]=1;static_bits+=pop(f.mask);
            Json row={{"kind","static"},{"query",query},{"node",id},{"scope","original_F"},{"mask",f.mask},{"value",f.value},{"modulo_bits",f.k},{"residue",f.residue}};
            if(f.lower)row["lower"]=decimal(*f.lower);if(f.upper)row["upper"]=decimal(*f.upper);log<<row.dump()<<"\n";log.flush();}
        // A fixed bit is excluded only when its requested side contradicts the fact.
        uint64_t blocked=(f.mask&(f.value^desired))|(impossible1[id]&desired)|(impossible0[id]&~desired);
        filtered_occurrences+=pop(demand&blocked);return demand&~blocked;
    }
    uint64_t probe(unsigned id,uint64_t selected,uint64_t desired,z3::expr const& reach,unsigned query,double remaining){
        uint64_t todo=selected&~((probed1[id]&desired)|(probed0[id]&~desired));
        if(!todo||proof_wall>=allowance||remaining<0.05)return selected;
        unsigned bit=__builtin_ctzll(todo);uint64_t mask=uint64_t(1)<<bit;bool want=desired&mask;
        (want?probed1[id]:probed0[id])|=mask;
        auto start=std::chrono::steady_clock::now();
        if(!proof){proof=std::make_unique<z3::solver>(o.context);proof->add(o.nodes[0].expr);}
        auto p=encode_pattern(o.nodes[id].expr,reach,mask,desired);
        proof->push();proof->add(p.definitions);proof->add(p.goals);
        z3::params parameters(o.context);parameters.set("timeout",unsigned(std::max(1.0,std::min({5.0,(allowance-proof_wall)*1000.0,remaining*1000.0}))));proof->set(parameters);
        auto result=proof->check();std::string reason=result==z3::unknown?proof->reason_unknown():"";proof->pop();
        double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();proof_wall+=elapsed;++proof_calls;
        log<<Json({{"kind","probe"},{"query",query},{"node",id},{"bit",bit},{"desired",want},{"scope","original_F_and_Reach"},{"result",result==z3::unsat?"unsat":result==z3::sat?"sat":"unknown"},{"reason",reason},{"wall",elapsed},{"reach",reach.to_string()}}).dump()<<"\n";log.flush();
        if(result==z3::unsat){(want?impossible1[id]:impossible0[id])|=mask;++unsat_bits;return selected&~mask;}return selected;
    }
};
}
