"""POST /check-photo — 촬영 품질 판정 (2-7c, 촬영 가이드 층위 3).

/analyze와 다르게 AI를 호출하지 않아 빠르고 무료다 — 실시간 폴링에 사용 가능.
"""

import base64
import binascii

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException

from models.schemas import CheckPhotoRequest, PhotoCheckResult
from services.photo_check import check_photo

router = APIRouter()


@router.post("/check-photo", response_model=PhotoCheckResult)
def check_photo_endpoint(req: CheckPhotoRequest) -> PhotoCheckResult:
    try:
        raw = base64.b64decode(req.image.base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=422, detail="base64 이미지 디코딩 실패")

    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=422, detail="이미지 형식을 해석할 수 없습니다")

    return PhotoCheckResult(**check_photo(image, req.mode))
