import json
import numpy as np

def load_hsv_config(path):
    with open(path, "r") as f:
        cfg = json.load(f)

    return {
        "name": cfg.get("name", "unnamed"),
        "hsv_min": np.array(cfg["lower"]),
        "hsv_max": np.array(cfg["upper"]),
        "min_area": cfg.get("min_area", 300)
    }
