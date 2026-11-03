    bool commit(z3::model const& m,z3::expr const& formula,std::ofstream& samples) {
        const double start_wall=refinement::wall_now(),start_cpu=refinement::cpu_now(),native_ready=elapsed();
        const double optional_before_wall=split->budget.optional_wall,optional_before_cpu=split->budget.optional_cpu;
        struct Charge {
            refinement::BudgetLedger& b;double w,c,ow,oc;
            ~Charge(){b.mandatory_wall+=std::max(0.0,refinement::wall_now()-w-(b.optional_wall-ow));b.mandatory_cpu+=std::max(0.0,refinement::cpu_now()-c-(b.optional_cpu-oc));}
        } charge{split->budget,start_wall,start_cpu,optional_before_wall,optional_before_cpu};
        z3::model snapshot(c);std::map<std::string,Big> values;refinement::Assignment native;
        Json typed=Json::array();std::string key;
        for(auto const& v:variables){auto value=m.eval(v,false);
            if(v.is_int()&&!value.is_numeral())value=c.int_val(0);
            if(v.is_bool()&&!value.is_true()&&!value.is_false())value=c.bool_val(false);
            auto d=v.decl();snapshot.add_const_interp(d,value);
            Big exact=v.is_int()?numeral(value):Big(value.is_true());auto name=d.name().str(),val=exact.str();
            native.push_back(exact);values[name]=exact;key+=std::to_string(name.size())+":"+name+(v.is_int()?"I":"B")+std::to_string(val.size())+":"+val;
            typed.push_back({{"name",name},{"sort",v.is_int()?"Int":"Bool"},{"value",val}});
        }
        bool legal=snapshot.eval(formula,true).is_true();for(auto const& h:real_hard)legal=legal&&snapshot.eval(h,true).is_true();
        if(!legal){std::ofstream f(dir+"/native_models.jsonl",std::ios::app);f<<Json({{"query",query},{"typed",typed},{"legal",false}}).dump()<<'\n';throw std::runtime_error("native snapshot violates formula or actual hard conditions");}
        bool native_observing=guidance&&guidance->observing();auto observer_start=Clock::now();
        auto ev=native_ast().evaluate(values);if(native_observing)guidance->record_observer(std::chrono::duration<double>(Clock::now()-observer_start).count());auto trace=refinement::trace_from_native(native_ast(),ev);
        auto accepted=split->accept(native,trace);
        Json native_rec={{"native_ready",native_ready},{"query",query},{"source",source},{"typed",typed},{"assignment",refinement::assignment_json(native)},
            {"native_event_id",accepted.native_event_id},{"native_duplicate",accepted.native_duplicate},{"legal",true},
            {"actual_observations",refinement::trace_json(trace)},{"model_hash",identity_hash(key)},
            {"formal_index",accepted.native_event_id-1},{"new_observed",ev.observed},{"new_covered",ev.covered}};
        // Advance native feedback before output selection. q is never passed here.
        if(accepted.accepted_for_native_history&&guidance){
            if(native_observing&&source=="CDCL"){auto started=Clock::now();guidance->pending_outcomes=guidance->outcomes(ev);guidance->charge("outcome_evaluation_seconds",std::chrono::duration<double>(Clock::now()-started).count());}
            guidance->formal_record(native_rec);if(native_observing)guidance->commit(ev);
        }
        {std::ofstream f(dir+"/native_models.jsonl",std::ios::app);f<<native_rec.dump()<<'\n';f.flush();if(!f)throw std::runtime_error("native archive failed");}
        if(!accepted.accepted_for_native_history)return false;
        if(remaining()<=0||interrupted){++split->deadline_missed_after_native_ready;return true;}
        bool detail_logged=false;
        auto result=split->choose(accepted,remaining(),
            [&](refinement::WorkBudget& b){return refinement::copy_original_ast(native_ast(),variables,input_sha,b);},
            [&](refinement::Refiner const& r,refinement::WorkBudget& b){std::ofstream f(dir+"/refinement_metadata.json");f<<Json({{"ast",refinement::ast_json(r.ir.ast)},{"algebra",r.metadata()}}).dump()<<'\n';f.flush();if(!f)throw std::runtime_error("refinement metadata I/O failure");b.check();},
            [&](refinement::WorkBudget& b){std::vector<refinement::AffineIR> hard;for(auto const& h:real_hard){b.check();OriginalAst ast(h);hard.push_back(refinement::compile_affine_ir(refinement::copy_original_ast(ast,variables,"real_hard",b),b,split->repair_configuration));}return hard;},
            [&](refinement::RefinementResult const& r,refinement::WorkBudget&){std::ofstream f(dir+"/refinement_candidates.jsonl",std::ios::app);auto j=refinement::refinement_json(r);j["native_event_id"]=accepted.native_event_id;f<<j.dump()<<'\n';f.flush();if(!f)throw std::runtime_error("candidate log I/O failure");detail_logged=true;});
        auto const& chosen=result.chosen?result.chosen->assignment:native;
        auto const& chosen_trace=result.chosen?result.chosen->trace:trace;
        bool duplicate=split->output.unique.count(refinement::assignment_key(chosen));
        Json decision={{"native_event_id",accepted.native_event_id},{"reason",result.reason},{"replaced",bool(result.chosen)},
            {"output_duplicate",duplicate},{"candidate_detail_logged",detail_logged},{"budget",refinement::budget_json(split->budget)}};
        {std::ofstream f(dir+"/refinement_decisions.jsonl",std::ios::app);f<<decision.dump()<<'\n';f.flush();if(!f)throw std::runtime_error("decision log failed");}
        if(duplicate){split->deliver(chosen,chosen_trace,bool(result.chosen),false);return true;}
        std::string line,outkey;Json outtyped=Json::array();
        for(unsigned i=0;i<variables.size();++i){auto name=variables[i].decl().name().str(),val=chosen[i].str();line+=name+":"+val+";";outkey+=std::to_string(name.size())+":"+name+(variables[i].is_int()?"I":"B")+std::to_string(val.size())+":"+val;outtyped.push_back({{"name",name},{"sort",variables[i].is_int()?"Int":"Bool"},{"value",val}});}
        refinement::WorkBudget mandatory;auto gain=refinement::marginal_gain(chosen_trace,split->output.observations,mandatory);
        samples<<raw<<": "<<line<<'\n';samples.flush();if(!samples)throw std::runtime_error("output raw flush failed");
        Json rec={{"kind","prepare"},{"raw_index",raw++},{"formal_index",formal},{"native_event_id",accepted.native_event_id},
            {"query",query},{"source",source},{"legal",true},{"duplicate",false},{"model_hash",identity_hash(outkey)},
            {"typed",outtyped},{"replaced",bool(result.chosen)},{"output_complete",elapsed()},
            {"new_observed",gain.observed},{"new_covered",gain.covered},{"actual_observations",refinement::trace_json(chosen_trace)}};
        receipts<<rec.dump()<<'\n';receipts.flush();models<<rec.dump()<<'\n';models.flush();
        if(!receipts||!models)throw std::runtime_error("output prepare flush failed");
        double commit_begin=elapsed();bool timely=commit_begin<wall&&!interrupted;
        receipts<<Json({{"kind","commit"},{"raw_index",rec["raw_index"]},{"formal_index",formal},{"commit_begin",commit_begin},{"timely",timely}}).dump()<<'\n';receipts.flush();
        double complete=elapsed();receipts<<Json({{"kind","confirm"},{"raw_index",rec["raw_index"]},{"commit_complete",complete},{"timely",timely&&complete<wall&&!interrupted}}).dump()<<'\n';receipts.flush();
        if(!receipts)throw std::runtime_error("output confirm flush failed");
        auto delivered=split->deliver(chosen,chosen_trace,bool(result.chosen),timely&&complete<wall&&!interrupted);
        formal=split->output.committed_count;
        if(delivered.committed&&result.chosen&&result.chosen->gain.covered>result.base_gain.covered)++split->covered_replacements;
        return true;
    }
