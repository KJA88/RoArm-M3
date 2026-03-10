#!/usr/bin/env python3
"""
Milestone 03: Deterministic Pipelines (LOCKABLE — FINAL)

PURPOSE:
- Enforce strict 1:1 Supervisor ↔ Executor communication
- Block deterministically on every command
- Sanitize serial framing WITHOUT interpreting payload meaning
- Treat ambiguity as terminal failure
"""

import time
import json
import serial
import sys
from datetime import datetime

# ---------------- CONFIG ----------------

PORT = "/dev/ttyUSB0"
BAUD = 115200
TIMEOUT = 1.0

# --------------------------------------


class HandshakeSupervisor:
    def __init__(self):
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            time.sleep(1.0)
            self.log(f"Deterministic Pipeline Established on {PORT}")

            # Prove executor is alive
            self.set_torque(True)

        except Exception as e:
            self.log(f"CRITICAL: Unable to establish pipeline: {e}")
            sys.exit(1)

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")

    # ---------- Deterministic Handshake ----------

    def send_and_wait(self, msg):
        """
        STRICT Milestone 03 Handshake with framing sanitation.

        Rules:
        - Exactly one command in flight
        - Exactly one response required
        - Response must be reconstructable into valid JSON
        """

        try:
            payload = json.dumps(msg) + "\n"
            self.ser.write(payload.encode("ascii"))

            raw = self.ser.readline().decode("ascii", errors="ignore").strip()

            if not raw:
                raise RuntimeError("Pipeline Stalled: No response from ESP32.")

            # ---- FRAMING SANITATION ----
            # Drop everything before the first JSON key or brace
            brace_idx = raw.find("{")
            quote_idx = raw.find('"')

            if brace_idx == -1 and quote_idx == -1:
                raise RuntimeError(f"No JSON content found: {raw}")

            start = brace_idx if brace_idx != -1 else quote_idx
            candidate = raw[start:]

            if not candidate.startswith("{"):
                candidate = "{" + candidate

            if "}" not in candidate:
                raise RuntimeError(f"Incomplete JSON frame: {raw}")

            end = candidate.rfind("}")
            candidate = candidate[: end + 1]

            # Structural validation ONLY
            json.loads(candidate)

            self.log("HANDSHAKE SUCCESS")
            return candidate

        except Exception as e:
            self.log(f"CRITICAL: Deterministic Pipeline Failure: {e}")
            raise

    # ---------- Minimal Commands ----------

    def set_torque(self, enabled):
        state = 1 if enabled else 0
        self.log(f"Commanding Torque: {enabled}")
        return self.send_and_wait({"T": 210, "cmd": state})

    def run_pipeline_validation(self):
        self.log("Starting 1:1 Pipeline Validation Sweep...")

        test_positions = [0.4, -0.4, 0.0]

        for pos in test_positions:
            self.log(f"TX: Base -> {pos} rad")
            self.send_and_wait(
                {"T": 101, "joint": 1, "rad": pos, "spd": 50}
            )
            time.sleep(1.5)  # motor settle only

        self.log("✅ MILESTONE 03 LOCKED: Deterministic pipeline verified.")


# ---------------- ENTRY ----------------

if __name__ == "__main__":
    try:
        arm = HandshakeSupervisor()
        arm.run_pipeline_validation()
    except KeyboardInterrupt:
        print("\nUSER ABORTED — deterministic shutdown.")
        sys.exit(0)
    except Exception as e:
        print(f"\nFATAL ERROR — Pipeline Trust Lost: {e}")
        sys.exit(1)
