# Milestone 03: Deterministic Pipelines

**Status:** COMPLETE  
**Role:** Communication Authority & Synchronization

## Purpose
To solve "command spamming" and "hardware amnesia" by enforcing a strict **One Command -> One Response** rule. This ensures the Raspberry Pi Supervisor and the ESP32 Executor stay in perfect sync.

## Verified Capabilities
- **Deterministic Handshake:** The Supervisor blocks execution until the ESP32 returns a JSON status string.
- **Safety Boot:** Manual confirmation of the "Candle" (Home) position before torque engagement.
- **Auto-Home Shutdown:** The system automatically returns the arm to the vertical 0.0 position and disengages torque on exit.

## How to Run
```bash
cd ~/RoArm
python3 milestones/Phase_1_System_Authority/03_deterministic_pipelines/milestone_03_run.py
---

## Current Authority Notice

This directory contains historical Phase 1 read-only work as well as later
live-motion authority additions.

Do not interpret older `read-only`, `no motion`, or
`hardware_action: NONE` language as a global permanent prohibition.

Those statements remain authoritative for the specific read-only validator
and state-reader components in which they appear.

For current live-motion authority, consult:

- `MOTION_AUTHORITY.md`
- `milestone_03_motion_authority.py`
- `milestone_03_joint_motion_authority.py`

Current approved live motion is intentionally narrow and gated.
