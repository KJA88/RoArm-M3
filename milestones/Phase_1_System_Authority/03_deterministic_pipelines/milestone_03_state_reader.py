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
from urllib.parse import urlencode
from urllib.request import urlopen

import serial


BAUD = 115200
HTTP_TIMEOUT = 1.5
DEFAULT_HTTP_BASE_URL = "http://192.168.4.1"

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


def normalize_feedback(feedback, transport, endpoint, **transport_details):
    """Return one validated firmware packet in the stable state schema."""
    return {
        "connected": True,
        "fresh": True,
        "transport": transport,
        "endpoint": endpoint,
        **transport_details,
        "timestamp_unix": time.time(),

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


def get_serial_feedback():
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

        return normalize_feedback(
            feedback,
            transport="serial",
            endpoint=port,
            port=port,
            baud=BAUD,
        )

    finally:
        ser.close()


def get_http_feedback():
    """Perform one read-only T=105 query through the firmware HTTP API."""
    base_url = os.environ.get(
        "ROARM_HTTP_BASE_URL",
        DEFAULT_HTTP_BASE_URL,
    ).rstrip("/")
    if not base_url:
        raise ValueError("ROARM_HTTP_BASE_URL must not be empty")

    query = urlencode({"json": '{"T":105}'})
    url = f"{base_url}/js?{query}"

    with urlopen(url, timeout=HTTP_TIMEOUT) as response:
        packet = json.loads(response.read().decode("utf-8"))

    if not isinstance(packet, dict):
        raise RuntimeError("HTTP feedback must be a JSON object")
    if packet.get("T") != 1051:
        raise RuntimeError("HTTP feedback did not contain T=1051")

    return normalize_feedback(
        packet,
        transport="http",
        endpoint=base_url,
    )


def get_feedback():
    """Use the explicitly selected state transport; serial is the default."""
    transport = os.environ.get(
        "ROARM_STATE_TRANSPORT",
        "serial",
    ).strip().lower()

    if transport == "serial":
        return get_serial_feedback()
    if transport == "http":
        return get_http_feedback()

    raise ValueError(
        "ROARM_STATE_TRANSPORT must be 'serial' or 'http'"
    )


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
