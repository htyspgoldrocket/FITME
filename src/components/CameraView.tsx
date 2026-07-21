import { useEffect, useRef, useState } from 'react';
import {
  gyroNeedsPermission,
  requestGyroPermission,
  startCamera,
  stopCamera,
  watchTilt,
  VERTICAL_TOLERANCE_DEG as TILT_TOLERANCE_DEG,
  type CameraFacing,
  type TiltState,
} from '../lib/camera';
import { checkPhoto } from '../lib/api';
import { captureFromVideo } from '../lib/image';
import type { MeasurementMode, PhotoCheckResult } from '../types';

/** 셔터 타이머(초). 0 = 즉시 촬영 */
export type TimerSeconds = 0 | 3 | 5 | 10;
export const TIMER_OPTIONS: TimerSeconds[] = [0, 3, 5, 10];

// ===== 층위 3 — 실시간 검증 + 자동 촬영 (2-8d, 서버 폴링 방식 확정) =====
const POLL_INTERVAL_MS = 1200; // 응답 수신 후 다음 폴링까지 간격 (직렬 — 요청 중첩 없음)
const AUTO_COUNTDOWN_SEC = 3; // 조건 충족 시 자동 촬영 카운트다운
const READY_STREAK_TO_SHOOT = 2; // 연속 ready 판정 수 — 일시적 통과(깜빡임) 오발사 방지
const CANCEL_COOLDOWN_MS = 8000; // 사용자가 자동 카운트다운을 취소하면 잠시 재발동 억제

// ===== 5-4 개선 ② — 원거리 인지: 사용자는 카메라에서 2m 떨어져 있어
// 배너 글씨를 읽을 수 없다. 판정 사유를 TTS로 읽어주고, 화면 전체 테두리
// 색(빨강=미충족/초록=ready)으로 멀리서도 상태를 알 수 있게 한다.
const RESPEAK_INTERVAL_MS = 7000; // 같은 안내를 다시 읽어주기까지의 간격 (잔소리 방지)

// ===== 5-4 백로그 ④ 보완 — 실루엣·거리 자를 입력 키에 비례해 스케일 =====
// 고정 실루엣은 "선에 맞추기 = 픽셀 크기 고정 = 거리가 키에 비례"가 되어
// 작은 키를 근거리(깊이 편향)로 유도한다 — 마커 픽셀 밴드(절대 거리)와 충돌.
// 발 위치는 바닥선이라 키와 무관하므로 발 기준으로 고정하고 높이만 키에
// 비례시키면 "선에 맞추기 = 누구나 약 2m"이 성립한다.
const REF_HEIGHT_CM = 170; // BASE_SILHOUETTE_PCT가 나타내는 기준 키
const BASE_SILHOUETTE_PCT = 83; // 기준 키의 실루엣 화면 높이 % (기존 CSS 튜닝값)
const SILHOUETTE_BOTTOM_PCT = 12; // 발 고정 앵커 (기존 CSS bottom 값)
const SILHOUETTE_SCALE_MIN = 0.75; // 프로필 하드 한계(100~250)의 UI 폭주 방지
const SILHOUETTE_SCALE_MAX = 1.05;
// 기준물 문구 칩의 실루엣 내 상대 위치 — 기존 튜닝값(24%/28.5%)을 역산한 상수
const CHIP_K_PRECISE = 0.2289;
const CHIP_K_CARD = 0.2831;

function speak(text: string) {
  if (!('speechSynthesis' in window)) return; // 미지원 브라우저 — 시각 안내만
  window.speechSynthesis.cancel(); // 밀린 안내가 쌓여 뒤늦게 읽히는 것 방지
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'ko-KR';
  u.rate = 1.05;
  window.speechSynthesis.speak(u);
}

interface CameraViewProps {
  mode: MeasurementMode;
  /** 전면/후면 선택 — 재촬영 등 화면 전환 후에도 유지되도록 App이 보관 */
  facing: CameraFacing;
  onToggleFacing: () => void;
  /** 셔터 타이머 — facing과 동일하게 App이 보관해 재촬영 후에도 유지 */
  timerSec: TimerSeconds;
  onCycleTimer: () => void;
  onBack: () => void;
  /** 촬영 버튼 탭 시 현재 비디오 프레임 전달 — 캡처 파이프라인은 Step 1-6 */
  onShutter: (video: HTMLVideoElement) => void;
  /** 층위 1 정적 안내(2-8c) — 세션 첫 진입에만 자동 표시되도록 App이 보관 */
  showGuide: boolean;
  onDismissGuide: () => void;
  /** 층위 3 자동 촬영(2-8d) — 재촬영 후에도 유지되도록 App이 보관 */
  autoShoot: boolean;
  onToggleAutoShoot: () => void;
  /** 음성 안내(5-4 ②) — 원거리에서 배너 대신 판정 사유를 읽어준다. App이 보관 */
  voiceGuide: boolean;
  onToggleVoiceGuide: () => void;
  /** 다중 프레임 캡처 진행 중(2-8e) — 셔터 잠금 + 정지 안내 + 폴링 일시정지 */
  capturing: boolean;
  /** 사용자 키(cm) — 실루엣·거리 자 스케일용 (프로필 입력값, App이 보관) */
  heightCm: number;
}

