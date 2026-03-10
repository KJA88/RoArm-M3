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