#!/usr/bin/env python3
import sys
import json
import subprocess

ROARM = "./roarm_control.py"
MISSION = "joint_stream"

cmd = {"T":242, "name":MISSION, "times":1}
raw = json.dumps(cmd)

subprocess.run([sys.executable, ROARM, "json", raw], check=True)
