# Mac ↔ Spark transfer: WiFi will ruin your day

When moving the 51 GB merged BF16 from Spark to Mac over your LAN, you'll get **10× slower throughput on WiFi even when both IPs are on the same subnet**, due to macOS dual-default-route behavior.

## Symptoms

- `rsync -avh --progress` shows **brief 80 MB/s bursts** but **~7–11 MB/s sustained**
- `tail ~/rsync.log` shows repeated "The read operation timed out" + "Trying to resume download..."
- Mac has two active IPs (one on ethernet, one on WiFi)
- Both IPs on 10.0.0.0/24 — packets can take either route and the stack switches mid-stream

## Minimum diagnostic

```bash
# On Mac
ifconfig | grep "inet " | grep -v 127.0.0.1
# If you see TWO IPs (one on en0 ethernet, one on en1 WiFi), this is the issue.

netstat -rn -f inet | grep default
# Two default routes = trouble.
```

## Fix

**Disable WiFi during the transfer.** Don't just disconnect — fully power it off:

```bash
networksetup -setairportpower en1 off
```

Then start the transfer. Re-enable after with `on`.

## What we measured

| | Average throughput |
|---|---|
| WiFi only (no ethernet) | ~7.5 MB/s |
| Ethernet + WiFi both up | 7–11 MB/s (bursty) |
| **Ethernet only (WiFi off)** | **~100 MB/s** (near gigabit) |
| Plain SSH pipe (reference) | ~57 MB/s with AES-GCM |

## The actual transfer command we use

rsync introduces ~80% idle overhead even with `--whole-file --inplace`. Use a raw tar stream instead:

```bash
# From Mac, pulling from Spark
ssh -c aes256-gcm@openssh.com -o Compression=no brandonv@spark \
  "cd ~/models && tar cf - Jarvis_27B_trading" \
  | tar xf - -C ~/jarvis/merged --strip-components=1
```

Why this is faster than rsync:
- No per-file stat / checksum roundtrip
- No delta-xfer protocol overhead
- AES-GCM is hardware-accelerated on Apple Silicon (3× cipher throughput vs ChaCha20-Poly1305 default)
- Compression off (weights don't compress well)

## Why the router also matters

The effective throughput is also router-limited if you go Spark → router → Mac. Our NETGEAR did ~100 MB/s routed switching. A direct Mac ↔ Spark ethernet cable (static IPs, no router) would likely do full 112+ MB/s gigabit line rate.
