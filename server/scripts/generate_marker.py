# -*- coding: utf-8 -*-
"""정밀 모드용 ArUco 마커 PDF 생성 (Step 2-3, 1회 실행).

실행:  server/ 에서  .\\venv\\Scripts\\python.exe scripts\\generate_marker.py
출력:  server/data/aruco_marker.pdf  (+ 확인용 aruco_marker_preview.png)

★ 마커 실측 크기는 services/reference_detect.py 의 MARKER_SIZE_MM(단일 출처)를
  따른다. 그 값을 바꾸면 이 스크립트를 다시 돌려 마커를 재출력해야 하고,
  기존 출력물은 폐기해야 한다 (척도 계산 2-4·2-6이 이 값을 신뢰).
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.reference_detect import ARUCO_DICT_ID, MARKER_ID, MARKER_SIZE_MM  # noqa: E402

DPI = 300
A4_MM = (210.0, 297.0)
OUT_PDF = Path(__file__).resolve().parent.parent / "data" / "aruco_marker.pdf"
OUT_PNG = OUT_PDF.with_name("aruco_marker_preview.png")


def mm_to_px(mm: float) -> int:
    return round(mm * DPI / 25.4)


def _load_font(size_px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """한글 폰트(맑은 고딕) → 실패 시 기본 폰트."""
    for name in (r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(name, size_px)
        except OSError:
            continue
    return ImageFont.load_default()


def build_page() -> Image.Image:
    page_w, page_h = mm_to_px(A4_MM[0]), mm_to_px(A4_MM[1])
    page = Image.new("L", (page_w, page_h), 255)
    draw = ImageDraw.Draw(page)

    # ---- 마커 (정확히 MARKER_SIZE_MM) ----
    side_px = mm_to_px(MARKER_SIZE_MM)
    marker = cv2.aruco.generateImageMarker(
        cv2.aruco.getPredefinedDictionary(ARUCO_DICT_ID), MARKER_ID, side_px
    )
    mx = (page_w - side_px) // 2
    my = mm_to_px(70)
    page.paste(Image.fromarray(marker), (mx, my))

    # ---- 제목·안내 문구 ----
    f_big = _load_font(mm_to_px(7))
    f_mid = _load_font(mm_to_px(4.5))
    f_small = _load_font(mm_to_px(3.5))

    def center_text(y_px: int, text: str, font) -> None:
        w = draw.textlength(text, font=font)
        draw.text(((page_w - w) / 2, y_px), text, fill=0, font=font)

    center_text(mm_to_px(20), "FITME 정밀 측정용 ArUco 마커", f_big)
    center_text(mm_to_px(32), "반드시 100% 크기로 출력하세요 (페이지 맞춤/축소 금지)", f_mid)
    center_text(
        mm_to_px(40),
        f"마커 한 변 = {MARKER_SIZE_MM / 10:.0f}cm · 아래 눈금자를 자로 재서 확인하세요",
        f_small,
    )
    center_text(
        mm_to_px(47),
        "마커 둘레의 흰 여백을 1cm 이상 남기고 자르세요 (여백도 인식에 필요)",
        f_small,
    )

    # ---- 실측 확인용 눈금자 (마커 아래, 정확히 7cm) ----
    ruler_len = mm_to_px(MARKER_SIZE_MM)
    rx, ry = (page_w - ruler_len) // 2, my + side_px + mm_to_px(20)
    draw.line([(rx, ry), (rx + ruler_len, ry)], fill=0, width=mm_to_px(0.6))
    n_cm = int(MARKER_SIZE_MM / 10)
    for i in range(n_cm + 1):  # 0 ~ 7cm 눈금
        tx = rx + mm_to_px(i * 10)
        tall = mm_to_px(5 if i % 5 == 0 or i == n_cm else 3.5)
        draw.line([(tx, ry), (tx, ry + tall)], fill=0, width=mm_to_px(0.5))
        label = f"{i}"
        w = draw.textlength(label, font=f_small)
        draw.text((tx - w / 2, ry + mm_to_px(6)), label, fill=0, font=f_small)
    center_text(
        ry + mm_to_px(14),
        f"↑ 이 눈금자가 자로 정확히 {n_cm}cm이면 올바르게 출력된 것입니다",
        f_small,
    )
    center_text(
        page_h - mm_to_px(20),
        f"(마커 ID {MARKER_ID} · DICT_4X4_50 · 생성 도구: FITME generate_marker.py)",
        f_small,
    )
    return page


def main() -> None:
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    page = build_page()
    # Pillow PDF: resolution(DPI)로 물리 크기 확정 → 픽셀/300dpi = 실측 mm
    page.save(OUT_PDF, "PDF", resolution=DPI)
    page.save(OUT_PNG)

    side_px = mm_to_px(MARKER_SIZE_MM)
    print(f"저장: {OUT_PDF}")
    print(f"마커 한 변: {side_px}px @ {DPI}dpi = {side_px * 25.4 / DPI:.3f}mm "
          f"(목표 {MARKER_SIZE_MM}mm)")

    # 자기 검증: 만든 페이지에서 마커가 실제로 검출되는지 (규칙 1)
    from services.reference_detect import detect_aruco

    bgr = cv2.cvtColor(np.array(page.convert("RGB")), cv2.COLOR_RGB2BGR)
    result = detect_aruco(bgr)
    if not result["detected"]:
        print("!! 자기 검증 실패: 생성한 페이지에서 마커 미검출")
        sys.exit(1)
    c = np.array(result["cornersPx"])
    measured = float(np.linalg.norm(c[1] - c[0]))
    print(f"자기 검증: 검출 성공, 검출된 변 길이 {measured:.1f}px (기대 {side_px}px)")


if __name__ == "__main__":
    main()
