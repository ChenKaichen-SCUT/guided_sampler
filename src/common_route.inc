    unsigned m_round1_route_epoch = 0;
    void round1_route(char const* backend) {
        auto path=std::getenv("HIGHDIV_ROUTE_LOG");
        if (!path || !*path) return;
        std::ofstream out(path,std::ios::app);
        out << "{\"check_epoch\":" << m_round1_route_epoch
            << ",\"solver\":" << reinterpret_cast<uintptr_t>(this)
            << ",\"backend\":\"" << backend << "\"}\n";
        out.flush();
    }
