#pragma once
#include "affine_ir.hpp"
#include <numeric>
namespace refinement {
struct Fraction {
    Big n=0,d=1;Fraction()=default;Fraction(Big a):n(std::move(a)){}Fraction(Big a,Big q):n(std::move(a)),d(std::move(q)){normalize();}
    void normalize(){if(d==0)throw std::runtime_error("zero rational denominator");if(d<0){n=-n;d=-d;}Big g=gcd_big(n,d);n/=g;d/=g;}
};
struct AlgebraBudget {WorkBudget& time;uint64_t ops=0;void check(){time.check();if(time.trace)++time.trace->elimination_ops;if(++ops>200000)throw Exhausted("component_elimination_budget");}void value(Fraction const& x){time.integer(x.n);time.integer(x.d);}};
inline Fraction normalized_fraction(Big n,Big d,AlgebraBudget& w){w.time.integer(n);w.time.bits(d);if(d==0)throw std::runtime_error("zero denominator");if(d<0){n=-n;d=-d;}Big g=checked_gcd(n,d,w.time);Fraction q;q.n=n/g;q.d=d/g;return q;}
inline Fraction subtract(Fraction const& a,Fraction const& b,AlgebraBudget& w){w.check();return normalized_fraction(checked_add(checked_mul(a.n,b.d,w.time),-checked_mul(b.n,a.d,w.time),w.time),checked_mul(a.d,b.d,w.time),w);}
inline Fraction multiply(Fraction const& a,Fraction const& b,AlgebraBudget& w){w.check();return normalized_fraction(checked_mul(a.n,b.n,w.time),checked_mul(a.d,b.d,w.time),w);}
inline Fraction divide(Fraction const& a,Fraction const& b,AlgebraBudget& w){w.check();if(b.n==0)throw std::runtime_error("zero pivot");return normalized_fraction(checked_mul(a.n,b.d,w.time),checked_mul(a.d,b.n,w.time),w);}
struct IntegerDirection {unsigned id=0,component=0,local_id=0;IntegerVector values;std::vector<unsigned> affected;};
struct DirectionPool {std::vector<IntegerDirection> directions;Json components=Json::array();uint64_t omitted=0;};
inline std::string direction_key(IntegerVector const& d){std::string s;for(auto const& [i,v]:d)s+=std::to_string(i)+":"+v.str()+";";return s;}
inline DirectionPool build_integer_directions(AffineIR const& ir,EqualitySystem const& eq,WorkBudget& b){
    StageScope components(b.trace,RepairStage::Components);
    size_t nv=ir.ast.variables.size();std::vector<unsigned> parent(nv);std::iota(parent.begin(),parent.end(),0);
    std::function<unsigned(unsigned)> root=[&](unsigned x){while(parent[x]!=x){parent[x]=parent[parent[x]];x=parent[x];}return x;};
    for(auto const& r:eq.rows){b.check();if(!r.coefficients.empty()){unsigned first=r.coefficients.begin()->first;for(auto const& [v,c]:r.coefficients){auto a=root(first),z=root(v);parent[std::max(a,z)]=std::min(a,z);}}}
    std::map<unsigned,std::vector<unsigned>> comps;for(unsigned i=0;i<nv;++i)if(!ir.ast.variables[i].boolean)comps[root(i)].push_back(i);
    std::map<unsigned,std::vector<unsigned>> component_rows;
    std::vector<std::vector<std::pair<unsigned,Big>>> equation_uses(nv);
    for(unsigned k=0;k<eq.rows.size();++k){b.check();auto const& row=eq.rows[k];if(!row.coefficients.empty())component_rows[root(row.coefficients.begin()->first)].push_back(k);for(auto const& [v,c]:row.coefficients)equation_uses[v].emplace_back(k,c);}
    std::vector<std::vector<unsigned>> node_uses;
    if(ir.mode!=RepairMode::Shared)node_uses.resize(nv);
    for(unsigned n=0;n<ir.dependencies.size();++n){b.check();for(auto v:ir.dependencies[n])node_uses[v].push_back(n);}
    DirectionPool out;std::vector<std::vector<IntegerDirection>> generated;unsigned cid=0;
    for(auto const& [r,vars]:comps){b.check();Json info={{"component",cid},{"variables",vars},{"status","complete"}};std::vector<unsigned> rowids=component_rows[r];size_t nonzeros=0;
        for(auto k:rowids){b.check();nonzeros+=eq.rows[k].coefficients.size();}
        info["rows"]=rowids;info["nonzeros"]=nonzeros;std::vector<IntegerDirection> dirs;
        if(vars.size()>64||rowids.size()>128||nonzeros>4096)info["status"]="component_size_limit";
        else try {
            StageScope elimination(b.trace,RepairStage::Elimination);
            using Row=std::map<unsigned,Fraction>;std::vector<Row> rows;for(auto k:rowids){Row row;for(auto const& [v,c]:eq.rows[k].coefficients)row.emplace(v,Fraction(c));rows.push_back(std::move(row));}
            AlgebraBudget w{b};std::vector<unsigned> pivots;unsigned pos=0;
            for(auto v:vars){w.check();unsigned selected=pos;while(selected<rows.size()&&(!rows[selected].count(v)||rows[selected][v].n==0))++selected;if(selected==rows.size())continue;std::swap(rows[pos],rows[selected]);auto pivot=rows[pos].at(v);
                for(auto& [col,c]:rows[pos])c=divide(c,pivot,w);
                for(unsigned k=0;k<rows.size();++k)if(k!=pos&&rows[k].count(v)){auto factor=rows[k].at(v);for(auto const& [col,c]:rows[pos]){auto old=rows[k].count(col)?rows[k].at(col):Fraction();auto val=subtract(old,multiply(factor,c,w),w);if(val.n==0)rows[k].erase(col);else rows[k][col]=std::move(val);}}
                pivots.push_back(v);++pos;
            }
            unsigned lid=0;for(auto free:vars)if(std::find(pivots.begin(),pivots.end(),free)==pivots.end()){
                w.check();std::map<unsigned,Fraction> rational;rational[free]=Fraction(1);Big lcm=1;
                for(unsigned p=0;p<pivots.size();++p)if(rows[p].count(free)){auto q=rows[p].at(free);q.n=-q.n;rational[pivots[p]]=q;lcm=checked_mul(lcm/checked_gcd(lcm,q.d,b),q.d,b);b.integer(lcm);}
                IntegerDirection dir;dir.component=cid;dir.local_id=lid++;Big gcd=0;
                for(auto const& [v,q]:rational){b.check();Big c=checked_mul(q.n,lcm/q.d,b);b.integer(c);if(c!=0){dir.values[v]=c;gcd=checked_gcd(gcd,c,b);}}
                if(dir.values.empty())continue;Big sign=dir.values.begin()->second<0?-1:1;for(auto& [v,c]:dir.values){c=sign*(c/gcd);b.integer(c);}
                // Verify all mandatory rows, including rows not used by this component.
                StageScope verify(b.trace,RepairStage::VerifyDirections);std::vector<Big> dots(eq.rows.size(),0);for(auto const& [v,step]:dir.values)for(auto const& [row,c]:equation_uses[v])dots[row]=checked_add(dots[row],checked_mul(c,step,b),b);for(auto const& dot:dots){b.check();if(dot!=0)throw std::runtime_error("integer direction violates mandatory equality");}
                dirs.push_back(std::move(dir));
            }
            info["elimination_ops"]=w.ops;info["nullity"]=dirs.size();
        }catch(Exhausted const& e){std::string why=e.what();if(why!="component_elimination_budget"&&why!="integer_bit_limit")throw;dirs.clear();info["status"]=why;}
        info["generated"]=dirs.size();out.components.push_back(info);generated.push_back(std::move(dirs));++cid;
    }
    StageScope affected_scope(b.trace,RepairStage::BuildAffected);
    ScratchMarks marks(ir.mode==RepairMode::Shared?ir.ast.nodes.size():0);if(b.trace&&ir.mode==RepairMode::Shared)b.trace->allocation(ir.ast.nodes.size());
    std::set<std::string> seen;for(size_t round=0;;++round){bool any=false;for(auto const& dirs:generated)if(round<dirs.size()){b.check();any=true;auto d=dirs[round];if(!seen.insert(direction_key(d.values)).second)continue;if(out.directions.size()>=256){++out.omitted;continue;}d.id=out.directions.size();if(ir.mode==RepairMode::Shared)d.affected=collect_affected(ir.reverse,d.values,marks,b);else{std::set<unsigned> affected;for(auto const& [v,step]:d.values){b.check();affected.insert(node_uses[v].begin(),node_uses[v].end());}d.affected.assign(affected.begin(),affected.end());}if(b.trace)b.trace->affected_entries+=d.affected.size();out.directions.push_back(std::move(d));}if(!any)break;}
    for(auto& c:out.components){unsigned included=0;for(auto const& d:out.directions)if(d.component==c["component"])++included;c["included"]=included;c["omitted"]=c["generated"].get<unsigned>()-included;}
    return out;
}
inline std::vector<unsigned> select_directions(DirectionPool const& pool,Ast const& ast,ObservationHistory const& history,uint64_t event,WorkBudget& b){
    std::vector<std::pair<uint64_t,unsigned>> ranked;for(auto const& d:pool.directions){uint64_t score=0;for(auto n:d.affected){b.check();score+=std::popcount(ast.nodes[n].mask()&~(history.zero[n]&history.one[n]));}ranked.emplace_back(score,d.id);}
    std::sort(ranked.begin(),ranked.end(),[](auto a,auto c){return a.first!=c.first?a.first>c.first:a.second<c.second;});std::vector<unsigned> chosen;
    for(size_t i=0;i<std::min(size_t(8),ranked.size());++i)chosen.push_back(ranked[i].second);
    std::vector<unsigned> rest;for(auto const& d:pool.directions)if(std::find(chosen.begin(),chosen.end(),d.id)==chosen.end())rest.push_back(d.id);
    for(size_t i=0;i<std::min(size_t(8),rest.size());++i)chosen.push_back(rest[(event+i)%rest.size()]);return chosen;
}
}
