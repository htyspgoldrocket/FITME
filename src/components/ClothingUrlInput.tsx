import { useState } from 'react';

interface ClothingUrlInputProps {
  /** 재진입 시 이전 입력 유지 — 값은 App이 보관한다 */
  initial: string | null;
  onSubmit: (url: string) => void;
  onBack: () => void;
}

type Parsed = { kind: 'empty' } | { kind: 'invalid' } | { kind: 'ok'; url: string };

// http(s) 주소만 허용 — 지원 쇼핑몰 여부 판정은 백엔드 몫(3-2에서 무신사 먼저)
function parseUrl(value: string): Parsed {
  const trimmed = value.trim();
  if (trimmed === '') return { kind: 'empty' };
  try {
    const u = new URL(trimmed);
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return { kind: 'invalid' };
    return { kind: 'ok', url: u.toString() };
  } catch {
    return { kind: 'invalid' };
  }
}

/** 의류 URL 입력 화면 (3-1) — 폼 스타일은 ProfileInput의 profile__* 클래스 재사용 */
function ClothingUrlInput({ initial, onSubmit, onBack }: ClothingUrlInputProps) {
  const [urlStr, setUrlStr] = useState(initial ?? '');
  const parsed = parseUrl(urlStr);

  const handleSubmit = () => {
    if (parsed.kind !== 'ok') return;
    onSubmit(parsed.url);
  };

  return (
    <div className="profile clothing">
      <header className="profile__header">
        <h1>의류 주소 입력</h1>
        <p>사이즈를 비교할 옷의 상품 페이지 주소를 붙여넣어 주세요</p>
      </header>

      <label className="profile__field">
        <span className="profile__label">
          상품 페이지 URL <em className="profile__required">필수</em>
        </span>
        <input
          type="url"
          inputMode="url"
          placeholder="예: https://www.musinsa.com/products/..."
          value={urlStr}
          onChange={(e) => setUrlStr(e.target.value)}
          autoFocus
        />
        <span
          className={
            parsed.kind === 'invalid'
              ? 'profile__hint profile__hint--error'
              : 'profile__hint'
          }
        >
          {parsed.kind === 'invalid'
            ? 'http(s)로 시작하는 주소를 입력해 주세요'
            : '현재 무신사를 먼저 지원해요 — 다른 쇼핑몰은 이후 순차 확대'}
        </span>
      </label>

      <div className="profile__actions">
        <button type="button" className="profile__btn" onClick={onBack}>
          뒤로 (측정 결과)
        </button>
        <button
          type="button"
          className="profile__btn profile__btn--primary"
          disabled={parsed.kind !== 'ok'}
          onClick={handleSubmit}
        >
          다음 (사이즈 확인)
        </button>
      </div>
    </div>
  );
}

export default ClothingUrlInput;
