# Hacker News post (ready to copy)

**Title:** Mac Studio M3 Ultra has 3× the memory bandwidth of DGX Spark but loses at LLM serving — here's why

**URL:** https://github.com/AImindPalace/mac-studio-mlx-serving

**Text (optional — HN treats the URL as primary):**

Put the same DoRA fine-tuned Qwen3.5-27B on both platforms and benchmarked side-by-side. Results are counter-intuitive:

- Mac M3 Ultra: 819 GB/s memory bandwidth, 14 GB 4-bit model → theoretical ceiling 58 tok/s, measured 14 tok/s (25% efficiency)
- DGX Spark: 273 GB/s memory bandwidth, 19 GB NVFP4 model → theoretical ceiling 14 tok/s, measured 11 tok/s plain / 17.6 tok/s with MTP (76%+ efficiency)

Mac has **3× the raw bandwidth** and still loses. The gap is entirely software:

1. MLX is ~3 years old vs vLLM+CUDA 10+ years of kernel tuning
2. Qwen3.5's Gated DeltaNet (hybrid linear+full attention) has tuned FLA kernels on CUDA, fallback paths on MLX
3. NVFP4 is a native Blackwell hardware op; MLX 4-bit dequantizes per layer
4. Every Mac speculation path is broken today: classical spec-decode hurts on fine-tunes (2.8× slower) and llama.cpp FastMTP generates word-salad on 27B

Repo documents the full pipeline + dead ends: https://github.com/AImindPalace/mac-studio-mlx-serving

The prediction: Mac closes this gap within 12–18 months as MLX's hybrid-attention kernels mature. Today, Spark wins by ~20%.

---

## Notes for when to post

- Best times: 7–10am US East weekday mornings
- Don't editorialize beyond what's in the docs — HN reads tone
- If it takes off, expect "why not test on Apple M3 Max/M4 Ultra" questions; honest answer is we only had M3 Ultra
