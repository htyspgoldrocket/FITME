# -*- coding: utf-8 -*-
"""GET /beta — 베타 게이트 상태 (Phase 6-2). AI 호출 0·사용량 카운트 0.

프론트가 앱 진입 시 "베타 코드 입력 화면을 띄울지"를 판단하는 UX용
엔드포인트. 실제 강제는 access_guard(6-1)가 AI 비용 라우트에서 수행하므로,
이 응답을 우회해도 비용은 보호된다. 프론트는 이 요청이 실패하면(서버 다운 등)
게이트 없이 진행한다(fail-open — UX는 열고 방어는 서버가).
"""

import os

from fastapi import APIRouter, Request

from models.schemas import BetaStatusResponse

router = APIRouter()


@router.get("/beta", response_model=BetaStatusResponse)
def beta_status(request: Request) -> BetaStatusResponse:
    expected = os.environ.get("FITME_BETA_CODE")
    if not expected:
        return BetaStatusResponse(active=False, codeOk=True)
    return BetaStatusResponse(
        active=True, codeOk=request.headers.get("x-beta-code") == expected
    )
