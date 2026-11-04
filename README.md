# Expression soft guidance — V1

Frozen V1 of the new original-expression partial-bit guidance built on the
verified HighDiv source. Earlier experimental iteration names v3/v4/v5 are
retained for provenance; the approved release name is **V1**.

- Code, experiments and Chinese report: [expression_soft_guidance](expression_soft_guidance/README.zh.md).
- Full measured results: [REPORT_v5.zh.md](expression_soft_guidance/REPORT_v5.zh.md).
- Version identity: [VERSION.json](expression_soft_guidance/VERSION.json).
- Validation: [v5_final_verification.json](expression_soft_guidance/results/v5_final_verification.json).

The primary V1 profile is `ESG_MODE=soft ESG_CCSS_MS=100`. Complete projected
model exchange is an optional ablation (`ESG_CCSS_FEEDBACK=complete`).

The evaluation criterion for subsequent development is **coverage at equal
wall-clock time**. Sample count is diagnostic; fewer samples with equal or
better coverage are not a regression. Historical fixed-sample experiments
remain as evidence but are not a required metric for subsequent iterations.

This backup contains the precise frozen HighDiv source, registered inputs,
new implementation, build recipes, source/binary hashes and compact audited
results. Full raw run logs, tested binaries and libraries are preserved locally
at `expression_soft_guidance/releases/V1` and the original result directories;
they are not required to inspect the source changes and are not uploaded here.

Build on Linux/WSL with g++, make, Python 3, Boost headers and nlohmann/json
headers. Follow the commands in the project README using new build directories.
The build's optional old-workspace include path can be absent when these headers
are installed under `/usr/include`. `prepare.py` reads the included original
manifests and verifies the included HighDiv source before applying patches.
For independent Python audits, provide unmodified HighDiv Z3 Python bindings
and its library at the locations documented in `scripts/audit.py`; the exact
library used for the archived measurements is recorded by its SHA-256.

This branch is independent of previous guided_sampler implementations. No
previous development branch or uncommitted working-tree files were overwritten.
