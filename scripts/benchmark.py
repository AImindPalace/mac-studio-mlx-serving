#!/usr/bin/env python3
"""Benchmark MLX-LM generation. Reports median generation tok/s across runs.

Usage: python benchmark.py --model ~/jarvis/jarvis2-mlx-4bit --runs 3
"""
import argparse
import json
import re
import subprocess
import sys
import time

PROMPT = (
    "Explain the Kelly criterion for position sizing in trading, "
    "and give a worked example."
)


def run_once(model: str, max_tokens: int, temp: float) -> dict:
    t0 = time.time()
    result = subprocess.run(
        [
            sys.executable, "-m", "mlx_lm", "generate",
            "--model", model,
            "--prompt", PROMPT,
            "--max-tokens", str(max_tokens),
            "--temp", str(temp),
        ],
        capture_output=True, text=True, check=True,
    )
    wall = time.time() - t0
    out = result.stdout
    gen_match = re.search(r"Generation:\s+(\d+)\s+tokens,\s+([0-9.]+)\s+tokens-per-sec", out)
    pp_match = re.search(r"Prompt:\s+(\d+)\s+tokens,\s+([0-9.]+)\s+tokens-per-sec", out)
    mem_match = re.search(r"Peak memory:\s+([0-9.]+)\s+GB", out)
    return {
        "wall_s": round(wall, 2),
        "gen_tok_s": float(gen_match.group(2)) if gen_match else None,
        "prefill_tok_s": float(pp_match.group(2)) if pp_match else None,
        "peak_mem_gb": float(mem_match.group(1)) if mem_match else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--temp", type=float, default=0.6)
    ap.add_argument("--warmup", type=int, default=1, help="throwaway runs before measurement")
    args = ap.parse_args()

    for i in range(args.warmup):
        print(f"[warmup {i+1}/{args.warmup}] ...", file=sys.stderr)
        run_once(args.model, 50, args.temp)

    results = []
    for i in range(args.runs):
        print(f"[run {i+1}/{args.runs}] ...", file=sys.stderr)
        r = run_once(args.model, args.max_tokens, args.temp)
        print(f"  gen={r['gen_tok_s']} tok/s  prefill={r['prefill_tok_s']} tok/s  peak_mem={r['peak_mem_gb']} GB",
              file=sys.stderr)
        results.append(r)

    gens = [r["gen_tok_s"] for r in results if r["gen_tok_s"]]
    prefills = [r["prefill_tok_s"] for r in results if r["prefill_tok_s"]]
    summary = {
        "model": args.model,
        "runs": results,
        "median_gen_tok_s": sorted(gens)[len(gens) // 2] if gens else None,
        "median_prefill_tok_s": sorted(prefills)[len(prefills) // 2] if prefills else None,
        "max_peak_mem_gb": max((r["peak_mem_gb"] or 0) for r in results),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
