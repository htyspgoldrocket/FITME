// 3-4b E2E — 의류 정보 화면: /clothing 실연동(가짜 스크래핑) 통짜 검증
//
// 사전 조건: npm run dev (5173) 만 떠 있으면 됨. 백엔드(8000)는 이 스크립트가
// 가짜 백엔드(tests/e2e_fake_backend.py — 무신사 접속·AI 호출 0)로 직접 띄운다.
// 정규화(3-3)·라우트·SQLite 캐시(3-4a)는 실제 코드가 돈다.
//
// 핵심 확인: 사이즈 표 표시(부위 컬럼 동적·단면×2 환산값), 뒤로가기 재진입 시
// 재요청 없음(App 캐시), URL 변경 시 재조회, 지원 외 쇼핑몰 → 한국어 안내

import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const URL_APP = 'http://localhost:5173';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const Y4M = join(ROOT, 'tests', 'fake-marker.y4m');
const PYTHON = join(ROOT, 'server', 'venv', 'Scripts', 'python.exe');
const MUSINSA_URL = 'https://www.musinsa.com/products/1234567';
const MUSINSA_URL_2 = 'https://www.musinsa.com/products/7654321';
const OTHER_MALL_URL = 'https://example.com/item/1';

let failures = 0;
function check(name, cond) {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}`);
  if (!cond) failures += 1;
}

if (!existsSync(Y4M)) {
  console.error('fake-marker.y4m 없음 — tests/gen_fake_camera.py 먼저 실행');
  process.exit(1);
}

async function waitBackend(up, tries = 40) {
  for (let i = 0; i < tries; i += 1) {
    try {
      await fetch('http://127.0.0.1:8000/health');
      if (up) return true;
    } catch {
      if (!up) return true;
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

if (!(await waitBackend(false, 1))) {
  console.error('8000 포트에 백엔드가 이미 떠 있음 — 내리고 다시 실행하세요');
  process.exit(1);
}

const backend = spawn(
  PYTHON,
  ['-m', 'uvicorn', 'tests.e2e_fake_backend:app', '--port', '8000'],
  { cwd: ROOT, stdio: 'ignore' },
);

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: [
    '--use-fake-device-for-media-stream',
    '--use-fake-ui-for-media-stream',
    `--use-file-for-fake-video-capture=${Y4M}`,
    '--no-sandbox',
  ],
});

/** React 제어 입력 값 교체 (삼중 클릭 불가 — Ctrl+A 후 타이핑, 배운 것 2번) */
async function replaceInput(page, selector, value) {
  await page.click(selector);
  await page.keyboard.down('Control');
  await page.keyboard.press('a');
  await page.keyboard.up('Control');
  await page.type(selector, value);
}

try {
  check('가짜 백엔드 기동', await waitBackend(true));
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844 });

  // /clothing 호출 수 추적 — App 캐시(재진입 재요청 방지) 검증용
  let clothingCalls = 0;
  page.on('request', (req) => {
    if (req.url().includes('/api/clothing') && req.method() === 'POST') {
      clothingCalls += 1;
    }
  });

  // 의류 URL 입력 화면까지 주행 (자동 촬영 → 측정 결과 경유)
  await page.goto(URL_APP, { waitUntil: 'networkidle2', timeout: 20000 });
  await page.click('.mode-card--precise');
  await page.waitForSelector('.profile input');
  await page.type('.profile__field:nth-of-type(1) input', '172');
  await page.click('.profile__btn--primary');
  await page.waitForSelector('.camera-guide', { timeout: 10000 });
  await page.click('.camera-guide__confirm');
  await page.waitForSelector('.preview', { timeout: 30000 });
  await page.click('.preview__btn--primary');
  await page.waitForSelector('.result__table', { timeout: 30000 });
  await page.click('.result__actions .result__btn--primary');
  await page.waitForSelector('.clothing input', { timeout: 5000 });

  // 정상 URL → 스펙 화면: 사이즈 표까지 로딩
  await page.type('.clothing input', MUSINSA_URL);
  await page.click('.clothing .profile__btn--primary');
  await page.waitForSelector('.clothing-spec .spec__table', { timeout: 15000 });
  // dev는 StrictMode가 마운트 효과를 2회 실행 → 1~2회가 정상 (프로덕션 1회)
  const baseline = clothingCalls;
  check(`사이즈 표 표시 (/clothing ${baseline}회 — StrictMode 이중 실행 포함)`,
    baseline >= 1 && baseline <= 2);

  const specText = await page.$eval('.clothing-spec', (el) => el.textContent);
  check('브랜드·상품명 표시', specText.includes('E2E BRAND'));
  check('카테고리 한국어 표시 (아우터)', specText.includes('아우터'));
  check('가슴단면 52.5 → 둘레 105 환산 표시', specText.includes('105'));

  const headers = await page.$$eval('.spec__table thead th', (els) =>
    els.map((el) => el.textContent),
  );
  check('제공 부위 컬럼만 표시 (가슴둘레 O)', headers.includes('가슴둘레'));
  check('없는 부위 컬럼 생략 (허리둘레 X)', !headers.includes('허리둘레'));

  const rows = await page.$$eval('.spec__table tbody tr', (els) => els.length);
  check(`사이즈 2종(S/M) 행 표시 (${rows}행)`, rows === 2);

  // 주소 다시 입력 → 같은 URL 재제출 → App 캐시로 재요청 없음
  await page.click('.clothing-spec .result__actions .result__btn');
  await page.waitForSelector('.clothing input', { timeout: 5000 });
  const kept = await page.$eval('.clothing input', (el) => el.value);
  check('재진입 시 URL 입력값 유지', kept === MUSINSA_URL);
  await page.click('.clothing .profile__btn--primary');
  await page.waitForSelector('.clothing-spec .spec__table', { timeout: 5000 });
  await new Promise((r) => setTimeout(r, 1000));
  check(`같은 URL 재진입 — 재요청 없음 (/clothing 총 ${clothingCalls}회)`,
    clothingCalls === baseline);

  // URL 변경 → 캐시 무효화 → 재조회
  await page.click('.clothing-spec .result__actions .result__btn');
  await page.waitForSelector('.clothing input', { timeout: 5000 });
  await replaceInput(page, '.clothing input', MUSINSA_URL_2);
  await page.click('.clothing .profile__btn--primary');
  await page.waitForSelector('.clothing-spec .spec__table', { timeout: 15000 });
  check(`URL 변경 시 재조회 (/clothing 총 ${clothingCalls}회)`,
    clothingCalls > baseline);

  // 지원 외 쇼핑몰 → ok=false 한국어 안내 (실제 라우트 unsupported 경로)
  await page.click('.clothing-spec .result__actions .result__btn');
  await page.waitForSelector('.clothing input', { timeout: 5000 });
  await replaceInput(page, '.clothing input', OTHER_MALL_URL);
  await page.click('.clothing .profile__btn--primary');
  await page.waitForFunction(
    () => document.querySelector('.clothing-spec h2')?.textContent
      ?.includes('가져오지 못했어요'),
    { timeout: 15000 },
  );
  const errText = await page.$eval('.clothing-spec', (el) => el.textContent);
  check('지원 외 쇼핑몰 안내 표시 (무신사 언급)', errText.includes('무신사'));

  // 안내 화면에서 주소 다시 입력으로 복귀
  await page.click('.clothing-spec .result__actions .result__btn--primary');
  await page.waitForSelector('.clothing input', { timeout: 5000 });
  check('오류 화면 → 주소 다시 입력 복귀', true);
} catch (e) {
  console.error('FAIL  예외 발생:', e.message);
  failures += 1;
} finally {
  backend.kill();
  await browser.close();
}

console.log(failures === 0 ? '\n전체 통과' : `\n실패 ${failures}건`);
process.exit(failures === 0 ? 0 : 1);
