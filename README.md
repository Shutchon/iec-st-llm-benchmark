# IEC-ST-LLM-Benchmark

**A Benchmark for Evaluating Local Large Language Models on IEC 61131-3 Structured Text Code Generation**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Dataset: CC BY 4.0](https://img.shields.io/badge/Dataset-CC_BY_4.0-blue.svg)](LICENSE-DATASET)

## Overview

This repository contains the complete benchmark suite, evaluation pipeline, and experimental data for our study:

> Shutchon Premchaisawatt, Krit Tashoo, and Narong Boonsaner. **Benchmarking Local Large Language Models for IEC 61131-3 Structured Text Code Generation: An Offline, Compiler-Verified Evaluation.** *Submitted to IEICE Transactions on Information and Systems* (2026).

We evaluate **8 open-weight LLMs** (Qwen3-Coder-30B, GPT-OSS-20B, Qwen3.8-27B, Qwen3.5-27B, Gemma4-12B, Qwen2.5-Coder-14B, DeepSeek-Coder-V2-Lite-16B, Llama-3.1-8B) served through Ollama on a single NVIDIA L4 GPU, across **3,600 trials** (8 models × 3 prompting strategies × 30 tasks × 5 runs).

## Key Results

| Model | pass@1 | pass@5 | Throughput |
|-------|--------|--------|------------|
| Qwen3.8-27B | 0.49 | 0.64 | 33 tok/s |
| GPT-OSS-20B | 0.36 | 0.62 | 58 tok/s |
| Qwen3-Coder-30B | 0.26 | 0.39 | 82 tok/s |
| Gemma4-12B | 0.23 | 0.42 | 69 tok/s |
| Qwen3.5-27B | 0.22 | 0.43 | 14 tok/s |
| Qwen2.5-Coder-14B | 0.10 | 0.24 | 27 tok/s |
| Llama-3.1-8B | 0.07 | 0.11 | 50 tok/s |
| DS-Coder-V2-16B | 0.03 | 0.10 | 106 tok/s |

## Repository Structure

```
iec-st-llm-benchmark/
├── benchmark/
│   ├── tasks.json              # IEC-ST-30 dataset (30 tasks + truth tables)
│   ├── task_definitions.py     # Source of truth for dataset
│   └── README.md               # Dataset documentation
├── plc_llm_benchmark_lab.py    # Main evaluation harness (3-level pipeline)
├── tools/
│   ├── level2_harness.py       # Scan-cycle simulation (virtual time)
│   ├── build_tasks_json.py     # Dataset build + validation
│   ├── rq4_taxonomy.py         # Failure-mode taxonomy analysis
│   ├── make_figures.py         # Publication figures
│   ├── stat_analysis.py        # Statistical analysis (Friedman, Wilcoxon, ANOVA)
│   ├── matiec/                 # MatIEC compiler (build instructions in BUILD_NOTES.md)
│   └── gcp/                    # Cloud VM setup scripts
├── results/
│   ├── benchmark_results.jsonl # Raw trial records (3,600 trials)
│   ├── stats_summary.json      # Statistical test results
│   ├── pass_at_k.json          # Per-task pass@k
│   └── taxonomy.json           # Failure-mode taxonomy
├── figures/                    # Publication-quality figures (300 DPI)
├── PROTOCOL.md                 # Frozen experimental protocol (pre-registered)
└── findings_log.md             # Empirical findings log (F-01 through F-19)
```

## Quick Start

### Prerequisites
- Python 3.10+ with `requests`, `scipy`, `statsmodels`, `pandas`, `matplotlib`
- [Ollama](https://ollama.com) with any of the evaluated models
- [MatIEC](https://github.com/beremiz/matiec) compiler (build instructions in `tools/BUILD_NOTES.md`)
- A C compiler (gcc/clang) for Level-2 functional verification

### Run the benchmark

```bash
# Build and validate the dataset
python3 tools/build_tasks_json.py

# Run evaluation (single model, all tasks, one strategy)
python3 plc_llm_benchmark_lab.py --models qwen3.8:27b --strategies zero_shot --runs 1

# Full protocol (all 8 models, 3 strategies, 5 runs)
python3 plc_llm_benchmark_lab.py --runs 5 --out benchmark_results.jsonl

# Statistical analysis
python3 stat_analysis.py benchmark_results.jsonl
```

### Three-Level Evaluation Pipeline

1. **Level 1 — Syntax:** Generated ST is compiled by MatIEC (`iec2c`). An empty file compiles successfully (a pitfall); our pipeline rejects empty responses.
2. **Level 2 — Functional:** The FB under test is compiled to C and driven by a harness that advances a virtual clock and injects inputs each scan cycle, comparing outputs against truth tables.
3. **Level 3 — Efficiency:** Latency and tokens/s are recorded per trial.

## Dataset: IEC-ST-30

30 function-block tasks across three difficulty tiers:

| Tier | Count | Examples |
|------|-------|----------|
| Basic | 10 | AND gate, TON timer, CTU counter, TOF timer |
| Intermediate | 10 | Star-delta starter, conveyor sorting, bottle filling, traffic lights |
| Advanced | 10 | PID controller, CRC-8, batch reactor FSM, Modbus packing |

All reference solutions pass three validation layers:
1. MatIEC compilation
2. Schema-checked truth tables
3. Scan-cycle simulation (the same harness used for evaluation)

## Citation

```bibtex
@misc{iecst30,
  title = {{IEC-ST-30}: A Benchmark for Local LLM Evaluation on IEC 61131-3 Structured Text},
  author = {Premchaisawatt, Shutchon and Tashoo, Krit and Boonsaner, Narong},
  year = {2026},
  howpublished = {\url{https://github.com/iec-st/iec-st-llm-benchmark}}
}
```

## License

- **Code:** MIT License (see [LICENSE](LICENSE))
- **Dataset:** CC BY 4.0 (see [LICENSE-DATASET](LICENSE-DATASET))

## Acknowledgments

This work was supported by Rajamangala University of Technology Isan, Khon Kaen Campus. Experimental compute was provided by Google Cloud Platform (spot GPU instances).
