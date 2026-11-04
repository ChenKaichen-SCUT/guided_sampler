#include "pattern.hpp"
#include "kernel_api.hpp"
#include <iostream>
using namespace esg;
void require(bool value,char const* why){if(!value)throw std::runtime_error(why);}
struct Active {
    Active(z3::context& c,Pattern const& p,bool install=false){std::vector<Z3_ast> goals,aux,definitions;for(auto e:p.goals)goals.push_back(e);for(auto e:p.auxiliaries)aux.push_back(e);if(install)for(auto e:p.definitions)definitions.push_back(e);
        Z3_expr_soft_begin(c,goals.size(),goals.data(),aux.size(),aux.data(),64,definitions.size(),definitions.data());}
    ~Active(){Z3_expr_soft_end();}
};
int main(){
    Json cases=Json::array();
    for(int scenario=0;scenario<6;++scenario){
        z3::context c;auto x=c.int_const("x"),y=c.int_const("y"),sum=x+y;
        z3::solver s(c);s.add(x>=0&&x<=100&&y>=0&&y<=100&&y==x+10);s.push();
        uint64_t mask=0x83,desired=0x82;
        if(scenario==1)s.add(sum==130);
        if(scenario==2){mask=0x83;desired=0x83;} // bit zero impossible, other two attainable
        if(scenario==3){s.add(sum==10);mask=0x83;desired=0x82;} // high bit impossible
        if(scenario==4){s.add(x==4);mask=0x83;desired=0x82;}
        auto reach=c.bool_val(scenario!=5);auto p=encode_pattern(sum,reach,mask,desired);s.add(p.definitions);
        uint64_t stats[12];
        {Active a(c,p);require(s.check()==z3::sat,"soft target incorrectly made formula UNSAT");auto m=s.get_model();
            auto integer=parse_integer(m.eval(sum,true).to_string());uint64_t value=low64(integer);unsigned hits=0;
            for(unsigned i=0;i<p.bits.size();++i){bool expected=scenario!=5&&(((value>>p.bits[i])&1)==((desired>>p.bits[i])&1));
                require(m.eval(p.goals[i],true).is_true()==expected,"solver goal is not original expression bit");hits+=expected;}
            Z3_expr_soft_stats(stats);require(stats[0]>=p.goals.size(),"soft targets never internalized on persistent SMT backend");
            std::cerr<<"scenario "<<scenario<<" sum "<<integer<<" hits "<<hits<<" chosen "<<stats[1]<<"\n";
            if(scenario==0)require(hits==3,"feasible coordinated pattern not honored");
            if(scenario==2)require(hits>=1&&hits<3,"conflicting bits not abandoned individually");
            cases.push_back({{"scenario",scenario},{"sum",decimal(integer)},{"hits",hits},{"prepared",stats[0]},{"chosen",stats[1]},{"false",stats[3]},{"exchange_skips",stats[6]}});
        }
        s.pop();s.push();s.add(sum==12);require(s.check()==z3::sat,"temporary preferences/definitions leaked after pop");s.pop();
    }
    // An empty guidance scope must preserve non-incremental routing. A native
    // assumption check must still permanently switch to the incremental route.
    for(unsigned scenario=0;scenario<4;++scenario){
        z3::context c;auto x=c.int_const("x"),y=c.int_const("y");z3::solver s(c);
        s.add(x>=0&&x<=100&&y>=0&&y<=100&&y==x+10);
        require(s.check()==z3::sat,"initial native query");
        for(unsigned iteration=0;iteration<3;++iteration){
            auto p=encode_pattern(x+y,c.bool_val(true),0x83,0x82);
            if(scenario==0||scenario==2){p.goals.resize(0);p.definitions.resize(0);p.auxiliaries.resize(0);}
            Active active(c,p,true);
            z3::expr_vector asms(c);if(scenario>=2&&iteration==1)asms.push_back(x>=0);
            require(s.check(asms)==z3::sat,"route-preserving query failed");auto m=s.get_model();
            for(auto goal:p.goals)require(m.eval(goal,true).is_true(),"preprocessed coordinated pattern not attained");
            uint64_t stats[12];Z3_expr_soft_stats(stats);
            bool incremental=scenario>=2&&iteration>=1;
            require(stats[incremental?9:8]==1&&stats[incremental?8:9]==0,"temporary scope changed native routing state");
            if(p.goals.size())require(stats[0]>0&&stats[11]==0,"preprocessed goals not transported");
            cases.push_back({{"route_scenario",scenario},{"iteration",iteration},{"tactic",stats[8]},{"incremental",stats[9]},{"mapped",stats[10]},{"prepared",stats[0]}});
        }
        s.add(x+y==12);require(s.check()==z3::sat,"temporary definitions leaked");
    }
    // Reach must agree with actual short-circuit visits, including a shared node.
    z3::context c;auto x=c.int_const("x"),y=c.int_const("y");auto expression=x+y;
    auto f=(x>0)||(expression==5&&z3::ite(y>0,expression,-expression)<100);
    Observer o(f);unsigned checked=0;
    for(int xv=-2;xv<=2;++xv)for(int yv=-2;yv<=6;++yv){auto ev=o.evaluate({{"x",Int(xv)},{"y",Int(yv)}});z3::model m(c);
        auto xd=x.decl(),yd=y.decl();auto xx=c.int_val(xv),yy=c.int_val(yv);m.add_const_interp(xd,xx);m.add_const_interp(yd,yy);
        for(unsigned id=0;id<o.nodes.size();++id){require(m.eval(o.reach(id,c),true).is_true()==bool(ev.visited[id]),"Reach differs from short-circuit evaluation");++checked;}}
    // History: neither -> no preference; exactly one -> opposite; both -> none.
    Observer history(x>=0);for(auto const& n:history.nodes)require((n.seen0^n.seen1)==0,"unseen bit preferred");
    history.commit(history.evaluate({{"x",Int(0)}}));unsigned xid=history.variables[0];require(history.nodes[xid].seen0==UINT64_MAX&&history.nodes[xid].seen1==0,"zero history");
    history.commit(history.evaluate({{"x",Int(1)}}));require(((history.nodes[xid].seen0^history.nodes[xid].seen1)&1)==0,"covered bit still preferred");
    Observer conjunction((x>=0)&&(y>=0)&&((x<1)||(x+y<4)));
    for(int xv=0;xv<5;++xv)for(int yv=0;yv<5;++yv){auto ev=conjunction.evaluate({{"x",Int(xv)},{"y",Int(yv)}});if(!ev.legal)continue;
        z3::model m(c);auto xd=x.decl(),yd=y.decl();auto xx=c.int_val(xv),yy=c.int_val(yv);m.add_const_interp(xd,xx);m.add_const_interp(yd,yy);
        for(unsigned id=0;id<conjunction.nodes.size();++id){require(m.eval(conjunction.reach(id,c),true).is_true()==bool(ev.visited[id]),"F-relative Reach mismatch");++checked;}}
    std::cout<<Json({{"passed",true},{"cases",cases},{"reach_checks",checked}}).dump(2)<<"\n";
}
