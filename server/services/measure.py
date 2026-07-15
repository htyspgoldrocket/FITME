"""척도 계산 (Step 2-4) — 왜곡 극복 전략 2: 호모그래피로 원근 제거 + px→mm 환산.

원리 (CLAUDE.md 2장): 크기를 아는 직사각형(카드 85.6×53.98mm / ArUco 70×70mm)이
사진에서 찌그러진 정도로 카메라 원근을 역산한다. 기준물 4꼭짓점 ↔ 실측 mm 좌표의
대응으로 호모그래피 H(이미지 px → 기준물 평면 mm)를 구하면, 같은 평면 위 임의의
두 점 사이 실제 거리를 mm로 잴 수 있다.

⚠️ 전제 1 — 꼭짓점 순서 계약: cornersPx는 반드시 **좌상→우상→우하→좌하** 순서다.
   (2-2 detect_card / 2-3 detect_aruco가 이 순서로 반환하며 테스트로 고정되어 있음.
    순서가 어긋나면 호모그래피가 뒤틀려 척도가 완전히 틀어진다.)

⚠️ 전제 2 — 평면 한정: H는 "기준물이 놓인 평면"에서만 정확하다. 깊이가 다른
   점(카메라에 더 가깝거나 먼 신체 부위)은 오차가 생긴다. 그래서 촬영 가이드가
   기준물을 측정 부위와 같은 평면에 대도록 유도한다(전략 1). 깊이 차이가 큰
   둘레 추정은 2-6의 타원 근사가 보완한다.

신체 부위 좌표 추출(2-5)과 부위별 cm 산출·둘레 근사(2-6)는 아직 미구현.
"""

from __future__ import annotations

import numpy as np
import cv2


def compute_scale(reference: dict) -> dict:
    """ReferenceInfo(detect_card/detect_aruco 반환값)로 척도 정보를 계산한다.

    카드/ArUco 공통 인터페이스: reference["realWidthMm"/"realHeightMm"]만 다르고
    처리 방식은 동일하다.

    반환 dict (추적 가능성 우선 — 어떤 입력으로 어떻게 계산됐는지 전부 포함):
      homographyPx2Mm: 3x3 리스트 — 이미지 px → 기준물 평면 mm 변환 행렬
      mmPerPx:         평균 척도 (기준물 위치 기준 참고값. 정밀 계산은 H를 쓸 것)
      trace: {
        refType, realWidthMm, realHeightMm, cornersPx,
        sidesPx: {top, right, bottom, left},   # 검출된 사각형 변 길이
        widthPx, heightPx,                     # 마주보는 변 평균
        mmPerPxWidth, mmPerPxHeight,           # 가로/세로 각각의 척도
      }

    Raises:
      ValueError: 기준물 미검출이거나 cornersPx가 유효한 4점이 아닐 때
    """
    if not reference.get("detected") or not reference.get("cornersPx"):
        raise ValueError("기준물이 검출되지 않아 척도를 계산할 수 없습니다")

    src = np.asarray(reference["cornersPx"], dtype=np.float32)
    if src.shape != (4, 2):
        raise ValueError(f"cornersPx는 4개의 (x,y)여야 합니다: shape={src.shape}")

    real_w = float(reference["realWidthMm"])
    real_h = float(reference["realHeightMm"])
    if real_w <= 0 or real_h <= 0:
        raise ValueError("기준물 실측 크기(mm)가 유효하지 않습니다")

    # 순서 계약(좌상→우상→우하→좌하)에 맞춘 목적 좌표 (기준물 평면, 단위 mm)
    dst = np.array(
        [[0.0, 0.0], [real_w, 0.0], [real_w, real_h], [0.0, real_h]],
        dtype=np.float32,
    )
    homography = cv2.getPerspectiveTransform(src, dst)

    # 참고용 평균 척도 + 추적 정보
    sides_px = {
        "top": float(np.linalg.norm(src[1] - src[0])),
        "right": float(np.linalg.norm(src[2] - src[1])),
        "bottom": float(np.linalg.norm(src[2] - src[3])),
        "left": float(np.linalg.norm(src[3] - src[0])),
    }
    width_px = (sides_px["top"] + sides_px["bottom"]) / 2.0
    height_px = (sides_px["left"] + sides_px["right"]) / 2.0
    mm_per_px_w = real_w / width_px
    mm_per_px_h = real_h / height_px

    return {
        "homographyPx2Mm": homography.tolist(),
        "mmPerPx": (mm_per_px_w + mm_per_px_h) / 2.0,
        "trace": {
            "refType": reference.get("type"),
            "realWidthMm": real_w,
            "realHeightMm": real_h,
            "cornersPx": src.tolist(),
            "sidesPx": sides_px,
            "widthPx": width_px,
            "heightPx": height_px,
            "mmPerPxWidth": mm_per_px_w,
            "mmPerPxHeight": mm_per_px_h,
        },
    }


def points_px_to_plane_mm(scale: dict, points_px: list | np.ndarray) -> np.ndarray:
    """이미지 px 좌표들을 기준물 평면 mm 좌표로 변환한다 (원근 제거).

    ⚠️ 기준물과 같은 평면에 있는 점에서만 정확 (모듈 docstring 전제 2).
    """
    homography = np.asarray(scale["homographyPx2Mm"], dtype=np.float64)
    pts = np.asarray(points_px, dtype=np.float64).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(pts, homography).reshape(-1, 2)


def distance_mm(scale: dict, p1_px, p2_px) -> float:
    """이미지 위 두 점(px) 사이의 실제 거리(mm) — 기준물 평면 기준."""
    mm = points_px_to_plane_mm(scale, [p1_px, p2_px])
    return float(np.linalg.norm(mm[1] - mm[0]))
