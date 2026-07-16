"""다인(多人) 계수 역산·검증 — 표본이 확보되면 Phase 진행과 무관하게 언제든 실행.

목적 (2-7b 후속 구조, CLAUDE.md 13-2 향후 과제):
  1. 대상별 계수 역산 → 사람 간 산포 확인 (계수가 "사람 일반의 상수"인지 판정)
  2. N≥2: Leave-One-Out 교차 검증 — 다른 사람들의 계수로 본인을 예측했을 때의
     오차 (절대 정확도 ±3cm/±5cm 검증은 이 방식으로만 가능)
  3. 현재 measure.py 상수와 집계값 비교 — **상수 갱신은 자동으로 하지 않는다.**
     갱신은 사용자 결정 후 수동으로 하고, 갱신 시 pytest + verify_27b.py 재실행.

대상 등록: tests/fixtures/calibration_set.json (로컬 전용 — 형식은 fixtures/README.md)
전제 조건: 대상마다 v2 촬영 조건(밀착 의류·약 2m·정면·r≈1)의 사진 + truth JSON
  + 랜드마크 캐시. 캐시가 없으면 --collect로 수집 (API 사용 — 명시 확인 후 실행).

사용:
  .\\venv\\Scripts\\python.exe scripts\\calibrate_multi.py               # 역산+집계 (API 0)
  .\\venv\\Scripts\\python.exe scripts\\calibrate_multi.py --collect 13  # 캐시 수집 (API 사용!)
"""

from __future__ import annotations

import base64
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import measure  # noqa: E402
from services.reference_detect import detect_aruco, detect_card  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
MANIFEST = FIXTURES / "calibration_set.json"

CIRC_KEYS = ("chest_circumference", "waist_circumference", "hip_circumference")
CIRC_TO_PART = {"chest_circumference": "chest", "waist_circumference": "waist",
                "hip_circumference": "hip"}
WIDTH_PAIRS = {
    "shoulder_width": ("left_shoulder", "right_shoulder"),
    "chest_circumference": ("chest_left", "chest_right"),
    "waist_circumference": ("waist_left", "waist_right"),
    "hip_circumference": ("hip_left", "hip_right"),
}


def load_manifest() -> list[dict]:
    if not MANIFEST.exists():
        raise SystemExit(
            f"manifest 없음: {MANIFEST}\n"
            "fixtures/README.md의 'calibration_set.json' 형식으로 대상을 등록하세요"
        )
    subjects = json.loads(MANIFEST.read_text(encoding="utf-8"))["subjects"]
    if not subjects:
        raise SystemExit("manifest에 등록된 대상이 없습니다")
    return subjects


def load_runs(stem: str) -> list[dict]:
    """랜드마크 캐시 로드: <stem>.landmarks.json + <stem>.landmarks.run*.json"""
    files = sorted(FIXTURES.glob(f"{stem}.landmarks*.json"))
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def collect_runs(stem: str, photo: Path, n: int) -> list[dict]:
    """랜드마크 캐시 수집 — ⚠️ 대상당 API n회 호출. --collect로만 실행됨."""
    from services.claude_vision import extract_body_landmarks  # 지연 임포트

    img = cv2.imread(str(photo))
    h, w = img.shape[:2]
    data = base64.b64encode(photo.read_bytes()).decode()
    runs = []
    for i in range(1, n + 1):
        lm = extract_body_landmarks(data, w, h)
        suffix = ".landmarks.json" if i == 1 else f".landmarks.run{i}.json"
        (FIXTURES / f"{stem}{suffix}").write_text(
            json.dumps(lm, indent=2), encoding="utf-8")
        runs.append(lm)
        print(f"  {stem}: {i}/{n} 수집")
    return runs


def analyze_subject(subj: dict, collect_n: int | None) -> dict:
    """대상 1명: 척도 확정 → 폭 원자료 → 계수 역산."""
    photo = FIXTURES / subj["photo"]
    truth = json.loads((FIXTURES / subj["truth"]).read_text(encoding="utf-8"))
    stem = photo.stem

    img = cv2.imread(str(photo))
    if img is None:
        raise SystemExit(f"{subj['id']}: 사진 없음 ({photo.name})")
    detect = detect_card if subj.get("reference") == "card" else detect_aruco
    ref = detect(img)
    if not ref["detected"]:
        raise SystemExit(f"{subj['id']}: 기준물 미검출 ({photo.name})")
    scale = measure.compute_scale(ref)

    runs = load_runs(stem)
    if not runs:
        if collect_n:
            print(f"⚠️ {subj['id']}: 캐시 없음 → API {collect_n}회로 수집합니다")
            runs = collect_runs(stem, photo, collect_n)
        else:
            raise SystemExit(
                f"{subj['id']}: 랜드마크 캐시 없음 ({stem}.landmarks*.json)\n"
                f"→ --collect 13 으로 수집 (API {13}회/대상) 후 재실행"
            )

    height_cm = float(truth["height"])
    weight_kg = truth.get("weight_kg")
    hs = measure.height_scale_from_runs(runs, height_cm)
    agree = measure.check_scale_agreement(hs["mmPerPx"], scale["mmPerPx"])

    # 폭 원자료 (키 척도 — A안): 런별 계산 후 중앙값
    widths_cm = {}
    for key, (lk, rk) in WIDTH_PAIRS.items():
        ds = [measure.scalar_distance_mm(hs["mmPerPx"], lm[lk], lm[rk]) / 10.0
              for lm in runs]
        widths_cm[key] = float(np.median(ds))

    # 계수 역산 (2-7b와 동일 산식 — verify_27b.py 참조)
    coefs = {"shoulder_coef": truth["shoulder_width"] / widths_cm["shoulder_width"]}
    adj = measure.bmi_depth_ratios(height_cm, weight_kg)
    for ck in CIRC_KEYS:
        part = CIRC_TO_PART[ck]
        d = 2.0 * truth[ck] / (math.pi * widths_cm[ck]) - 1.0
        # 파이프라인이 더할 BMI 가감을 제외한 base 값으로 저장
        coefs[f"depth_{part}"] = d - (adj[part] - measure.DEPTH_RATIOS[part])

    bmi = weight_kg / (height_cm / 100.0) ** 2 if weight_kg else None
    return {"id": subj["id"], "truth": truth, "widths": widths_cm, "coefs": coefs,
            "bmi": bmi, "agree": agree, "runs": len(runs),
            "marker_px": scale["trace"]["widthPx"]}


