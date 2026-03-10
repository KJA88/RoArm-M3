#!/usr/bin/env python3
"""
MechanicalSupervisor (Phase 2 - AUTHORITATIVE)
Location: /home/kallen/RoArm/core/supervisor/mechanical_supervisor.py

MILESTONE CONSUMPTION:
- M02: Mechanical Truth (Limits enforced via JSON)
- M03: Deterministic Pipeline (Handshake + Telemetry Translation)
"""

import serial
import json
import time
import sys
from pathlib import Path

# --- SYSTEM CONFIG ---
PORT = "/dev/ttyUSB0"
BAUD = 115200
TIMEOUT = 1.0 

LIMITS_FILE = Path(__file__).resolve().parents[1] / "calibration" / "joint_limits.json"

class MechanicalSupervisor:
    def __init__(self):
        # 1. CONSUME M02: Load the Mechanical Truths
        if not LIMITS_FILE.exists():
            raise FileNotFoundError(f"M02 Artifact missing: {LIMITS_FILE}")
        with open(LIMITS_FILE, "r") as f:
            self.limits = json.load(f)

        # 2. STATE STORAGE: The Supervisor's Internal Brain
        self.joint_state = {
            "base": 0.0,
            "shoulder": 0.0,
            "elbow": 0.0,
            "wrist": 0.0,
            "roll": 0.0,
            "hand": 0.0
        }

        # 3. CONSUME M03: Establish the Resilient Pipe ("Church Logic")
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
            
            # Drain/Pulse/Drain Sequence
            time.sleep(1.0)              
            self.ser.reset_input_buffer() 
            self.ser.write(b"\n")        
            time.sleep(0.2)
            self.ser.reset_input_buffer() 
            
            # Torque ON
            self._send_and_wait({"T": 210, "cmd": 1})
            print("Supervisor Online: Pipeline Sync'd and Authority Active.")

        except Exception as e:
            print(f"CRITICAL: Supervisor failed to boot: {e}")
            sys.exit(1)

    # --- M03 RESILIENT HANDSHAKE + TRANSLATOR ---

    def _send_and_wait(self, cmd):
        """
        Deterministic 1:1 Handshake.
        Translates hardware shorthand to semantic supervisor state.
        """
        payload = json.dumps(cmd) + "\n"
        self.ser.write(payload.encode("ascii"))

        for _ in range(3):
            raw = self.ser.readline().decode("ascii", errors="ignore").strip()
            if not raw:
                continue

            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    data = json.loads(raw[start:end+1])
                    
                    # TELEMETRY MAP: Hardware Shorthand -> Supervisor Longhand
                    telemetry_map = {
                        "b": "base", "s": "shoulder", "e": "elbow",
                        "t": "wrist", "r": "roll", "g": "hand"
                    }

                    for short, long in telemetry_map.items():
                        if short in data:
                            self.joint_state[long] = data[short]
                    
                    return data
                except json.JSONDecodeError:
                    continue
        
        raise RuntimeError(f"Pipeline Stalled: {raw}")

    # --- M02 LIMIT ENFORCEMENT ---

    def _validate_move(self, joint_id, rad):
        jid = str(joint_id)
        if jid not in self.limits:
            return 
        
        lim = self.limits[jid]
        if not (lim["negative_limit"] <= rad <= lim["positive_limit"]):
            raise PermissionError(f"M02 VIOLATION: {lim['name']} {rad}rad is UNSAFE.")

    # --- PUBLIC API ---

    def move_joint(self, joint_id, rad, spd=50):
        """
        Moves a specific joint using T:101 (Direct Joint Control).
        This is the most reliable way to ensure motion occurs.
        """
        self._validate_move(joint_id, rad)
        
        # T:101 is the "Absolute" command for RoArm-M3 joints
        cmd = {
            "T": 101,
            "joint": joint_id,
            "rad": rad,
            "spd": spd,
            "acc": 0
        }

        return self._send_and_wait(cmd)

    def get_last_state(self):
        return self.joint_state.copy()

    def close(self):
        self.ser.close()