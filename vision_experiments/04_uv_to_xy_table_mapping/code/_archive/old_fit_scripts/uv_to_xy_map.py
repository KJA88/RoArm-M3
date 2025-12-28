"""
Camera (u,v) → Table (x,y) mapping
Derived from Lesson 07 affine calibration
"""

def uv_to_xy(u, v):
    # Affine coefficients (LOCKED)
    a = 0.048795
    b = 0.532439
    c = 12.153846

    d = 0.484161
    e = -0.167213
    f = -297.579834

    x = a * u + b * v + c
    y = d * u + e * v + f

    return x, y


# --- quick sanity test ---
if __name__ == "__main__":
    test_uv = (640, 360)
    x, y = uv_to_xy(*test_uv)
    print(f"Test uv={test_uv} -> x={x:.1f}, y={y:.1f}")