def predict_errors(subject: dict, coefs: dict) -> dict:
    """주어진 계수로 이 대상의 어깨·둘레를 예측했을 때의 오차 (LOO용)."""
    errors = {}
    pred_shoulder = subject["widths"]["shoulder_width"] * coefs["shoulder_coef"]
    errors["shoulder_width"] = pred_shoulder - subject["truth"]["shoulder_width"]
    adj = measure.bmi_depth_ratios(
        float(subject["truth"]["height"]), subject["truth"].get("weight_kg"))
    for ck in CIRC_KEYS:
        part = CIRC_TO_PART[ck]
        d = coefs[f"depth_{part}"] + (adj[part] - measure.DEPTH_RATIOS[part])
        pred = math.pi * subject["widths"][ck] * (1.0 + d) / 2.0
        errors[ck] = pred - subject["truth"][ck]
    return errors


def main():
    collect_n = None
    if "--collect" in sys.argv:
        idx = sys.argv.index("--collect")
        collect_n = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else 13
        print(f"⚠️ --collect 모드: 캐시 없는 대상마다 API {collect_n}회 호출됩니다")

    subjects = [analyze_subject(s, collect_n) for s in load_manifest()]
    n = len(subjects)
    coef_keys = list(subjects[0]["coefs"].keys())

    print("=" * 78)
    print(f"표 1 — 대상별 역산 계수 (N={n})")
    print("=" * 78)
    print(f"{'id':10} {'BMI':>5} {'r':>6} {'판정':>10} {'마커px':>7} "
          + "".join(f"{k:>15}" for k in coef_keys))
    for s in subjects:
        bmi = f"{s['bmi']:.1f}" if s["bmi"] else "-"
        print(f"{s['id']:10} {bmi:>5} {s['agree']['ratio']:6.3f} "
              f"{s['agree']['level']:>10} {s['marker_px']:7.1f}"
              + "".join(f"{s['coefs'][k]:15.4f}" for k in coef_keys))
        if s["agree"]["level"] != "ok":
            print(f"  ⚠️ {s['id']}: r 판정이 ok가 아님 — v2 촬영 조건(약 2m) 미달."
                  " 이 대상의 계수는 깊이 편향이 섞여 있어 집계에서 빼는 것을 검토")

    print()
    print("=" * 78)
    print("표 2 — 집계 (중앙값) vs 현재 measure.py 상수")
    print("=" * 78)
    current = {
        "shoulder_coef": measure.SHOULDER_CURVE_COEF,
        **{f"depth_{p}": v for p, v in measure.DEPTH_RATIOS.items()},
    }
    print(f"{'계수':15} {'집계 중앙값':>12} {'산포(max-min)':>14} {'현재 상수':>10} {'차이':>8}")
    for k in coef_keys:
        vals = [s["coefs"][k] for s in subjects]
        med, spr = float(np.median(vals)), max(vals) - min(vals)
        print(f"{k:15} {med:12.4f} {spr:14.4f} {current[k]:10.4f} {med - current[k]:+8.4f}")
    if n == 1:
        print("※ N=1 — 산포·일반화 판단 불가. 표본 3명+ 확보 시 재실행 (13-2)")

    print()
    print("=" * 78)
    print("표 3 — Leave-One-Out 교차 검증 (다른 사람들의 계수로 본인 예측)")
    print("=" * 78)
    if n < 2:
        print("N<2 — LOO 불가. 표본이 2명 이상이면 자동으로 수행된다.")
    else:
        items = ("shoulder_width",) + CIRC_KEYS
        print(f"{'id':10}" + "".join(f"{i:>24}" for i in items))
        all_errs = []
        for s in subjects:
            others = [o for o in subjects if o["id"] != s["id"]]
            loo = {k: float(np.median([o["coefs"][k] for o in others]))
                   for k in coef_keys}
            errs = predict_errors(s, loo)
            all_errs.append(errs)
            print(f"{s['id']:10}" + "".join(f"{errs[i]:+24.1f}" for i in items))
        flat = [abs(e[i]) for e in all_errs for i in items]
        print(f"±3cm 이내: {sum(1 for v in flat if v <= 3.0)}/{len(flat)}  "
              f"±5cm 이내: {sum(1 for v in flat if v <= 5.0)}/{len(flat)}")

    print()
    print("계수 상수 갱신은 수동: measure.py의 SHOULDER_CURVE_COEF / DEPTH_RATIOS를")
    print("사용자 결정 후 수정하고, pytest + scripts/verify_27b.py를 재실행할 것.")


if __name__ == "__main__":
    main()
