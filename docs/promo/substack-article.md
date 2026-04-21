# Substack article

## Title options (pick one — first is my lead)

**Primary:** My Mac Studio Has More Memory Bandwidth Than NVIDIA's DGX Spark. It's Still Slower at LLM Serving.

**Alternates:**
- The Apple Silicon Paradox: 3× the Bandwidth, 20% Less Throughput
- The Gap Is Software: Why I Can't Beat a DGX Spark With a Mac Studio Today
- Hardware Won, Software Lost: A Same-Model Benchmark Across Mac Studio and DGX Spark

## Subtitle options (pick one — first is my lead)

**Primary:** I put the same fine-tuned Qwen3.5-27B on both machines. The Mac has the hardware. The Spark has the software. Here's every benchmark, every dead end, and what it means for local inference in 2026.

**Alternates:**
- A head-to-head benchmark across MLX, vLLM, and llama.cpp reveals that Apple's memory architecture is a decade ahead — and its kernels are a decade behind.
- Same Qwen3.5-27B fine-tune, two platforms, one counter-intuitive result.

---

## Article body (~1,400 words)

I ordered a Mac Studio a few weeks ago with a specific hypothesis: my NVIDIA DGX Spark has been serving my fine-tuned Qwen3.5-27B at around 17 tokens per second, and everything I knew about memory architecture suggested the Mac Studio — with its 96 GB of unified memory running at 819 GB/s versus the Spark's 273 GB/s — should simply dominate this workload.

The hypothesis was wrong. Or more precisely: the hardware hypothesis was right. The software reality was not.

This is the story of clustering the two machines together for the first time, running the same model on each, and discovering that the gap between them has almost nothing to do with silicon.

### The setup

Both machines got the exact same fine-tuned Qwen3.5-27B dense model — a DoRA fine-tune I call Jarvis_2, trained on 59,000 examples from 65 books on trading, finance, and decision science. Final training loss 0.945, 4×H200 NVL on RunPod, identical weights merged into the Qwen/Qwen3.5-27B base.

The platforms:

| Platform | Memory | Bandwidth | Compute |
|---|---|---|---|
| **Apple Mac Studio (M3 Ultra)** | 96 GB unified | **819 GB/s** | 28-core CPU (20P + 8E) + integrated GPU |
| **NVIDIA DGX Spark (GB10)** | 128 GB unified | 273 GB/s | Grace CPU + Blackwell GPU (~100 TFLOPS FP16, native NVFP4) |

The Mac has 3× the raw bandwidth. For memory-bandwidth-bound workloads — which LLM decoding absolutely is — the Mac should win cleanly. The theoretical ceiling for decoding at 4-bit is roughly `bandwidth ÷ model_size`:

- Mac at 14 GB MLX 4-bit: **58.5 tok/s theoretical**
- Spark at 19 GB NVFP4: **14.4 tok/s theoretical**

On paper, the Mac should hit around 4× the Spark's throughput. It's the kind of hardware advantage that doesn't even need to be argued about.

### The results

Here's what I actually measured, running the same model, the same prompt, and the same token budget on both machines:

