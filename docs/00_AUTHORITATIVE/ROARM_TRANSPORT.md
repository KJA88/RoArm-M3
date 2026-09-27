# RoArm-M3 Production Transport Architecture

Status: **LIVE VERIFIED**

Verified baseline commit: `f5edfb6df758dffb5ff3764b7d9a91e0d8c8649b`

Verified recovery branch: `udp-live-verified-2026-09-26`

## Decision

RoArm production communication is split by responsibility.

- **HTTP JSON is the control and status plane.**
- **Sequenced UDP on port 4210 is the continuous trajectory data plane.**
- **USB serial is a service, firmware-flashing, recovery, and diagnostic interface only. It is not a production runtime fallback.**

This decision exists to keep discrete control operations reliable while removing per-point request/response behavior from continuous trajectory streaming.

## Network Contract

Normal wireless topology:

- Raspberry Pi trajectory source: `192.168.4.2`
- RoArm-M3 controller: `192.168.4.1`
- Required Pi interface: `wlan0`
- Trajectory UDP port: `4210`

The Pi runtime refuses trajectory execution unless the kernel route to `192.168.4.1` resolves through `wlan0` with source `192.168.4.2`.

## HTTP Responsibilities

HTTP remains authoritative for discrete operations around a trajectory, including:

- `T210` torque control
- `T104` start pose
- `T104` return pose
- `T105` feedback/readback
- configuration and other non-streaming control operations

`T105` remains available while a UDP trajectory owns motion authority.

## UDP Responsibilities

UDP is used only for continuous `T1041` trajectory points.

Each datagram uses the envelope:

```json
{"sid":7,"seq":0,"cmd":{"T":1041,"x":265.0,"y":0.0,"z":250.0,"t":0.3,"r":0,"g":3.0}}
```

Contract:

- `sid` is a non-zero 32-bit stream identifier generated for each trajectory run.
- `seq` starts at `0` and increments by exactly one for each accepted point.
- Datagram size must not exceed 384 bytes.
- Only the Pi source `192.168.4.2` is accepted for trajectory authority.
- A new stream starts only with `seq == 0`.
- While a stream is active, only the same `sid` and exact next `seq` are accepted.
- Duplicate, stale, skipped, or foreign stream packets are rejected.
- UDP is one-way; there is no per-point reply.

## Motion Authority and Watchdog

While a valid UDP trajectory stream is active:

- UDP owns continuous-motion authority.
- HTTP `T105` feedback remains allowed.
- Competing HTTP motion/control requests are blocked rather than interleaved with the stream.

If no valid trajectory point is accepted for approximately 100 ms, the firmware watchdog releases UDP trajectory authority. Normal HTTP control then resumes.

The Pi sender must not burst delayed points to catch up. If it falls more than one trajectory interval behind, the run stops rather than replaying a backlog.

## Runtime Command Behavior

The production command:

```text
python3 roarm run lissajous
```

and the continuous `circle` and `spiral` patterns use sequenced UDP for their `T1041` points.

The lesson files remain the source of the existing trajectory geometry, but they are not executed as serial programs. There is no `/dev/ttyUSB0` runtime path and no serial fallback for these continuous patterns.

Discrete named poses remain on HTTP.

## Live Verification — 2026-09-26

The UDP firmware was flashed to the physical RoArm-M3 application partition and the wireless HTTP path was verified afterward.

Live checks confirmed:

- Pi route: `192.168.4.2` -> `192.168.4.1` over `wlan0`
- HTTP `T105` remained functional
- UDP `T1041` motion executed on the physical arm
- During an active UDP stream, HTTP `T405` returned `{"blocked":1}`
- After the watchdog release interval, HTTP `T405` worked normally again
- No USB serial connection was required for normal operation

Production trajectory validation then completed:

- Lissajous: 5 consecutive successful runs, 304 motion packets each
- Circle: 1 successful run, 543 motion packets
- Spiral: 1 successful run, 722 motion packets
- Total: **2,785 motion packets across 7 consecutive successful production runs**
- All runs reported `transport: "udp"`
- All runs reported `serial_opened: false`
- All runs reported `udp_opened: true`
- All runs completed with `ok: true` and `reason: "PATTERN_FINISHED"`
- All preflight checks succeeded on the first fresh `T105` attempt
- No transport dropouts occurred during this verification sequence

## Acceptance Criteria

Transport health is evaluated by communication behavior, sequence handling, watchdog behavior, successful command completion, and absence of transport failures.

Do **not** use millimeter-perfect Cartesian endpoint readback as a transport acceptance criterion. The RoArm-M3 is a hobby-grade mechanism with known repeatability, backlash, deadband, servo, and firmware-IK limitations. Transport debugging must not reopen precision-calibration work unless a new failure demonstrates that it is materially relevant.

## Recovery and Service

Use USB only when firmware flashing, low-level recovery, or direct diagnostics are required.

For normal SYZYGY operation:

1. Pi connects to the RoArm-M3 Wi-Fi AP.
2. HTTP performs route/preflight/discrete control and readback.
3. Sequenced UDP performs continuous trajectory streaming.
4. The watchdog releases trajectory authority on stream loss.

Do not reintroduce serial as an automatic runtime fallback. A failed wireless trajectory should fail explicitly so the actual network, power, sender, or firmware fault remains observable.

## Change Policy

This transport is a live-verified baseline. Do not modify the UDP protocol, authority rules, cadence behavior, or fallback policy merely to clean up code or pursue theoretical improvements.

Change the transport only when an observed requirement or reproducible failure justifies it, and preserve a known-good recovery reference before doing so.
