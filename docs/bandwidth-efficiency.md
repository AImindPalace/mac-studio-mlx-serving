# Why Spark beats Mac despite the Mac having more bandwidth

## The numbers

| | Memory bandwidth | Model size (4-bit) | Theoretical decode tok/s | **Measured (plain)** | **% realized** |
|---|---|---|---|---|---|
| Mac M3 Ultra | **819 GB/s** | 14 GB (MLX 4-bit) | 58.5 | **~14.4** | **25%** |
| DGX Spark Blackwell | 273 GB/s | 19 GB (NVFP4) | 14.4 | **~11** | **76%** |

The Mac has **3× the raw bandwidth**. The theoretical ceiling for bandwidth-bound decode is nearly **4× higher** on the Mac. And yet today, Spark's plain decode matches the Mac and Spark+MTP beats it.

## The gap is software, not hardware

1. **MLX is younger (~3 years)** than the vLLM+CUDA+cuBLAS stack (10+ years of tuning). Kernel-per-op efficiency gap is ~3×.

2. **Hybrid Qwen3.5 architecture** uses Gated DeltaNet (linear attention). vLLM+FLA has hand-tuned DeltaNet kernels. MLX relies on fallback paths. The `"fast path is not available"` warning at merge time also applies (in spirit) to inference — the hybrid layer isn't operating at Apple Silicon's peak.

3. **NVFP4 is native hardware** on Blackwell. Weight → matmul without a dequantize step. MLX 4-bit dequants per layer before compute.

4. **Working MTP** — Spark has Qwen3.5's built-in MTP head accepted through `qwen3_next_mtp` vLLM method, giving ~1.6× speedup with minimal quality loss. Every speculation path we tried on Mac either hurt (draft model mismatch, −2.8×) or broke correctness (llama.cpp FastMTP PR #20700 on 27B).

## The prediction

Mac's theoretical headroom (58 vs 14 tok/s plain) is real. As MLX matures — especially with native hybrid-attention kernels and a working MTP implementation — the Mac should pull ahead by 2–4×. The gap closes in software.

Today: Spark wins by ~20%. Probably flips within 12–18 months.

## What would actually change it

- **MLX-LM PR #1111** merges and handles 27B dense hybrid correctly (classical spec-decode with a matched draft)
- **llama.cpp FastMTP** validated + fixed for 27B (PR #20700 is 9B-only today)
- **MLX internal-MTP implementation** (issue #872 — open, no PR)
- **Custom DeltaNet Metal kernels** for MLX
- **A trading-fine-tuned 0.8B draft model** — single RunPod run, would make classical spec-decode on Mac actually useful (target+draft distribution match)
