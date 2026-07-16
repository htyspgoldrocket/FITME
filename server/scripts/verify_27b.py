"""2-7b 검증: 척도 3방식 비교 + A/B안 판정 — 캐시 랜드마크 39회분, 신규 API 호출 0.

비교하는 척도 방식:
  H = 기존 호모그래피 (2-4~2-7 경로) — v3 폭주 재현으로 폐기 근거를 기록
  M = 마커 스칼라 (compute_scale의 mmPerPx)
  A = 전 항목 키 척도 (height_scale_from_runs)
  B = 길이(키·팔·다리안쪽·상체)=키 척도, 폭(어깨·둘레 3종)=마커 스칼라

A/B 판정 지표 (둘레 계수와 무관한 것만 사용 — 계수 역산은 ④에서):
  1) 폭 항목의 사진 간(v1/v2/v3) 일관성 — 같은 사람이므로 실제 폭은 동일해야 함
  2) 반복 편차 (Gate 기준: 2cm)
키 항목은 A/B에서 캘리브레이션 앵커라 오차 0이 자명 — 표에서 (0 자명)으로 표기.

사용: .\\venv\\Scripts\\python.exe scripts\\verify_27b.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

# Windows 콘솔(cp949)에서 한글·특수문자 출력 깨짐 방지
sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import measure  # noqa: E402
from services.reference_detect import detect_aruco  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
HEIGHT_CM = 172.0  # person01 실측 키 (truth/truth_v2 공통 — 키 캘리브레이션 입력)

PHOTOS = [
    # (표기, 파일 stem, truth 파일, 성격)
    ("v1", "person01_aruco", "person01_truth.json", "헐렁+중간거리(엣지)"),
    ("v2", "person01_v2_aruco", "person01_truth_v2.json", "밀착+원거리(기준)"),
    ("v3", "person01_v3_aruco", "person01_truth_v2.json", "밀착+근거리(엣지)"),
]

ITEMS = list(measure.PLAUSIBLE_RANGES_CM.keys())
LENGTH_ITEMS = ("height", "arm_length", "inseam", "torso_length")
WIDTH_ITEMS = ("shoulder_width", "chest_circumference",
               "waist_circumference", "hip_circumference")
# 폭 원자료(둘레 계수 미적용) — 사진 간 일관성 판정용
WIDTH_PAIRS = {
    "shoulder_w": ("left_shoulder", "right_shoulder"),
    "chest_w": ("chest_left", "chest_right"),
    "waist_w": ("waist_left", "waist_right"),
    "hip_w": ("hip_left", "hip_right"),
}


def load_runs(stem: str) -> list[dict]:
    files = [FIXTURES / f"{stem}.landmarks.json"] + [
        FIXTURES / f"{stem}.landmarks.run{i}.json" for i in range(2, 14)
    ]
    runs = [json.loads(f.read_text(encoding="utf-8")) for f in files if f.exists()]
    if len(runs) != 13:
        print(f"⚠️ {stem}: 캐시 {len(runs)}개 (13개 기대)")
    return runs


def median_spread(runs, scale, ref, **kw):
    """(13런 중앙값, 롤링 7프레임 편차).

    편차 지표는 2-7 Gate 기록과 동일: 13런에서 연속 7런 윈도우(7개)마다
    중앙값(=제품이 보고할 값)을 내고, 그 윈도우 중앙값들의 max-min.
    (measure_with_statistics 내부의 3런-중앙값 산포보다 Gate 비교에 적합)
    """
    vals = []
    for lm in runs:
        m, _ = measure.landmarks_to_measurements(lm, scale, "precise", ref, **kw)
        vals.append({k: m[k] for k in ITEMS})
    median, _ = measure.aggregate_runs(vals)
    windows = [vals[i:i + 7] for i in range(len(vals) - 6)] if len(vals) >= 7 else [vals]
    wmed = [measure.aggregate_runs(w)[0] for w in windows]
    spread = {
        k: float(max(m[k] for m in wmed) - min(m[k] for m in wmed)) for k in ITEMS
    }
    return median, spread


def width_medians_cm(runs, mm_per_px: float) -> dict:
    """둘레 계수 미적용 원자료: 좌우 랜드마크 픽셀거리 × 척도 → cm (런 중앙값)."""
    out = {}
    for name, (lk, rk) in WIDTH_PAIRS.items():
        ds = [measure.scalar_distance_mm(mm_per_px, lm[lk], lm[rk]) / 10.0 for lm in runs]
        out[name] = float(np.median(ds))
    return out


def fmt_err(value, truth):
    if truth is None:
        return f"{value:6.1f} (실측없음)"
    return f"{value:6.1f} ({value - truth:+6.1f})"


def main():
    results = {}
    for tag, stem, truth_file, desc in PHOTOS:
        img = cv2.imread(str(FIXTURES / f"{stem}.jpg"))
        if img is None:
            raise SystemExit(f"사진 없음: {stem}.jpg")
        ref = detect_aruco(img)
        if not ref["detected"]:
            raise SystemExit(f"{tag}: 마커 미검출 — 검증 불가")
        scale = measure.compute_scale(ref)
        runs = load_runs(stem)
        truth = json.loads((FIXTURES / truth_file).read_text(encoding="utf-8"))

        height_scale = measure.height_scale_from_runs(runs, HEIGHT_CM)
        marker_mpp = scale["mmPerPx"]
        height_mpp = height_scale["mmPerPx"]
        agree = measure.check_scale_agreement(height_mpp, marker_mpp)

        methods = {
            "H": median_spread(runs, scale, ref),
            "M": median_spread(runs, scale, ref,
                               length_mm_per_px=marker_mpp, width_mm_per_px=marker_mpp),
            "A": median_spread(runs, scale, ref,
                               length_mm_per_px=height_mpp, width_mm_per_px=height_mpp),
            "B": median_spread(runs, scale, ref,
                               length_mm_per_px=height_mpp, width_mm_per_px=marker_mpp),
        }
        results[tag] = {
            "desc": desc, "truth": truth, "scale": scale,
            "marker_mpp": marker_mpp, "height_mpp": height_mpp, "agree": agree,
            "methods": methods, "runs": runs,
            "marker_px": scale["trace"]["widthPx"],
        }

    # ---- 표 1: 척도 요약 ----
    print("=" * 78)
    print("표 1 — 척도 요약 (마커 스칼라 vs 키 캘리브레이션)")
    print("=" * 78)
    print(f"{'사진':4} {'성격':22} {'마커px':>7} {'마커mm/px':>10} {'키mm/px':>9} "
          f"{'r':>6} {'판정':10}")
    for tag, r in results.items():
        print(f"{tag:4} {r['desc']:22} {r['marker_px']:7.1f} {r['marker_mpp']:10.4f} "
              f"{r['height_mpp']:9.4f} {r['agree']['ratio']:6.3f} {r['agree']['level']:10}")

    # ---- 표 2: 키 오차 — 척도 방식별 (H 폭주 재현 + 스칼라 기준선) ----
    print()
    print("=" * 78)
    print("표 2 — 키 오차(cm): H=호모그래피(폐기 근거), M=마커 스칼라, A/B=캘리브레이션")
    print("=" * 78)
    print(f"{'사진':4} {'H(호모그래피)':>16} {'M(마커 스칼라)':>16} {'A/B(키 척도)':>14}")
    for tag, r in results.items():
        t = r["truth"].get("height")
        h = r["methods"]["H"][0]["height"] - t
        m = r["methods"]["M"][0]["height"] - t
        print(f"{tag:4} {h:+16.1f} {m:+16.1f} {'(0 자명)':>14}")

    # ---- 표 3: 길이 항목 오차 (A=B 동일 — 키 척도) ----
    print()
    print("=" * 78)
    print("표 3 — 길이 항목(키 척도, A/B 동일): 측정값 (실측 대비 오차)")
    print("=" * 78)
    header = f"{'항목':18}" + "".join(f"{t:>18}" for t in results)
    print(header)
    for item in LENGTH_ITEMS:
        if item == "height":
            continue  # 표 2에서 다룸 + A/B에선 자명
        row = f"{item:18}"
        for tag, r in results.items():
            row += f"{fmt_err(r['methods']['A'][0][item], r['truth'].get(item)):>18}"
        print(row)

    # ---- 표 4: 폭 원자료(계수 무관)의 사진 간 일관성 — A/B 판정 핵심 ----
    print()
    print("=" * 78)
    print("표 4 — 폭 원자료 cm (둘레 계수 미적용) — 같은 사람이므로 사진 간 동일해야 함")
    print("=" * 78)
    for opt, mpp_key in (("A(키 척도)", "height_mpp"), ("B(마커 스칼라)", "marker_mpp")):
        print(f"[{opt}]")
        print(f"{'항목':12}" + "".join(f"{t:>10}" for t in results)
              + f"{'산포(max-min)':>16}")
        for name in WIDTH_PAIRS:
            vals = [width_medians_cm(r["runs"], r[mpp_key])[name]
                    for r in results.values()]
            row = f"{name:12}" + "".join(f"{v:10.1f}" for v in vals)
            row += f"{max(vals) - min(vals):16.2f}"
            print(row)
        print()

    # ---- 표 5: 반복 편차 (Gate 기준 2cm) ----
    print("=" * 78)
    print("표 5 — 반복 편차 cm (Gate ≤2.0) — 방식별 통과 항목 수")
    print("=" * 78)
    for tag, r in results.items():
        print(f"[{tag}]")
        print(f"{'항목':22}" + "".join(f"{m:>8}" for m in ("H", "M", "A", "B")))
        for item in ITEMS:
            row = f"{item:22}"
            for m in ("H", "M", "A", "B"):
                row += f"{r['methods'][m][1][item]:8.2f}"
            print(row)
        counts = {m: sum(1 for i in ITEMS if r["methods"][m][1][i] <= 2.0)
                  for m in ("H", "M", "A", "B")}
        print(f"{'≤2cm 항목 수':22}" + "".join(f"{counts[m]:>7}/8" for m in ("H", "M", "A", "B")))
        print()

    # ---- 표 6: 최종 파이프라인 — A안 확정 + 계수 역산(v2) + BMI 둘레 보정 ----
    # 계수(SHOULDER_CURVE_COEF, DEPTH_RATIOS)는 v2에서 역산했으므로 v2의
    # 어깨·둘레 오차 ≈ 0은 자명(역산 기준). 실질 검증은 v1/v3으로의 전이 오차.
    weight_kg = json.loads(
        (FIXTURES / "person01_truth_v2.json").read_text(encoding="utf-8"))["weight_kg"]
    ratios = measure.bmi_depth_ratios(HEIGHT_CM, weight_kg)
    print("=" * 78)
    print(f"표 6 — 최종 A 파이프라인: 키 척도 + 계수(v2 역산) + BMI 보정 "
          f"(몸무게 {weight_kg}kg → 깊이 계수 {ratios})")
    print("      측정값 (실측 대비 오차) / [반복 편차] — v2 어깨·둘레는 역산 기준이라 자명")
    print("=" * 78)
    final = {}
    for tag, r in results.items():
        final[tag] = median_spread(
            r["runs"], r["scale"], {"detected": True},
            length_mm_per_px=r["height_mpp"], width_mm_per_px=r["height_mpp"],
            depth_ratios=ratios,
        )
    print(f"{'항목':20}" + "".join(f"{t:>26}" for t in results))
    for item in ITEMS:
        row = f"{item:20}"
        for tag, r in results.items():
            med, spr = final[tag]
            row += f"{fmt_err(med[item], r['truth'].get(item)):>18} [{spr[item]:4.1f}]"
        print(row)
    for tag in results:
        cnt = sum(1 for i in ITEMS if final[tag][1][i] <= 2.0)
        print(f"{tag}: 편차 ≤2cm {cnt}/8")


if __name__ == "__main__":
    main()
