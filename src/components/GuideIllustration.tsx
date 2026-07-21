// 층위 1 안내 픽토그램 (5-4 백로그 B-3) — 텍스트만으로는 촬영 조건이 잘
// 전달되지 않음이 1차 실기기에서 실증됨(근거리 접근·세로 카드). 항목별
// 그림을 곁들여 글을 읽지 않아도 핵심 조건이 보이게 한다.
// 인라인 SVG — 외부 이미지 없음(오프라인·번들 영향 0), 선 굵기·색은
// 오버레이 다크 배경 팔레트(index.css)와 동일 계열.

export type GuideKind = 'fit' | 'reference' | 'distance' | 'camera' | 'center';

/** 다크 배경 위 기본 선 색 (camera-guide 본문 텍스트와 동일 계열) */
const LINE = '#e5e7eb';
const ACCENT = '#facc15'; // 거리 자·기준물과 같은 노랑
const GOOD = '#4ade80';
const BAD = '#f87171';

interface GuideIllustrationProps {
  kind: GuideKind;
  /** reference 그림 전용 — 카드(가로 직사각형) vs 마커(정사각형 패턴) */
  refType: 'card' | 'marker';
}

/** 팔·다리 있는 졸라맨 (distance·center 공용) */
function StickFigure({ cx }: { cx: number }) {
  return (
    <g stroke={LINE} strokeWidth="2" strokeLinecap="round" fill="none">
      <circle cx={cx} cy="13" r="5" />
      <line x1={cx} y1="18" x2={cx} y2="38" />
      <line x1={cx} y1="24" x2={cx - 7} y2="32" />
      <line x1={cx} y1="24" x2={cx + 7} y2="32" />
      <line x1={cx} y1="38" x2={cx - 5} y2="52" />
      <line x1={cx} y1="38" x2={cx + 5} y2="52" />
    </g>
  );
}

/** 폰 + 삼각대 (distance·camera 공용) */
function PhoneOnTripod({ cx }: { cx: number }) {
  return (
    <g stroke={LINE} strokeWidth="2" strokeLinecap="round" fill="none">
      <rect x={cx - 4} y="20" width="8" height="15" rx="1.5" />
      <line x1={cx} y1="35" x2={cx} y2="42" />
      <line x1={cx} y1="42" x2={cx - 5} y2="52" />
      <line x1={cx} y1="42" x2={cx + 5} y2="52" />
    </g>
  );
}

function GuideIllustration({ kind, refType }: GuideIllustrationProps) {
  const common = {
    viewBox: '0 0 64 64',
    role: 'img' as const,
    'aria-hidden': true,
  };

  switch (kind) {
    case 'fit':
      // 밀착 티셔츠 ✓ vs 헐렁 티셔츠 ✗
      return (
        <svg {...common}>
          <g stroke={LINE} strokeWidth="2" strokeLinejoin="round" fill="none">
            {/* 슬림 핏 */}
            <path d="M12 12 L7 16 L10 22 L13 19 L13 38 L21 38 L21 19 L24 22 L27 16 L22 12 Q17 15 12 12 Z" />
            {/* 오버 핏 — 아래로 갈수록 퍼짐 */}
            <path d="M42 12 L36 16 L39 23 L42 20 L40 38 L56 38 L54 20 L57 23 L60 16 L52 12 Q47 15 42 12 Z" />
          </g>
          <polyline
            points="12,48 16,53 23,44"
            stroke={GOOD}
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
          />
          <g stroke={BAD} strokeWidth="3" strokeLinecap="round">
            <line x1="43" y1="45" x2="53" y2="54" />
            <line x1="53" y1="45" x2="43" y2="54" />
          </g>
        </svg>
      );
    case 'reference':
      // 가슴에 평평하게 붙인 기준물 — 카드는 가로 직사각형(B-1 실증: 세로 미지원)
      return (
        <svg {...common}>
          <g stroke={LINE} strokeWidth="2" strokeLinejoin="round" fill="none">
            <circle cx="32" cy="10" r="6" />
            <path d="M17 22 Q32 17 47 22 L49 54 L15 54 Z" />
          </g>
          {refType === 'card' ? (
            <rect
              x="23.5"
              y="29"
              width="17"
              height="10.7"
              rx="1.5"
              stroke={ACCENT}
              strokeWidth="2"
              fill="none"
            />
          ) : (
            <g>
              <rect x="26" y="28" width="12" height="12" stroke={ACCENT} strokeWidth="2" fill="none" />
              {/* ArUco 느낌의 내부 셀 */}
              <rect x="29" y="31" width="2.5" height="2.5" fill={ACCENT} />
              <rect x="33" y="34.5" width="2.5" height="2.5" fill={ACCENT} />
              <rect x="29" y="34.5" width="2.5" height="2.5" fill={ACCENT} opacity="0.45" />
            </g>
          )}
        </svg>
      );
    case 'distance':
      // 폰 ↔ 사람 약 2m — 1차 실기기 실패 주범(근거리)의 예방 그림
      return (
        <svg {...common}>
          <PhoneOnTripod cx={11} />
          <StickFigure cx={52} />
          <g stroke={ACCENT} strokeWidth="2" strokeLinecap="round">
            <line x1="20" y1="58" x2="44" y2="58" />
            <polyline points="24,55 20,58 24,61" fill="none" />
            <polyline points="40,55 44,58 40,61" fill="none" />
          </g>
          <text x="32" y="52" textAnchor="middle" fill={ACCENT} fontSize="9">
            약 2m
          </text>
        </svg>
      );
    case 'camera':
      // 폰을 배꼽~가슴 높이에 수직으로 — 점선이 사람 가슴 높이와 일직선
      return (
        <svg {...common}>
          <PhoneOnTripod cx={15} />
          <StickFigure cx={50} />
          <line
            x1="21"
            y1="27"
            x2="43"
            y2="27"
            stroke={ACCENT}
            strokeWidth="2"
            strokeDasharray="3 3"
            strokeLinecap="round"
          />
        </svg>
      );
    case 'center':
      // 프레임 정중앙 — 가장자리(광각 왜곡 구역)는 붉게 표시
      return (
        <svg {...common}>
          <rect x="9" y="5" width="46" height="54" rx="2" stroke={LINE} strokeWidth="2" fill="none" />
          <rect x="9" y="5" width="9" height="54" fill={BAD} opacity="0.3" />
          <rect x="46" y="5" width="9" height="54" fill={BAD} opacity="0.3" />
          <StickFigure cx={32} />
        </svg>
      );
  }
}

export default GuideIllustration;
