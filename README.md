# mac-studio-mlx-serving

Reproducible benchmarks for serving fine-tuned Qwen3.5-27B on Apple Silicon via MLX, and a record of the speculative-decoding dead ends we hit.

Companion to [AImindPalace/dgx-spark-nvfp4-serving](https://github.com/AImindPalace/dgx-spark-nvfp4-serving) — that repo covers the NVIDIA DGX Spark (Blackwell / NVFP4 / MTP) path; this one covers the Mac Studio (M3 Ultra / MLX / Q4_K_M-via-llama.cpp) path using the same merged BF16 fine-tune as input.

## TL;DR

| Platform | Stack | Quant | Generation tok/s | Correctness |
|---|---|---|---|---|
| DGX Spark | vLLM + NVFP4 + MTP | 4-bit | **17.64** | ✅ |
| **Mac Studio M3 Ultra** | **MLX-LM** | **4-bit** | **~14.4 avg, 16.9 warm** | **✅** |
| Mac Studio M3 Ultra | MLX-LM | 6-bit | 9.66 | ✅ |
| Mac Studio M3 Ultra | MLX-LM + 0.8B draft spec | 4-bit | 4.76 | ✅ (but 2.8× slower) |
| Mac Studio M3 Ultra | llama.cpp FastMTP PR #20700 | Q6_K | 1.49 | ❌ garbled output |

Spark wins today by ~20%, but Mac has 3× the theoretical memory bandwidth (819 vs 273 GB/s). The gap is software maturity, not hardware — see [docs/bandwidth-efficiency.md](docs/bandwidth-efficiency.md).

## Hardware

**Mac Studio M3 Ultra**
- Chip: Apple M3 Ultra, 28 cores (20P + 8E)
- Memory: 96 GB unified @ 819 GB/s
- Storage: 3.6 TB SSD
- OS: macOS 26.4.1 (Tahoe)
- Network: 10GbE built-in, WiFi 6 (802.11ax)

**Reference: DGX Spark** (for comparison)
- Chip: NVIDIA GB10 (Grace Blackwell, aarch64)
- Memory: 128 GB unified @ 273 GB/s
- Blackwell GPU: ~100 TFLOPS FP16, native NVFP4

## Model under test

**Jarvis_2** — Qwen3.5-27B dense (hybrid Gated DeltaNet + full-attention), DoRA fine-tuned on 59K trading/finance/decision-science examples (Cycle 2, final loss 0.945, trained on 4×H200 NVL).

Architecture: 48 Gated DeltaNet (linear attention) + 16 full-attention layers, full_attention_interval=4, head_dim=256, hidden=5120, 64 layers, 262K native context.

Weights are private (`bverbeck/jarvis-2-nvfp4` on HF Hub), but every step in this repo works for any Qwen3.5-27B derivative.

## Pipeline

```
HF base (Qwen/Qwen3.5-27B, BF16)
       │
       │ + DoRA adapter (trading-dora-adapter-v2)
       ▼
Merged BF16 (on Spark or RunPod — Mac CPU merge was infeasible, see docs/merge-on-mac-failed.md)
       │
       │ rsync over ethernet (see docs/ethernet-transfer-gotcha.md)
       ▼
Mac BF16 (51 GB)
       │
       ├─────────────┐
       │             │
       │             ▼
       │    mlx_lm.convert → MLX 4-bit (14 GB) / 6-bit (20 GB)
       │
       ▼
convert_hf_to_gguf → GGUF F16 (54.6 GB) → llama-quantize → Q6_K (22 GB)
```

## Reproducing

```bash
# Mac side (one-time)
brew install cmake python@3.12 git-lfs
python3.12 -m venv .venv && source .venv/bin/activate
pip install mlx-lm huggingface_hub[cli] peft transformers torch safetensors hf_transfer
hf auth login --token $HF_TOKEN

# Pull merged BF16 from Spark (see docs/ethernet-transfer-gotcha.md for why)
bash scripts/transfer_from_spark.sh <spark-host>

# MLX 4-bit
bash scripts/convert_mlx.sh 4

# Benchmark
python scripts/benchmark.py --model ~/jarvis/jarvis2-mlx-4bit --runs 3
```

## Known issues / dead ends

1. **MLX classical spec-decode needs a matching draft.** Using vanilla Qwen3.5-0.8B as draft for trading-fine-tuned target: 42% acceptance, net **2.8× slowdown**. Would need a 0.8B trained on the same corpus.

2. **llama.cpp FastMTP PR #20700 is 9B-only.** Builds and loads on 27B, but produces garbled tokens (57% acceptance with wrong positions) and drops to 1.49 tok/s. Author's validation was only on Qwen3.5-9B. Either fix upstream or wait.

3. **CPU DoRA merge on Mac is impractical.** 27B base + DoRA via PEFT on CPU hit 28 GB RSS after 40 min and was still in "loading adapter" phase. Merge elsewhere (GPU box or Spark) and rsync.

4. **Mac ↔ Spark WiFi transfer is 10× slower than ethernet** due to dual-default-route interference. Turn off WiFi while the transfer runs. See `docs/ethernet-transfer-gotcha.md`.

5. **Mac tok/s below public reports.** Public Qwen3.5-27B MLX benchmarks report ~31 tok/s on M2/M5 Ultras. Our Jarvis_2 hits ~14–17. Under investigation — possible causes: first-run Metal kernel compilation, hybrid attention fallback paths, MLX-LM 0.31.2 regression, or the fine-tune is marginally slower than base (shouldn't be — investigating).

## License

Apache-2.0, same as the Spark sister repo.

## Citation

See [CITATION.cff](CITATION.cff). This work extends the NVFP4 serving research published at Zenodo DOI [10.5281/zenodo.19673102](https://doi.org/10.5281/zenodo.19673102).
