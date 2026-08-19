#!/usr/bin/env python3

"""
Milestone 03 - Deterministic Read-Only RoArm State Reader

Purpose:
    Query the RoArm-M3-S for its current state without changing torque,
    commanding motion, or modifying robot configuration.

Protocol:
    Request:  {"T":105}
    Response: {"T":1051,...}

Safety:
    This module sends ONLY T=105.
    It does NOT send torque, joint, Cartesian, IK, gripper, or configuration
    commands.
"""

import json
import os
import time
import serial


BAUD = 115200

PREFERRED_PORT = (
    "/dev/serial/by-id/"
    "usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_"
    "5c6dc8363f01f01180d7c1295c2a50c9-if00-port0"
)

FALLBACK_PORT = "/dev/ttyUSB0"


def choose_port():
    """Return the verified stable RoArm serial device when available."""
    if os.path.exists(PREFERRED_PORT):
        return PREFERRED_PORT

    if os.path.exists(FALLBACK_PORT):
        return FALLBACK_PORT

    raise FileNotFoundError(
        "RoArm serial device not found. "
        f"Tried {PREFERRED_PORT} and {FALLBACK_PORT}"
    )


def get_feedback():
    """
    Perform one deterministic read-only firmware-state query.

    Sends exactly:
        {"T":105}

    Accepts only:
        T == 1051
    """

    port = choose_port()

    ser = serial.Serial(
        port,
        BAUD,
        timeout=0.2,
        dsrdtr=None,
    )

    ser.setRTS(False)
    ser.setDTR(False)

    try:
        time.sleep(0.2)

        # Discard stale serial input so the returned packet belongs
        # to this query.
        ser.reset_input_buffer()

        # The ONLY robot command issued by this reader.
        ser.write(b'{"T":105}\n')
        ser.flush()

        deadline = time.monotonic() + 1.5
        feedback = None

        while time.monotonic() < deadline:
            raw = ser.readline()

            if not raw:
                continue

            line = raw.decode("utf-8", errors="ignore").strip()

            if not (line.startswith("{") and line.endswith("}")):
                continue

            try:
                packet = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Ignore all unrelated firmware chatter.
            if packet.get("T") == 1051:
                feedback = packet

        if feedback is None:
            raise RuntimeError(
                "No valid T=1051 feedback received within timeout"
            )

        timestamp = time.time()

        return {
            "connected": True,
            "fresh": True,
            "port": port,
            "baud": BAUD,
            "timestamp_unix": timestamp,

            "pose": {
                "x": feedback.get("x"),
                "y": feedback.get("y"),
                "z": feedback.get("z"),
                "tilt": feedback.get("tit"),
            },

            "joints": {
                "base": feedback.get("b"),
                "shoulder": feedback.get("s"),
                "elbow": feedback.get("e"),
                "wrist": feedback.get("t"),
                "roll": feedback.get("r"),
                "gripper": feedback.get("g"),
            },

            # Preserve firmware fields whose meanings have not yet
            # been authoritatively assigned.
            "additional_feedback": {
                key: value
                for key, value in feedback.items()
                if key not in {
                    "T", "x", "y", "z", "tit",
                    "b", "s", "e", "t", "r", "g"
                }
            },

            "raw_feedback": feedback,
        }

    finally:
        ser.close()


def main():
    try:
        state = get_feedback()

    except Exception as exc:
        state = {
            "connected": False,
            "fresh": False,
            "error": str(exc),
            "timestamp_unix": time.time(),
        }

    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
