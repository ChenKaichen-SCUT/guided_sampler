void ls_sampler::r6_begin(std::unordered_map<std::string,std::string> const& map){m_r6.begin(map,mt,_cutoff);}
void ls_sampler::r6_finish(std::string const& reason,bool produced){m_r6.finish(mt,reason,produced);}