| Configuration | Gen tok/s | Output correct? |
|---|---|---|
| DGX Spark, vLLM + NVFP4 + MTP | **17.64** | ✅ |
| **Mac, MLX 4-bit plain** | **~14.4 avg** | ✅ |
| Mac, MLX 6-bit plain | 9.66 | ✅ |
| Mac, MLX 4-bit + 0.8B draft spec-decode | 4.76 | ✅ (but 2.8× slower) |
| Mac, llama.cpp FastMTP (PR #20700) | 1.49 | ❌ garbled |

The Spark wins by about 20%. The Mac — with 3× the memory bandwidth — is slower. And every attempt to speed the Mac up using speculative decoding either hurt performance or broke correctness.

### Why this happens

Bandwidth utilization is the whole story:

| | Theoretical ceiling | Measured | % of ceiling |
|---|---|---|---|
| Mac plain decode | 58 tok/s | ~14 | **22%** |
| Spark plain decode (no MTP) | 14 tok/s | ~11 | **76%** |

The Spark extracts 76% of its bandwidth. The Mac extracts 22%. NVIDIA's decade-old CUDA stack, combined with purpose-built vLLM kernels and native NVFP4 hardware ops on Blackwell, are pulling almost everything out of the Spark's memory interface. Apple's MLX stack — three years old and still maturing — is leaving more than three quarters on the table.

Four specific reasons contribute to this:

**1. MLX is young.** The vLLM + CUDA + cuBLAS stack has had more than a decade of kernel tuning, including specific tuning for hybrid attention architectures like Qwen3.5's Gated DeltaNet. MLX's default paths fall back to generic implementations for linear attention layers.

**2. NVFP4 is a native hardware op on Blackwell.** Weights flow directly into matrix multiplies without a dequantize step. MLX's 4-bit quantization is closer to a software optimization — the model gets dequantized per layer before compute. You save memory. You don't save memory bandwidth the same way.

**3. Speculative decoding works on the Spark, nowhere else here.** Qwen3.5 ships with a built-in Multi-Token Prediction head — a small auxiliary layer trained to guess the next few tokens so the main model can verify them in parallel. vLLM's `qwen3_next_mtp` method uses this and gets ~60% draft acceptance at zero quality loss. That alone is worth about 60% of the measured Spark speedup.

**4. Every Mac speculation path is broken today.** I tested two. The classical draft-model approach (MLX-LM PR #1111) works — pair a large target with a smaller draft, verify in parallel — but only if the draft's distribution matches the target. When you pair a fine-tuned 27B with a vanilla 0.8B draft, the acceptance rate craters to 57% and the overhead of running the draft plus verifying its tokens makes the whole thing 2.8× *slower* than not speculating at all. The alternative — llama.cpp's FastMTP PR #20700, which uses Qwen3.5's built-in MTP head like vLLM does — has been validated only on the 9B variant. On my 27B model it produces word-salad output at 1.49 tok/s.

### The counter-intuitive lesson

I've spent a week poking this problem from every angle, and here's the uncomfortable conclusion: **the gap between the Mac Studio and the DGX Spark at LLM serving in April 2026 has almost nothing to do with hardware**. The Mac has the bandwidth. The Mac has the memory. The Mac has the compute. What the Mac doesn't have yet is the software ecosystem: hand-tuned kernels for hybrid attention, a mature speculative-decoding stack, native hardware quantization ops, and a decade of accumulated performance work.

This is temporary. MLX is iterating fast — the PR that fixed hybrid-model speculative decoding just landed in the current release cycle. The llama.cpp FastMTP work will eventually extend past 9B. Someone will write hand-tuned Metal kernels for Gated DeltaNet. When that happens, the Mac's 4× theoretical headroom stops being theoretical.

My prediction: the benchmark table above flips within 12–18 months. The Mac wins when MLX catches up to CUDA, not when Apple ships new silicon. Until then, if you want to serve a 27B fine-tune as fast as possible at home, the DGX Spark with NVFP4 and working MTP is still the winning stack.

### Dead ends I recommend skipping

Three things I tried that didn't work, in case they save you time:

**Merging a DoRA adapter into a 27B base on Mac CPU.** Looks fine on paper — the Mac has enough RAM. In practice, PEFT's adapter merge on a 27B model sits in "loading adapter" for an hour with resident memory slowly climbing. The bottleneck is per-column DoRA magnitude vector processing in Python, not memory. I killed the run after 40 minutes. Merging the adapter on a GPU box (or on the Spark, which I did via a pre-merged checkpoint) then rsync'ing over gigabit ethernet is dramatically faster.

**Transferring the 51 GB merged model over WiFi.** The Mac was on WiFi 6. In theory that's 135 MB/s. In practice, with both ethernet and WiFi interfaces up and routing split between two default routes, the transfer bursts to 80 MB/s and drops to single digits in a sawtooth pattern. Disabling WiFi entirely — `networksetup -setairportpower en1 off` — pinned the route to ethernet and gave me a clean ~100 MB/s. That one setting was a 10× speedup.

**Using rsync.** Even with `--whole-file --inplace`, rsync introduced ~80% idle overhead — probably per-file stat and checksum roundtrips over SSH. Replacing it with a raw `tar cf - | ssh | tar xf -` pipe using AES-GCM (which has hardware acceleration on Apple Silicon) pinned throughput at the network's actual ceiling.

### What to do with this

If you're an MLX maintainer: the PR #1111 spec-decode fix works on 27B dense hybrid too. Ship it.

If you're the FastMTP PR #20700 author: 27B validation fails badly. The 9B number doesn't generalize. Happy to provide a repro.

If you're running a fine-tuned Qwen3.5-27B at home: Spark + NVFP4 + MTP still wins today. The Mac is a great backup inference box and a better-than-Spark model development machine (more unified memory, more cores). For serving specifically, wait another release cycle.

All the benchmarks, scripts, and raw JSON are in the repo: **https://github.com/AImindPalace/mac-studio-mlx-serving**

DOI and Zenodo archive coming once the integration finishes syncing.

---

## Notes before publishing

- Aim for ~6am Pacific / 9am Eastern posting time
- Add a prominent link to the GitHub repo in the opening
- Suggested tags: `llm`, `apple-silicon`, `nvidia`, `mlx`, `benchmarks`, `local-inference`
- Consider cross-posting abbreviated version on LinkedIn (400 words) and pinning to your profile
