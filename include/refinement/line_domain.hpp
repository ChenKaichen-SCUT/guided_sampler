#pragma once
#include "affine_ir.hpp"
namespace refinement {
// A missing lower bound is -infinity; a missing upper bound is +infinity.
// No integer sentinel participates in arithmetic.
struct Interval {std::optional<Big> lo,hi;};
using IntervalUnion=std::vector<Interval>;
struct DomainBudget {WorkBudget& time;uint64_t operations=0;void tick(){time.check();if(++operations>200000)throw Exhausted("domain_budget_exhausted");}};
inline bool lower_less(std::optional<Big> const& a,std::optional<Big> const& b){return !a?bool(b):b&&*a<*b;}
inline bool upper_less(std::optional<Big> const& a,std::optional<Big> const& b){return !b?bool(a):a&&*a<*b;}
inline bool nonempty(Interval const& i){return !i.lo||!i.hi||*i.lo<=*i.hi;}
inline IntervalUnion normalize(IntervalUnion src,DomainBudget& b){
    std::sort(src.begin(),src.end(),[&](auto const& a,auto const& c){b.tick();return a.lo!=c.lo?lower_less(a.lo,c.lo):upper_less(a.hi,c.hi);});IntervalUnion out;
    for(auto const& i:src){b.tick();if(!nonempty(i))continue;if(i.lo)b.time.integer(*i.lo);if(i.hi)b.time.integer(*i.hi);
        bool touch=false;if(!out.empty()){auto const& last=out.back();if(!last.hi||!i.lo)touch=true;else{Big next=*last.hi+1;b.time.integer(next);touch=*i.lo<=next;}}
        if(touch){if(!out.back().hi||!i.hi)out.back().hi.reset();else out.back().hi=std::max(*out.back().hi,*i.hi);}else out.push_back(i);
        if(out.size()>4096)throw Exhausted("domain_interval_limit");
    }return out;
}
inline IntervalUnion all_integers(){return {{std::nullopt,std::nullopt}};}
inline bool domain_contains(IntervalUnion const& u,Big const& t){for(auto const& i:u)if((!i.lo||t>=*i.lo)&&(!i.hi||t<=*i.hi))return true;return false;}
inline IntervalUnion unite(IntervalUnion const& a,IntervalUnion const& c,DomainBudget& b){IntervalUnion out=a;out.insert(out.end(),c.begin(),c.end());return normalize(std::move(out),b);}
inline IntervalUnion intersect(IntervalUnion const& a,IntervalUnion const& c,DomainBudget& b){IntervalUnion out;size_t i=0,j=0;while(i<a.size()&&j<c.size()){b.tick();auto lo=lower_less(a[i].lo,c[j].lo)?c[j].lo:a[i].lo;auto hi=upper_less(a[i].hi,c[j].hi)?a[i].hi:c[j].hi;Interval x{lo,hi};if(nonempty(x))out.push_back(x);if(out.size()>4096)throw Exhausted("domain_interval_limit");if(a[i].hi==c[j].hi){++i;++j;}else if(upper_less(a[i].hi,c[j].hi))++i;else ++j;}return out;}
inline IntervalUnion complement(IntervalUnion const& a,DomainBudget& b){IntervalUnion out;std::optional<Big> cursor;bool ended=false;for(auto const& i:a){b.tick();if(i.lo){Big h=*i.lo-1;b.time.integer(h);Interval gap{cursor,h};if(nonempty(gap))out.push_back(gap);}if(!i.hi){ended=true;break;}cursor=*i.hi+1;b.time.integer(*cursor);}if(!ended)out.push_back({cursor,std::nullopt});if(out.size()>4096)throw Exhausted("domain_interval_limit");return out;}
inline IntervalUnion le_domain(LineTerm const& v,DomainBudget& b){b.tick();if(v.slope==0)return v.constant<=0?all_integers():IntervalUnion{};if(v.slope>0)return {{std::nullopt,floor_div(-v.constant,v.slope)}};return {{ceil_div(-v.constant,v.slope),std::nullopt}};}
inline IntervalUnion eq_domain(LineTerm const& v,DomainBudget& b){b.tick();if(v.slope==0)return v.constant==0?all_integers():IntervalUnion{};if((-v.constant)%v.slope!=0)return {};Big t=-v.constant/v.slope;b.time.integer(t);return {{t,t}};}
inline IntervalUnion reflect(IntervalUnion const& a,DomainBudget& b){IntervalUnion out;for(auto it=a.rbegin();it!=a.rend();++it){b.tick();out.push_back({it->hi?std::optional<Big>(-*it->hi):std::nullopt,it->lo?std::optional<Big>(-*it->lo):std::nullopt});}return out;}
inline Json domain_json(IntervalUnion const& a){Json j=Json::array();for(auto const& i:a)j.push_back({i.lo?Json(i.lo->str()):Json("-inf"),i.hi?Json(i.hi->str()):Json("+inf")});return j;}
class LineDomain {
    AffineIR const& ir;Assignment const& anchor;IntegerVector const& direction;std::vector<std::optional<IntervalUnion>> cache;AnchorValues* values;std::vector<unsigned> affected;std::optional<LineValues> lines;
public:
    DomainBudget work;
    LineDomain(AffineIR const& a,Assignment const& m,IntegerVector const& d,WorkBudget& b,AnchorValues* numeric=nullptr,std::vector<unsigned> const* affected_nodes=nullptr):ir(a),anchor(m),direction(d),cache(a.ast.nodes.size()),values(numeric),work{b}{
        if(b.trace)b.trace->allocation(a.ast.nodes.size());
        if(a.mode==RepairMode::Shared){if(affected_nodes)affected=*affected_nodes;else{ScratchMarks scratch(a.ast.nodes.size());if(b.trace)b.trace->allocation(a.ast.nodes.size());affected=collect_affected(a.reverse,d,scratch,b);}}
        if(values)lines.emplace(a,m,d,*values,affected);
    }
    bool varies(unsigned n)const{return ir.mode==RepairMode::Shared?depends_on_direction(n,affected):depends_on(ir.dependencies[n],direction);}
    LineTerm line_term(unsigned n){return lines?lines->value(n,work.time):affine_on_line(ir,n,anchor,direction,work.time);}
    IntervalUnion truth(unsigned root){
        struct Frame{unsigned id;bool ready;};std::vector<Frame> todo{{root,false}};
        while(!todo.empty()){
            work.tick();auto f=todo.back();if(work.time.trace)work.time.trace->node(f.id);todo.pop_back();if(cache[f.id])continue;auto const& n=ir.ast.nodes[f.id];if(!n.boolean)throw std::runtime_error("nonboolean formula domain");
            if(!varies(f.id)){Big v;if(values)v=values->numeric.value(f.id,work.time);else{StageScope numeric(work.time.trace,RepairStage::NumericValues);auto e=evaluate(ir.ast,anchor,work.time,false,f.id);v=*e.values[f.id];}cache[f.id]=v!=0?all_integers():IntervalUnion{};continue;}
            if(!f.ready){todo.push_back({f.id,true});for(auto c:n.children)if(ir.ast.nodes[c].boolean&&!cache[c])todo.push_back({c,false});continue;}
            auto const& cs=n.children;auto get=[&](unsigned k)->IntervalUnion const&{return *cache.at(cs.at(k));};IntervalUnion out;
            if(n.op==Op::And){out=all_integers();for(unsigned k=0;k<cs.size();++k)out=intersect(out,get(k),work);}
            else if(n.op==Op::Or){for(unsigned k=0;k<cs.size();++k)out=unite(out,get(k),work);}
            else if(n.op==Op::Not)out=complement(get(0),work);
            else if(n.op==Op::Implies)out=unite(complement(get(0),work),get(1),work);
            else if(n.op==Op::Xor){for(unsigned k=0;k<cs.size();++k)out=unite(intersect(out,complement(get(k),work),work),intersect(complement(out,work),get(k),work),work);}
            else if(n.op==Op::Ite)out=unite(intersect(get(0),get(1),work),intersect(complement(get(0),work),get(2),work),work);
            else if(n.op==Op::Eq||n.op==Op::Distinct||n.op==Op::Le||n.op==Op::Lt||n.op==Op::Ge||n.op==Op::Gt){
                out=all_integers();for(unsigned l=0;l<cs.size();++l)for(unsigned r=l+1;r<cs.size();++r){if(n.op!=Op::Distinct&&r!=l+1)continue;work.tick();IntervalUnion atom;
                    if(ir.ast.nodes[cs[l]].boolean){if(n.op!=Op::Eq&&n.op!=Op::Distinct)throw Unsupported("ordered_boolean_comparison");atom=unite(intersect(*cache[cs[l]],*cache[cs[r]],work),intersect(complement(*cache[cs[l]],work),complement(*cache[cs[r]],work),work),work);}
                    else{auto a=line_term(cs[l]),c=line_term(cs[r]);LineTerm diff{a.constant-c.constant,a.slope-c.slope};work.time.integer(diff.constant);work.time.integer(diff.slope);
                        if(n.op==Op::Eq||n.op==Op::Distinct)atom=eq_domain(diff,work);else{if(n.op==Op::Ge||n.op==Op::Gt){diff.constant=-diff.constant;diff.slope=-diff.slope;}if(n.op==Op::Lt||n.op==Op::Gt)++diff.constant;work.time.integer(diff.constant);atom=le_domain(diff,work);}}
                    if(n.op==Op::Distinct)atom=complement(atom,work);out=intersect(out,atom,work);
                }
            }else throw Unsupported("unsupported_boolean_domain");cache[f.id]=normalize(std::move(out),work);
        }return *cache.at(root);
    }
    IntervalUnion formula(){auto u=truth(0);if(!domain_contains(u,0))throw std::runtime_error("legal native anchor excluded by complete line domain");return u;}
};
}
