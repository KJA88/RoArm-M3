# README_TROUBLESHOOTING.md  
## RoArm-M3 + Raspberry Pi — High-Cost Failure Guide (AI-Readable)

**Purpose**  
This document exists to help an AI (or human) quickly diagnose and fix the
small number of failures that cost the most time when working with a
Waveshare RoArm-M3 and Raspberry Pi.

This is **not** an exhaustive troubleshooting list.  
It only documents issues that:
- Look like software bugs
- Produce no errors
- Cause long debugging loops
- Are actually caused by identity, power, or interface mistakes

---

## SYSTEM CONTEXT (ASSUMED)

- Robot: Waveshare RoArm-M3
- Control MCU: ESP32 (USB serial)
- Host: Raspberry Pi
- Primary user: `kallen`
- SSH access via terminal or VS Code Remote-SSH
- Multiple USB devices exposed by the arm (ESP32 + LiDAR)

---

## FAILURE 1 — Arm Is “Alive” but Will Not Move

### Symptom Signature
- Arm powers on
- Arm homes to reset position
- Torque locks and holds
- Commands send without error
- **No physical movement at all**

### Why This Is Expensive
System appears healthy. Leads to deep software or firmware debugging.

### Root Cause
**Wrong USB interface selected**

The RoArm exposes multiple USB devices:
- ESP32 control interface → **accepts motion commands**
- LiDAR interface → **data only, ignores motion commands**

Both enumerate normally.

### Decisive Check
```bash
ls /dev/ttyUSB*

Unplug and replug the arm and observe which device appears.

Optional confirmation:

dmesg | tail

Fix

    Use the ESP32 USB serial interface

    Never use the LiDAR USB interface for control

AI Heuristic

    If the arm homes and holds torque but ignores all motion, check USB interface identity before touching software.

FAILURE 2 — VS Code Remote-SSH OfflineError / Timeout
Symptom Signature

    VS Code Remote-SSH shows OfflineError

    SSH hangs instead of rejecting

    System worked previously

Why This Is Expensive

Appears to be a VS Code or SSH configuration issue.
Root Cause

Silent IP address change

Common switch:

    192.168.1.x (home LAN)

    192.168.4.2 (arm hotspot / AP / isolated network)

Decisive Check (on Pi)

hostname -I

Fix

    Update SSH target to current IP

    Kill stale VS Code SSH server if needed

    Reconnect

AI Heuristic

    If SSH times out but the system worked before, verify the IP before editing configs.

FAILURE 3 — Ping Works, SSH Times Out
Symptom Signature

    ping <IP> succeeds

    ssh user@IP times out on port 22

    No password prompt

Why This Is Expensive

Network looks fine; feels like firewall or OS corruption.
Root Cause

SSH service not running or disabled
Decisive Checks (on Pi locally)

sudo systemctl status ssh
sudo ss -tlnp | grep :22

Fix

sudo systemctl enable ssh
sudo systemctl start ssh

Verify:

ssh localhost

AI Heuristic

    Ping + no SSH prompt = SSH daemon issue, not networking.

FAILURE 4 — Random or Inconsistent Behavior
Symptom Signature

    USB devices disappear or renumber

    Serial ports change

    Commands sometimes work

    VS Code disconnects

    Behavior worsens when the arm moves

Why This Is Expensive

Non-deterministic. Masquerades as logic or timing bugs.
Root Cause

Power instability / undervoltage
Decisive Check

vcgencmd get_throttled

Interpretation

    throttled=0x0 → OK

    Any other value → power fault

Fix

    Use proper Raspberry Pi power supply (5.1 V, sufficient current)

    Reboot after fixing power

    Re-verify USB ports after power events

AI Heuristic

    Inconsistent failures across subsystems almost always indicate power issues.

FAILURE 5 — Everything Looks Correct, Still Blocked
Symptom Signature

    Correct user

    Correct IP

    Correct USB port

    Correct commands

    Still no progress

Why This Is Expensive

Leads to firmware reflashing or code rewrites unnecessarily.
Root Cause

Debugging the wrong abstraction layer

The actual fault is usually lower:

    power

    network identity

    service state

    hardware interface selection

Fix Strategy (Do Not Skip Order)

    Power (vcgencmd get_throttled)

    Network identity (hostname -I)

    SSH service (systemctl status ssh)

    USB interface identity (ESP32 vs LiDAR)

    Serial port number

AI Heuristic

    If multiple layers are being debugged simultaneously, step down to hardware invariants.

QUICK AI DECISION TABLE
Primary Symptom	First Check
No motion, no error	USB interface identity
SSH timeout	Current IP
Ping works, SSH fails	SSH service
Random failures	Power / undervoltage
Ports changing	Power or USB reset
DESIGN NOTE (IMPORTANT)

This system often fails silently.
Lack of errors does not imply correctness.

Most failures are misidentification problems, not software bugs.
AI INSTRUCTION

When diagnosing this system:

    Prefer identity checks over configuration edits

    Assume the system may appear healthy while misconfigured

    Validate physical and network reality first

END OF DOCUMENT
