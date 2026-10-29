// Test-only observational trace. Off unless explicitly requested by tests.
// No RNG use and no solver mutation. Applied identically to both libraries.
{
    static const char* path = std::getenv("HIGHDIV_NATIVE_DECISION_TRACE");
    if (path && *path) {
        std::ofstream out(path, std::ios::app);
        out << m_scope_lvl << ' ' << var << ' ' << is_pos << '\n';
    }
}
