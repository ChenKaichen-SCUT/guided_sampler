#pragma once
#include "budget.hpp"
#include <nlohmann/json.hpp>
#include <map>
#include <set>
#include <optional>
#include <vector>
#include <bit>
namespace refinement {
using Json=nlohmann::json;
enum class Op {Constant,Variable,And,Or,Not,Implies,Xor,Ite,Eq,Distinct,Le,Lt,Ge,Gt,Add,Mul,Sub,Neg,Div,Mod,Unknown};
inline std::vector<std::string> const& op_names(){static std::vector<std::string> n={"const","var","and","or","not","implies","xor","ite","eq","distinct","le","lt","ge","gt","add","mul","sub","neg","div","mod","unknown"};return n;}
inline Op op_from(std::string const& name){auto const& ns=op_names();auto it=std::find(ns.begin(),ns.end(),name);if(it==ns.end())throw Unsupported("unknown_operator:"+name);return Op(it-ns.begin());}
struct Var {std::string name;bool boolean=false;};
struct Node {Op op=Op::Unknown;bool boolean=false;int variable=-1;Big constant=0;std::vector<unsigned> children;uint64_t mask()const{return boolean?1:UINT64_MAX;}};
using Assignment=std::vector<Big>;
struct Ast {
    std::string input_sha;std::vector<Node> nodes;std::vector<Var> variables;std::vector<unsigned> postorder;uint64_t total=0;
    void finalize(WorkBudget& budget){
        if(nodes.empty())throw std::runtime_error("empty original AST");total=0;postorder.clear();std::vector<unsigned char> state(nodes.size(),0);
        for(auto const& n:nodes){budget.check();total+=n.boolean?1:64;if(n.op==Op::Variable&&(n.variable<0||size_t(n.variable)>=variables.size()))throw std::runtime_error("invalid original variable");}
        for(unsigned root=0;root<nodes.size();++root)if(!state[root]){
            std::vector<std::pair<unsigned,size_t>> stack{{root,0}};state[root]=1;
            while(!stack.empty()) {budget.check();auto& f=stack.back();auto const& n=nodes[f.first];if(f.second<n.children.size()){unsigned c=n.children[f.second++];if(c>=nodes.size())throw std::runtime_error("invalid AST edge");if(state[c]==1)throw std::runtime_error("cyclic AST");if(!state[c]){state[c]=1;stack.emplace_back(c,0);}}else{state[f.first]=2;postorder.push_back(f.first);stack.pop_back();}}
        }
    }
    bool official_supported()const{
        for(auto const& n:nodes){auto k=n.children.size();switch(n.op){
        case Op::Constant:case Op::Variable:break;
        case Op::And:case Op::Or:case Op::Add:case Op::Mul:break;
        case Op::Not:case Op::Neg:if(k!=1)return false;break;
        case Op::Eq:case Op::Le:case Op::Lt:case Op::Ge:case Op::Gt:case Op::Sub:if(k!=2)return false;break;
        case Op::Ite:if(k!=3||n.boolean)return false;break;
        default:return false;}}
        return true;
    }
};
inline Ast ast_from_json(Json const& j,WorkBudget& budget){Ast a;a.input_sha=j.value("input_sha","");for(auto const& v:j.at("variables"))a.variables.push_back({v.at("name"),v.at("sort")=="Bool"});
    for(auto const& n:j.at("nodes")){budget.check();Node x;x.op=op_from(n.at("op"));x.boolean=n.at("sort")=="Bool";x.children=n.value("children",std::vector<unsigned>{});x.variable=n.value("variable",-1);if(n.contains("value"))x.constant=Big(n.at("value").get<std::string>());a.nodes.push_back(std::move(x));}a.finalize(budget);return a;}
inline Json ast_json(Ast const& a){Json j={{"input_sha",a.input_sha},{"variables",Json::array()},{"nodes",Json::array()}};for(auto const& v:a.variables)j["variables"].push_back({{"name",v.name},{"sort",v.boolean?"Bool":"Int"}});for(auto const& n:a.nodes)j["nodes"].push_back({{"op",op_names()[unsigned(n.op)]},{"sort",n.boolean?"Bool":"Int"},{"children",n.children},{"variable",n.variable},{"value",n.constant.str()}});return j;}
struct ObservationTrace {std::vector<std::optional<Big>> values;std::vector<uint64_t> zero,one;bool legal=false;};
inline ObservationTrace evaluate(Ast const& ast,Assignment const& assignment,WorkBudget& budget,bool official=true,unsigned root=0){
    if(assignment.size()!=ast.variables.size())throw std::runtime_error("incomplete original assignment");
    if(official&&!ast.official_supported())throw Unsupported("official_observer_unsupported");
    ObservationTrace out;out.values.resize(ast.nodes.size());out.zero.resize(ast.nodes.size());out.one.resize(ast.nodes.size());
    struct Frame{unsigned id;size_t child;};std::vector<Frame> stack{{root,0}};
    while(!stack.empty()){
        budget.check();auto& f=stack.back();auto const& n=ast.nodes[f.id];if(out.values[f.id]){stack.pop_back();continue;}
        if(n.op==Op::Constant||n.op==Op::Variable){Big v=n.op==Op::Constant?n.constant:assignment.at(n.variable);if(n.boolean&&v!=0&&v!=1)throw std::runtime_error("invalid Boolean assignment");budget.integer(v);out.values[f.id]=v;stack.pop_back();continue;}
        auto value=[&](unsigned k)->Big const&{return *out.values[n.children.at(k)];};
        if(n.op==Op::Ite){unsigned cond=n.children.at(0);if(!out.values[cond]){stack.push_back({cond,0});continue;}unsigned child=n.children.at(value(0)!=0?1:2);if(!out.values[child]){stack.push_back({child,0});continue;}out.values[f.id]=*out.values[child];stack.pop_back();continue;}
        if(f.child&&(n.op==Op::And||n.op==Op::Or)){bool v=value(f.child-1)!=0;if((n.op==Op::And&&!v)||(n.op==Op::Or&&v)){out.values[f.id]=v;stack.pop_back();continue;}}
        if(f.child<n.children.size()){unsigned child=n.children[f.child++];if(!out.values[child])stack.push_back({child,0});continue;}
        Big result=0;switch(n.op){
        case Op::And:result=1;break;case Op::Or:result=0;break;case Op::Not:result=value(0)==0;break;
        case Op::Implies:result=value(0)==0||value(1)!=0;break;
        case Op::Xor:for(unsigned k=0;k<n.children.size();++k)result=Big((result!=0)!=(value(k)!=0));break;
        case Op::Eq:result=1;for(unsigned k=1;k<n.children.size();++k)if(value(k)!=value(0))result=0;break;
        case Op::Distinct:result=1;for(unsigned k=0;k<n.children.size();++k)for(unsigned l=k+1;l<n.children.size();++l){budget.check();if(value(k)==value(l))result=0;}break;
        case Op::Le:case Op::Lt:case Op::Ge:case Op::Gt:result=1;for(unsigned k=1;k<n.children.size();++k){bool ok=n.op==Op::Le?value(k-1)<=value(k):n.op==Op::Lt?value(k-1)<value(k):n.op==Op::Ge?value(k-1)>=value(k):value(k-1)>value(k);if(!ok)result=0;}break;
        case Op::Add:for(unsigned k=0;k<n.children.size();++k){budget.check();result+=value(k);budget.integer(result);}break;
        case Op::Mul:result=1;for(unsigned k=0;k<n.children.size();++k){budget.check();result*=value(k);budget.integer(result);}break;
        case Op::Sub:result=value(0);for(unsigned k=1;k<n.children.size();++k){budget.check();result-=value(k);budget.integer(result);}break;
        case Op::Neg:result=-value(0);break;
        case Op::Div:if(value(1)==0)throw Unsupported("integer_division_by_zero");result=value(1)>0?floor_div(value(0),value(1)):Big(-floor_div(value(0),-value(1)));break;
        case Op::Mod:if(value(1)==0)throw Unsupported("integer_modulo_by_zero");result=floor_mod(value(0),abs_big(value(1)));break;
        default:throw Unsupported("numeric_evaluation_unsupported");}
        budget.integer(result);out.values[f.id]=result;stack.pop_back();
    }
    for(unsigned i=0;i<ast.nodes.size();++i){budget.check();if(out.values[i]){out.one[i]=low64(*out.values[i])&ast.nodes[i].mask();out.zero[i]=~out.one[i]&ast.nodes[i].mask();}}
    out.legal=out.values.at(root).has_value()&&*out.values[root]!=0;return out;
}
inline ObservationTrace observe_official(Ast const& a,Assignment const& m,WorkBudget& b){return evaluate(a,m,b,true);}
inline Json assignment_json(Assignment const& m){Json j=Json::array();for(auto const& v:m)j.push_back(v.str());return j;}
inline Assignment assignment_from(Json const& j){Assignment a;for(auto const& x:j)a.emplace_back(x.get<std::string>());return a;}
inline std::string assignment_key(Assignment const& a){std::string s;for(auto const& v:a){auto t=v.str();s+=std::to_string(t.size())+":"+t;}return s;}
inline Json trace_json(ObservationTrace const& t){Json j=Json::array();for(unsigned i=0;i<t.zero.size();++i)if(t.values[i])j.push_back({i,t.zero[i],t.one[i],t.values[i]->str()});return j;}
}
