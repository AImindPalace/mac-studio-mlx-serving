#!/usr/bin/env bash
# Convert merged BF16 HF model to MLX quantized format.
# Usage: convert_mlx.sh <bits> [input_dir] [output_dir]
# Example: convert_mlx.sh 4

set -euo pipefail

BITS="${1:-4}"
INPUT="${2:-$HOME/jarvis/merged}"
OUTPUT="${3:-$HOME/jarvis/jarvis2-mlx-${BITS}bit}"

if [[ ! -d "$INPUT" ]]; then
  echo "Input dir missing: $INPUT"; exit 1
fi

echo "Converting $INPUT -> $OUTPUT at ${BITS}-bit..."
python3 -m mlx_lm convert \
  --hf-path "$INPUT" \
  -q --q-bits "$BITS" \
  --mlx-path "$OUTPUT"

echo
echo "Done. Output size:"
du -sh "$OUTPUT"
echo
echo "Bits-per-weight (from log above, typically reads ~${BITS}.5)"
