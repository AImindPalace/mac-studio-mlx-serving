# r/LocalLLaMA post (ready to copy)

**Title:** Benchmark: M3 Ultra 96GB vs DGX Spark — same Qwen3.5-27B fine-tune. Mac has 3× the bandwidth but Spark still wins.

**Body:**

Ran the same DoRA fine-tuned Qwen3.5-27B through both platforms. Full repo + scripts: https://github.com/AImindPalace/mac-studio-mlx-serving

## Generation tok/s (same model, same prompt, 300 tokens)

| Platform | Stack | Quant | tok/s | Notes |
|---|---|---|---|---|
| **Mac M3 Ultra** | MLX-LM 4-bit | 4-bit | **~14.4 avg** | winner on Mac |
| Mac M3 Ultra | MLX-LM 6-bit | 6-bit | 9.66 | |
| Mac M3 Ultra | MLX-LM + 0.8B draft spec | 4-bit | 4.76 | draft mismatch → 2.8× slowdown |
| Mac M3 Ultra | llama.cpp FastMTP PR #20700 | Q6_K | 1.49 | **garbled output** — PR only validated on 9B |
| **DGX Spark** | vLLM + NVFP4 + MTP | 4-bit | **17.64** | winner overall |

## The surprise

Mac M3 Ultra has 819 GB/s memory bandwidth. DGX Spark has 273 GB/s. Mac should theoretically crush at memory-bound decode.

Bandwidth utilization:
- Mac realizes **22%** of its theoretical ceiling
- Spark realizes **76%**

The 3× bandwidth advantage is real hardware but MLX isn't extracting it. Custom DeltaNet kernels don't exist, MLX 4-bit isn't a hardware op (NVFP4 is on Blackwell), and every speculation approach on Mac is either broken (llama.cpp FastMTP on 27B) or hurts for fine-tuned targets (0.8B vanilla draft).

## What you'd need to close the gap

1. MLX-LM PR [#1111](https://github.com/ml-explore/mlx-lm/pull/1111) (classical spec-decode for hybrid models) is open but the draft needs to match your fine-tune's distribution. We tested with vanilla 0.8B and got −2.8×.
2. llama.cpp PR [#20700](https://github.com/ggml-org/llama.cpp/pull/20700) (FastMTP using Qwen3.5's built-in MTP head) produces word-salad on 27B. Only validated on 9B. Comment posted there.
3. Custom MLX kernels for Gated DeltaNet — nobody's written them yet.
4. A trading-fine-tuned 0.8B draft would flip #1 from −2.8× to positive (~+1.5×).

## Also in the repo

- How to transfer 50 GB between Mac and DGX Spark fast — WiFi's dual-default-route issue will kill you if you don't disable WiFi entirely during the transfer (10× speedup from one setting)
- Why we didn't merge DoRA on Mac CPU (PEFT on 27B is impractical even at 96 GB)
- Raw benchmark JSON if you want to dig

Apache-2.0, companion to our earlier [DGX Spark NVFP4 serving repo](https://github.com/AImindPalace/dgx-spark-nvfp4-serving).

**Would love feedback** — has anyone gotten higher than ~14 tok/s on Qwen3.5-27B dense on MLX? Public benchmarks report ~31 but we can't reproduce that on Jarvis_2.

---

## Notes for when to post

- r/LocalLLaMA mods dislike promo with no engagement. Plan to answer questions for 24h.
- If asked "is the fine-tune making it slower than base?" — honest answer: we haven't tested base Qwen3.5-27B MLX side-by-side yet. Noted as open question in the repo.
- Expect "try MLX 8-bit" / "try llama.cpp main branch (not FastMTP)" replies — those are fair, add to TODO.
