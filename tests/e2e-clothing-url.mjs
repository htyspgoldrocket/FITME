// 3-1 E2E — 측정 결과 → 의류 URL 입력 → 검증 → 의류 정보(stub) 전환
//
// 사전 조건: npm run dev (5173) 만 떠 있으면 됨. 백엔드(8000)는 이 스크립트가
// 가짜 백엔드(tests/e2e_fake_backend.py — AI 호출 0)로 직접 띄운다.
// tests/fake-marker.y4m 필요 (tests/gen_fake_camera.py).
//
// 핵심 확인: URL 형식 검증(빈 값·비정상 → 차단), 화면 전환, 뒤로가기 시
// 재분석 없음(/analyze 호출 수가 1로 유지 — App의 분석 캐시), 입력값 유지

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

// 가짜 백엔드를 처음부터 기동 (자동 촬영 + 분석 성공 경로)
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

try {
  check('가짜 백엔드 기동', await waitBackend(true));
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844 });

  // /analyze 호출 수 추적 — 캐시 동작(뒤로가기 재분석 방지) 검증용
  let analyzeCalls = 0;
  page.on('request', (req) => {
    if (req.url().includes('/api/analyze') && req.method() === 'POST') {
      analyzeCalls += 1;
    }
  });

  // 측정 결과 화면까지 주행 (자동 촬영 경로)
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
  // dev는 React StrictMode가 마운트 효과를 2회 실행 → 2회가 정상 (프로덕션은 1회).
  // 캐시 검증의 본질은 "뒤로가기 후 호출 수가 늘지 않음"이므로 기준값을 기록해 비교
  const baseline = analyzeCalls;
  check(`측정 결과 도달 (/analyze ${baseline}회 — StrictMode 이중 실행 포함)`,
    baseline >= 1 && baseline <= 2);

  // 결과 화면 → 의류 URL 입력 진입
  const nextBtn = await page.$('.result__actions .result__btn--primary');
  check('결과 화면에 "의류 사이즈 비교" 버튼 표시', nextBtn !== null);
  await page.click('.result__actions .result__btn--primary');
  await page.waitForSelector('.clothing', { timeout: 5000 });
  check('의류 URL 입력 화면 진입', true);

  // 검증: 빈 값 → 비활성
  const emptyDisabled = await page.$eval(
    '.clothing .profile__btn--primary',
    (el) => el.disabled,
  );
  check('빈 입력 시 다음 버튼 비활성', emptyDisabled);

  // 검증: 비정상 값 → 에러 힌트 + 비활성
  await page.type('.clothing input', 'not a url');
  const invalidHint = await page.$('.clothing .profile__hint--error');
  const invalidDisabled = await page.$eval(
    '.clothing .profile__btn--primary',
    (el) => el.disabled,
  );
  check('비정상 URL 시 에러 힌트 표시', invalidHint !== null);
  check('비정상 URL 시 다음 버튼 비활성', invalidDisabled);

  // 검증: 정상 URL → 활성 → 의류 정보(stub) 화면 전환
  // (React 제어 입력은 삼중 클릭 교체가 안 먹힘 — Ctrl+A 선택 후 타이핑으로 대체)
  await page.click('.clothing input');
  await page.keyboard.down('Control');
  await page.keyboard.press('a');
  await page.keyboard.up('Control');
  await page.type('.clothing input', MUSINSA_URL);
  const validEnabled = await page.$eval(
    '.clothing .profile__btn--primary',
    (el) => !el.disabled,
  );
  check('정상 URL 시 다음 버튼 활성', validEnabled);
  await page.click('.clothing .profile__btn--primary');
  await page.waitForSelector('.clothing-spec', { timeout: 5000 });
  const specText = await page.$eval('.clothing-spec', (el) => el.textContent);
  check('의류 정보(stub) 화면에 입력 주소 표시', specText.includes(MUSINSA_URL));

  // 주소 다시 입력 → 이전 입력값 유지 (App 보관)
  await page.click('.clothing-spec .result__actions .result__btn');
  await page.waitForSelector('.clothing', { timeout: 5000 });
  const kept = await page.$eval('.clothing input', (el) => el.value);
  check(`재진입 시 URL 입력값 유지 (${kept})`, kept === MUSINSA_URL);

  // 뒤로 (측정 결과) → 재분석 없이 캐시로 즉시 표시
  await page.click('.clothing .profile__actions .profile__btn:not(.profile__btn--primary)');
  await page.waitForSelector('.result__table', { timeout: 5000 });
  // 캐시로 즉시 표시돼야 하므로 /analyze 호출 수가 진입 시점과 동일해야 한다
  await new Promise((r) => setTimeout(r, 1500));
  check(`뒤로가기 후 측정 결과 재표시 — 재분석 없음 (/analyze 총 ${analyzeCalls}회)`,
    analyzeCalls === baseline);
} catch (e) {
  console.error('FAIL  예외 발생:', e.message);
  failures += 1;
} finally {
  backend.kill();
  await browser.close();
}

console.log(failures === 0 ? '\n전체 통과' : `\n실패 ${failures}건`);
process.exit(failures === 0 ? 0 : 1);
