# -*- coding: utf-8 -*-
"""E2E fake camera video generator (2-8d).

Creates tests/fake-marker.y4m: a static scene with an ArUco marker centered,
sized to pass /check-photo (marker inside the 40-55px distance band after
capture -- video is native 1080px wide so no resize happens and the size is
identical in the self-check and in the browser capture; axis-aligned so tilt
ratio == 1, centered in CENTER_*_RANGE).

Run with server venv (needs cv2):
  .\\server\\venv\\Scripts\\python.exe tests\\gen_fake_camera.py

Content is ASCII-only as a precaution against Windows cp949 console issues
(see PROGRESS lesson 1).
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

import cv2  # noqa: E402
from services.reference_detect import ARUCO_DICT_ID, MARKER_ID  # noqa: E402

W, H = 1080, 1440        # native CapturedImage size -> capture resize is a no-op
SIDE = 42                # marker side px, inside MIN/MAX_MARKER_WIDTH_PX (40-55).
# 42 also keeps the e2e-analyze "suspect" scenario alive: fake landmarks are
# head-heel 1400px with heightCm=172 (body 1.2286 mm/px) vs marker 70mm/42px
# (1.667 mm/px) -> r = 0.74, >20% mismatch -> retake recommendation banner.
MARGIN = 24              # white quiet zone (required for detection)
FRAMES = 3               # Chrome loops the file
OUT = ROOT / "tests" / "fake-marker.y4m"


def main() -> None:
    marker = cv2.aruco.generateImageMarker(
        cv2.aruco.getPredefinedDictionary(ARUCO_DICT_ID), MARKER_ID, SIDE
    )
    page = np.full((H, W), 200, dtype=np.uint8)  # light gray background
    cx, cy = W // 2, 600  # marker center: x ratio 0.5, y ratio 0.417 (in range)
    x0, y0 = cx - SIDE // 2, cy - SIDE // 2
    page[y0 - MARGIN : y0 + SIDE + MARGIN, x0 - MARGIN : x0 + SIDE + MARGIN] = 255
    page[y0 : y0 + SIDE, x0 : x0 + SIDE] = marker

    u = np.full((H // 2, W // 2), 128, dtype=np.uint8)  # gray chroma (Y4M 4:2:0)
    with open(OUT, "wb") as f:
        f.write(f"YUV4MPEG2 W{W} H{H} F15:1 Ip A1:1 C420jpeg\n".encode())
        for _ in range(FRAMES):
            f.write(b"FRAME\n")
            f.write(page.tobytes())
            f.write(u.tobytes())
            f.write(u.tobytes())

    # self-check: the same frame must pass detection before we hand it to Chrome
    bgr = cv2.cvtColor(page, cv2.COLOR_GRAY2BGR)
    from services.photo_check import check_photo  # noqa: E402

    result = check_photo(bgr, "precise")
    print("self-check ready:", result["ready"], result["reasons"])
    if not result["ready"]:
        raise SystemExit("generated frame does not pass check_photo")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
