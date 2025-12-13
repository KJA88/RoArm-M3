#!/usr/bin/env python3

import cv2
import json
import numpy as np

IMAGE_PATH   = "frame.jpg"              # still image from camera_snap.py
OUTPUT_IMAGE = "frame_with_patch.jpg"   # annotated preview
HSV_CONFIG   = "hsv_config.json"        # auto-generated HSV config


def main():
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        print("ERROR: could not load image", IMAGE_PATH)
        return

    h, w = img.shape[:2]
    cx, cy = w // 2, h // 2

    # 40x40 center patch (size=20 -> 2*20)
    size = 20
    x1 = max(cx - size, 0)
    x2 = min(cx + size, w)
    y1 = max(cy - size, 0)
    y2 = min(cy + size, h)

    patch_bgr = img[y1:y2, x1:x2]
    patch_hsv = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2HSV)

    hsv_vals = patch_hsv.reshape(-1, 3)
    H = hsv_vals[:, 0].astype(np.int32)
    S = hsv_vals[:, 1].astype(np.int32)
    V = hsv_vals[:, 2].astype(np.int32)

    print("Center patch size:", patch_hsv.shape)
    print(f"H (0-179): mean={H.mean():.1f}, min={H.min()}, max={H.max()}")
    print(f"S (0-255): mean={S.mean():.1f}, min={S.min()}, max={S.max()}")
    print(f"V (0-255): mean={V.mean():.1f}, min={V.min()}, max={V.max()}")

    # --- Build HSV range with a bit of margin around the patch values ---
    h_min = max(H.min() - 5, 0)
    h_max = min(H.max() + 5, 179)
    s_min = max(S.min() - 30, 0)
    s_max = 255
    v_min = max(V.min() - 30, 0)
    v_max = 255

    lower = [int(h_min), int(s_min), int(v_min)]
    upper = [int(h_max), int(s_max), int(v_max)]

    cfg = {"lower": lower, "upper": upper}
    with open(HSV_CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)

    print("Wrote HSV config to", HSV_CONFIG)
    print("  LOWER_HSV:", lower)
    print("  UPPER_HSV:", upper)

    # --- Draw the patch so you SEE what was used ---
    annotated = img.copy()
    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)  # green box
    cv2.drawMarker(
        annotated,
        (cx, cy),
        (255, 0, 0),   # blue cross at image center
        markerType=cv2.MARKER_CROSS,
        markerSize=20,
        thickness=2,
    )

    cv2.imwrite(OUTPUT_IMAGE, annotated)
    print("Saved annotated image with patch to", OUTPUT_IMAGE)
    print(f"Patch bounds: x1={x1}, x2={x2}, y1={y1}, y2={y2}")


if __name__ == "__main__":
    main()
