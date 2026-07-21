"""Phase 5-1 단독 테스트: Replicate cuuupid/idm-vton 합성 1회 호출.

⚠️ 개발/테스트 전용 — 이 모델(CC BY-NC-SA 4.0, 상업 사용 금지)은 출시 전
FASHN API 등으로 교체 필요 (CLAUDE.md 12장 참조).

실행: server/venv/Scripts/python.exe scripts/test_vton_standalone.py
"""
import os
import sys
from pathlib import Path

import replicate

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

HUMAN_IMG = FIXTURES / "person01_v2_aruco.jpg"
GARM_IMG_URL = (
    "https://image.msscdn.net/images/goods_img/20190327/996177/"
    "996177_17845258066104_500.jpg"
)
OUTPUT_PATH = FIXTURES / "debug_vton_test01.jpg"


def _load_token() -> str:
    if os.environ.get("REPLICATE_API_TOKEN"):
        return os.environ["REPLICATE_API_TOKEN"]
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith("REPLICATE_API_TOKEN=") and not line.startswith("#"):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
                if token:
                    return token
    raise RuntimeError("REPLICATE_API_TOKEN을 찾을 수 없습니다 (server/.env 또는 환경변수)")


def main() -> None:
    os.environ["REPLICATE_API_TOKEN"] = _load_token()

    if not HUMAN_IMG.exists():
        print(f"사람 이미지 없음: {HUMAN_IMG}", file=sys.stderr)
        sys.exit(1)

    print(f"human_img = {HUMAN_IMG}")
    print(f"garm_img  = {GARM_IMG_URL}")
    print("호출 중... (수십 초 소요될 수 있음)")

    with open(HUMAN_IMG, "rb") as human_file:
        output = replicate.run(
            "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985",
            input={
                "human_img": human_file,
                "garm_img": GARM_IMG_URL,
                "garment_des": "plain crewneck t-shirt",
                "category": "upper_body",
            },
        )

    print(f"output 타입: {type(output)}")
    print(f"output 값: {output!r}")

    data = output.read() if hasattr(output, "read") else None
    if data is None and isinstance(output, str):
        import urllib.request

        with urllib.request.urlopen(output, timeout=60) as resp:
            data = resp.read()
    if data is None and isinstance(output, list) and output:
        item = output[0]
        data = item.read() if hasattr(item, "read") else None

    if data:
        OUTPUT_PATH.write_bytes(data)
        print(f"저장 완료: {OUTPUT_PATH} ({len(data)} bytes)")
    else:
        print("⚠️ output에서 이미지 바이트를 추출하지 못함 — 위 output 값을 보고 형식 확인 필요")


if __name__ == "__main__":
    main()