/** 층위 1 — 촬영 전 정적 안내 항목 (CLAUDE.md 전략 1 4층위 명세) */
const GUIDE_ITEMS: { icon: string; text: (refName: string) => string }[] = [
  { icon: '👕', text: () => '몸에 밀착되는 옷을 입어 주세요 — 헐렁한 옷은 측정을 크게 왜곡해요' },
  {
    icon: '📐',
    // 카드는 가로 방향+대비 조건이 검출 성패를 가른다 (5-4 실기기 실증 — 백로그 ⑤)
    text: (ref) =>
      ref === '카드'
        ? '카드를 가슴에 가로 방향으로 평평하게 — 어두운 옷 위에서 잘 검출돼요'
        : `${ref}를 가슴에 평평하게 대 주세요`,
  },
  { icon: '📏', text: () => '약 2m 거리에서 — 머리와 발이 노란 선에 오면 딱 좋아요' },
  { icon: '📱', text: () => '카메라는 배꼽~가슴 높이에서 수직으로 (거치대 + 타이머 활용)' },
  { icon: '🧍', text: () => '몸을 화면 정중앙에 — 가장자리는 광각 왜곡이 생겨요' },
];

/** 촬영 화면 — 전/후면 카메라 + 전신/기준물 가이드 오버레이 + 자이로 수직 표시 */
function CameraView({
  mode,
  facing,
  onToggleFacing,
  timerSec,
  onCycleTimer,
  onBack,
  onShutter,
  showGuide,
  onDismissGuide,
  autoShoot,
  onToggleAutoShoot,
  voiceGuide,
  onToggleVoiceGuide,
  capturing,
  heightCm,
}: CameraViewProps) {
  // 실루엣 높이 = 기준 % × (키/기준 키), 발 기준 고정 — 위 스케일 상수 주석 참조
  const silhouettePct =
    BASE_SILHOUETTE_PCT *
    Math.min(SILHOUETTE_SCALE_MAX, Math.max(SILHOUETTE_SCALE_MIN, heightCm / REF_HEIGHT_CM));
  // 기준물 칩은 실루엣 가슴을 따라간다: 실루엣 상단(100-bottom-높이)% + 높이×k
  const chipTopPct =
    100 -
    SILHOUETTE_BOTTOM_PCT -
    silhouettePct +
    silhouettePct * (mode === 'simple' ? CHIP_K_CARD : CHIP_K_PRECISE);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);
  // 층위 1 안내: 세션 첫 진입엔 자동으로 열리고, 이후엔 ❓ 버튼으로 재열람
  const [guideOpen, setGuideOpen] = useState(showGuide);
  // 층위 3: 최신 판정 결과 (null = 아직 없음/서버 오류)
  const [check, setCheck] = useState<PhotoCheckResult | null>(null);
  const [serverDown, setServerDown] = useState(false);
  // 연속 ready 횟수 — READY_STREAK_TO_SHOOT 이상이면 자동 카운트다운 발동
  const readyStreak = useRef(0);
  // 진행 중인 카운트다운의 출처 — 조건 깨짐 취소는 auto에만 적용 (수동 타이머 보호)
  const countdownSource = useRef<'auto' | 'manual' | null>(null);
  // 사용자가 자동 카운트다운을 취소한 직후의 재발동 억제 시각
  const cooldownUntil = useRef(0);
  const [tilt, setTilt] = useState<TiltState | null>(null);
  const [needsGyroTap, setNeedsGyroTap] = useState(false);
  // 스트림 준비 전(초기 로딩·전환 중) 셔터를 막아 빈 프레임 캡처를 방지
  const [ready, setReady] = useState(false);
  // 타이머 카운트다운 남은 초 (null = 카운트다운 아님)
  const [countdown, setCountdown] = useState<number | null>(null);

  // 음성 안내(5-4 ②) — 폴링 클로저에서 최신 토글값을 보도록 ref 미러 + 중복 발화 억제
  const voiceOnRef = useRef(voiceGuide);
  const lastSpoken = useRef<{ text: string; at: number }>({ text: '', at: 0 });
  useEffect(() => {
    voiceOnRef.current = voiceGuide;
    if (!voiceGuide && 'speechSynthesis' in window) window.speechSynthesis.cancel();
  }, [voiceGuide]);
  // 화면 이탈 시 읽던 안내 즉시 중단
  useEffect(
    () => () => {
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    },
    [],
  );
  const speakGuidance = (text: string) => {
    if (!voiceOnRef.current) return;
    const now = Date.now();
    if (lastSpoken.current.text === text && now - lastSpoken.current.at < RESPEAK_INTERVAL_MS) {
      return;
    }
    lastSpoken.current = { text, at: now };
    speak(text);
  };

  // 카메라 시작/정지 (방향 전환 시 스트림 재시작)
  useEffect(() => {
    let stream: MediaStream | null = null;
    let cancelled = false;
    setReady(false);
    setCountdown(null); // 카메라 전환 시 진행 중이던 카운트다운 취소
    countdownSource.current = null;
    (async () => {
      try {
        stream = await startCamera(facing);
        if (cancelled) {
          stopCamera(stream);
          return;
        }
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadeddata = () => setReady(true);
        }
      } catch (e) {
        setError(
          '카메라를 열 수 없습니다. 브라우저 카메라 권한을 허용해 주세요. ' +
            `(${e instanceof Error ? e.message : String(e)})`,
        );
      }
    })();
    return () => {
      cancelled = true;
      if (videoRef.current) {
        videoRef.current.onloadeddata = null;
      }
      stopCamera(stream);
    };
  }, [facing]);

  // 자이로 감시 (iOS는 별도 탭 필요)
  useEffect(() => {
    if (gyroNeedsPermission()) {
      setNeedsGyroTap(true);
      return;
    }
    return watchTilt(setTilt);
  }, []);

  // 카운트다운 진행: 1초마다 감소, 0이 되면 촬영. 화면 이탈 시 자동 정리.
  useEffect(() => {
    if (countdown === null) return;
    if (countdown <= 0) {
      setCountdown(null);
      countdownSource.current = null;
      if (videoRef.current) onShutter(videoRef.current);
      return;
    }
    if (voiceOnRef.current) speak(String(countdown)); // 원거리 카운트다운 안내
    const id = window.setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => window.clearTimeout(id);
  }, [countdown, onShutter]);

  // 층위 3 — /check-photo 서버 폴링 (직렬: 응답 후 POLL_INTERVAL_MS 뒤 다음 요청).
  // 조건 연속 충족 → 자동 카운트다운, 카운트다운 중 조건 깨지면 취소.
  // 서버 미응답이어도 수동 촬영 경로는 그대로 살아 있다.
  useEffect(() => {
    if (!autoShoot || !ready || guideOpen || capturing) return;
    let stopped = false;
    let timer: number | undefined;
    readyStreak.current = 0;

    const tick = async () => {
      const video = videoRef.current;
      if (video && !stopped) {
        try {
          const result = await checkPhoto(captureFromVideo(video), mode);
          if (stopped) return;
          setServerDown(false);
          setCheck(result);
          // 원거리 음성 안내 — ready면 유지 안내, 아니면 첫 번째 사유를 읽어준다
          if (result.ready) speakGuidance('좋아요! 그대로 계세요');
          else if (result.reasons.length > 0) speakGuidance(result.reasons[0]);
          if (result.ready) {
            readyStreak.current += 1;
            if (
              readyStreak.current >= READY_STREAK_TO_SHOOT &&
              Date.now() >= cooldownUntil.current
            ) {
              setCountdown((c) => {
                if (c !== null) return c; // 이미 진행 중(수동 포함)이면 유지
                countdownSource.current = 'auto';
                return AUTO_COUNTDOWN_SEC;
              });
            }
          } else {
            readyStreak.current = 0;
            if (countdownSource.current === 'auto') {
              countdownSource.current = null;
              setCountdown(null); // 조건 깨짐 — 자동 카운트다운만 취소
            }
          }
        } catch {
          if (stopped) return;
          setServerDown(true);
          setCheck(null);
          readyStreak.current = 0;
        }
      }
      if (!stopped) timer = window.setTimeout(tick, POLL_INTERVAL_MS);
    };
    tick();
    return () => {
      stopped = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [autoShoot, ready, guideOpen, mode, capturing]);

  const handleShutterClick = () => {
    if (countdown !== null) {
      // 카운트다운 중 재탭 = 취소. 자동 발동이었다면 잠시 재발동을 억제한다.
      if (countdownSource.current === 'auto') {
        cooldownUntil.current = Date.now() + CANCEL_COOLDOWN_MS;
        readyStreak.current = 0;
      }
      countdownSource.current = null;
      setCountdown(null);
      return;
    }
    if (timerSec === 0) {
      if (videoRef.current) onShutter(videoRef.current);
      return;
    }
    countdownSource.current = 'manual';
    setCountdown(timerSec);
  };

  const enableGyro = async () => {
    if (await requestGyroPermission()) {
      setNeedsGyroTap(false);
      watchTilt(setTilt); // 화면을 떠날 때 컴포넌트가 사라지므로 정리 생략 가능하지만,
      // 안전하게 unmount 시 정리되도록 상태로 두지 않고 이벤트만 등록
    }
  };

  if (error) {
    return (
      <div className="camera camera--error">
        <p>{error}</p>
        <button type="button" onClick={onBack}>
          뒤로
        </button>
      </div>
    );
  }

  return (
    <div className="camera">
      {/* 전면 카메라는 미리보기만 거울상 — 캡처(captureFromVideo)는 원본 프레임이라 반전 없음 */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={
          'camera__video' + (facing === 'user' ? ' camera__video--mirrored' : '')
        }
      />

      {/* 5-4 ② — 원거리(2m)에서도 보이는 판정 상태 테두리 (빨강=미충족/초록=ready) */}
      {!guideOpen && autoShoot && !serverDown && check !== null && (
        <div
          className={'camera__edge camera__edge--' + (check.ready ? 'ok' : 'warn')}
          aria-hidden="true"
        />
      )}

      {/* 층위 2 — 정중앙 실루엣 가이드 (광각 가장자리 회피) + 기준물 위치 */}
      <div className="camera__overlay" aria-hidden="true">
        <svg
          className="camera__silhouette"
          viewBox="0 0 100 200"
          preserveAspectRatio="xMidYMid meet"
          style={{
            top: 'auto',
            bottom: `${SILHOUETTE_BOTTOM_PCT}%`,
            height: `${silhouettePct}%`,
          }}
        >
          <circle cx="50" cy="14" r="12" />
          <path
            d="M44 27 L30 34 L18 78 L26 82 L34 52 L33 96 L38 186 L48 186
               L50 120 L52 186 L62 186 L67 96 L66 52 L74 82 L82 78 L70 34
               L56 27 Z"
          />
          {/* 5-4 백로그 ⑤ — 간편 모드: 가로 방향 카드 박스 (세로 카드는 검출
              미지원 ±45°, 1차 실기기 실증). 비율은 ISO 카드 85.6:53.98 */}
          {mode === 'simple' && (
            <rect
              className="camera__card-box"
              x="39"
              y="40"
              width="22"
              height="13.9"
              rx="1.5"
            />
          )}
          {/* 5-4 백로그 ④ — 거리 자: 머리·발을 선에 맞추면 약 2m. 층위 3
              판정(마커 픽셀 밴드) 이전의 예방 층 — 1차 실기기에서 근거리
              접근이 A파트 실패 주범. viewBox 좌표라 화면 비율과 무관하게
              실루엣 머리(y=2)·발(y=186)에 정확히 붙는다 */}
          <line className="camera__ruler-line" x1="2" y1="2" x2="98" y2="2" />
          <line className="camera__ruler-line" x1="2" y1="186" x2="98" y2="186" />
          <text className="camera__ruler-text" x="98" y="8" textAnchor="end">
            머리를 이 선에
          </text>
          {/* 발 라벨은 선보다 위(y=170) — 하단 고정 토글·배너(camera__status,
              bottom 118px)와 겹치지 않게. ↓로 아래 선을 가리킨다 */}
          <text className="camera__ruler-text" x="98" y="170" textAnchor="end">
            ↓ 발을 이 선에 — 약 2m
          </text>
        </svg>
        <div className="camera__ref-guide" style={{ top: `${chipTopPct}%` }}>
          {mode === 'simple'
            ? '💳 카드를 가로 방향으로, 어두운 상의 위에'
            : '🔳 마커를 여기(가슴 부근)에'}
        </div>
      </div>

      {/* 상단 바: 뒤로 + 안내 + 자이로 2축(좌우 수평·앞뒤 기울기) 표시 */}
      <div className="camera__top">
        <button type="button" className="camera__back" onClick={onBack}>
          ←
        </button>
        <span className="camera__hint">약 2m 거리 — 머리·발을 노란 선에</span>
        {tilt && (
          <span className="camera__tilt-group">
            <span
              className={
                'camera__tilt ' +
                (Math.abs(tilt.rollDeg) <= TILT_TOLERANCE_DEG
                  ? 'camera__tilt--ok'
                  : 'camera__tilt--bad')
              }
            >
              {Math.abs(tilt.rollDeg) <= TILT_TOLERANCE_DEG ? '↔ 수평 OK' : '↔ 좌우 수평을'}
            </span>
            <span
              className={
                'camera__tilt ' +
                (Math.abs(tilt.pitchDeg) <= TILT_TOLERANCE_DEG
                  ? 'camera__tilt--ok'
                  : 'camera__tilt--bad')
              }
            >
              {Math.abs(tilt.pitchDeg) <= TILT_TOLERANCE_DEG ? '↕ 수직 OK' : '↕ 폰을 세워서'}
            </span>
          </span>
        )}
        {needsGyroTap && (
          <button type="button" className="camera__gyro-btn" onClick={enableGyro}>
            수직 가이드 켜기
          </button>
        )}
        <button
          type="button"
          className="camera__help"
          aria-label="촬영 방법 안내"
          onClick={() => setGuideOpen(true)}
        >
          ?
        </button>
      </div>

      {/* 층위 1 — 촬영 전 정적 안내 (세션 첫 진입 자동 표시, ❓로 재열람) */}
      {guideOpen && (
        <div className="camera-guide" role="dialog" aria-label="촬영 방법 안내">
          <h2 className="camera-guide__title">정확한 측정을 위한 촬영 방법</h2>
          <ul className="camera-guide__list">
            {GUIDE_ITEMS.map(({ icon, text }) => (
              <li key={icon}>
                <span className="camera-guide__icon">{icon}</span>
                {text(mode === 'simple' ? '카드' : '마커')}
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="camera-guide__confirm"
            onClick={() => {
              setGuideOpen(false);
              onDismissGuide();
            }}
          >
            확인했어요
          </button>
        </div>
      )}

      {/* 카운트다운 표시 */}
      {countdown !== null && countdown > 0 && (
        <div className="camera__countdown" aria-live="assertive">
          {countdown}
        </div>
      )}

      {/* 다중 프레임 캡처 중 안내 (약 2초) — 흔들리면 중앙값 품질이 떨어진다 */}
      {capturing && (
        <div className="camera__capturing" aria-live="assertive">
          📸 측정용 사진 여러 장을 찍고 있어요 — 움직이지 마세요
        </div>
      )}

      {/* 층위 3 — 자동 촬영 토글 + 실시간 판정 배너 */}
      {!guideOpen && (
        <div className="camera__status">
          <button
            type="button"
            className={'camera__auto' + (autoShoot ? ' camera__auto--on' : '')}
            onClick={onToggleAutoShoot}
          >
            자동 촬영 {autoShoot ? 'ON' : 'OFF'}
          </button>
          <button
            type="button"
            className={'camera__auto' + (voiceGuide ? ' camera__auto--on' : '')}
            onClick={onToggleVoiceGuide}
          >
            🔊 음성 {voiceGuide ? 'ON' : 'OFF'}
          </button>
          {autoShoot && (
            <span
              className={
                'camera__banner ' +
                (serverDown || check === null
                  ? 'camera__banner--idle'
                  : check.ready
                    ? 'camera__banner--ok'
                    : 'camera__banner--warn')
              }
            >
              {serverDown
                ? '판정 서버에 연결할 수 없어요 — 수동 촬영은 가능해요'
                : check === null
                  ? '촬영 조건 확인 중…'
                  : check.ready
                    ? countdown !== null
                      ? '✓ 좋아요! 곧 촬영해요'
                      : '✓ 좋아요! 이대로 계세요'
                    : check.reasons[0]}
            </span>
          )}
        </div>
      )}

      {/* 하단: 타이머 + 셔터 + 카메라 전환 */}
      <div className="camera__bottom">
        <button
          type="button"
          className="camera__timer"
          aria-label="셔터 타이머"
          onClick={onCycleTimer}
          disabled={countdown !== null}
        >
          ⏱ {timerSec === 0 ? '끔' : `${timerSec}초`}
        </button>
        <button
          type="button"
          className={
            'camera__shutter' +
            (countdown !== null ? ' camera__shutter--counting' : '')
          }
          aria-label={countdown !== null ? '카운트다운 취소' : '촬영'}
          disabled={!ready || capturing}
          onClick={handleShutterClick}
        />
        <button
          type="button"
          className="camera__flip"
          aria-label="카메라 전환"
          onClick={onToggleFacing}
        >
          🔄 {facing === 'environment' ? '전면' : '후면'}
        </button>
      </div>
    </div>
  );
}

export default CameraView;
