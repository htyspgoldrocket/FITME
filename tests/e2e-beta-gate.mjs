// 6-2 E2E — 베타 게이트: 코드 입력 + 개인정보·비상업 고지 + X-Beta-Code 전파
//
// 사전 조건: npm run dev (5173). 백엔드는 이 스크립트가 FITME_BETA_CODE를
// 설정한 가짜 백엔드(AI 0회)로 직접 띄운다. tests/fake-marker.y4m 필요.
//
// 시나리오: 게이트 표시(고지 포함) → 틀린 코드 거부 → 맞는 코드 통과 →
//           새로고침 시 게이트 생략(저장 코드 재검증) → 측정 완주(가드 활성
//           상태에서 /analyze에 X-Beta-Code 헤더가 실제로 실려 성공하는지)

import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const URL = 'http://localhost:5173';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const Y4M = join(ROOT, 'tests', 'fake-marker.y4m');
const PYTHON = join(ROOT, 'server', 'venv', 'Scripts', 'python.exe');
const CODE = 'e2e123';

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
  { cwd: ROOT, stdio: 'ignore', env: { ...process.env, FITME_BETA_CODE: CODE } },
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
  check('베타 백엔드 기동', await waitBackend(true));
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844 });

  // /analyze 요청의 X-Beta-Code 헤더 검사
  let analyzeCodeHeader = null;
  page.on('request', (req) => {
    if (req.url().includes('/api/analyze') && req.method() === 'POST') {
      analyzeCodeHeader = req.headers()['x-beta-code'] ?? null;
    }
  });

  await page.goto(URL, { waitUntil: 'networkidle2', timeout: 20000 });

  // 1) 게이트 표시 + 고지 문구
  await page.waitForSelector('.beta__input', { timeout: 10000 });
  check('베타 게이트 표시 (코드 입력 화면)', true);
  const gateText = await page.$eval('.beta', (el) => el.textContent);
  check('비상업 명시 (무료 베타)', gateText.includes('무료 베타') && gateText.includes('비상업'));
  check('개인정보 고지 (외부 전송)', gateText.includes('외부 AI 서버로 전송'));
  check('삭제 정책 고지 (1시간)', gateText.includes('1시간 후 자동 삭제'));

  // 2) 틀린 코드 → 거부
  await page.type('.beta__input', 'wrong-code');
  await page.click('.beta__btn');
  await page.waitForSelector('.beta__error', { timeout: 5000 });
  const err = await page.$eval('.beta__error', (el) => el.textContent);
  check(`틀린 코드 거부 (${err.slice(0, 14)}…)`, err.includes('올바르지 않'));

  // 3) 맞는 코드 → 모드 선택 진입 (제어 입력 교체는 Ctrl+A 후 타이핑 — 배운 것 2번)
  await page.click('.beta__input');
  await page.keyboard.down('Control');
  await page.keyboard.press('KeyA');
  await page.keyboard.up('Control');
  await page.type('.beta__input', CODE);
  await page.click('.beta__btn');
  await page.waitForSelector('.mode-select', { timeout: 5000 });
  check('맞는 코드 → 모드 선택 진입', true);

  // 4) 새로고침 → 저장된 코드 재검증으로 게이트 생략
  await page.reload({ waitUntil: 'networkidle2' });
  await page.waitForSelector('.mode-select', { timeout: 10000 });
  check('새로고침 시 게이트 생략 (코드 저장·재검증)', (await page.$('.beta__input')) === null);

  // 5) 가드 활성 상태에서 측정 완주 — 헤더가 안 실리면 403으로 실패한다
  await page.click('.mode-card--precise');
  await page.waitForSelector('.profile input');
  await page.type('.profile__field:nth-of-type(1) input', '172');
  await page.click('.profile__btn--primary');
  await page.waitForSelector('.camera-guide', { timeout: 10000 });
  await page.click('.camera-guide__confirm');
  await page.waitForSelector('.preview', { timeout: 30000 });
  await page.click('.preview__btn--primary');
  await page.waitForSelector('.result__table', { timeout: 30000 });
  const height = await page.$eval(
    '.result__table tr:first-child .result__value',
    (el) => el.textContent,
  );
  check(`가드 활성 측정 성공 (키 "${height.trim()}")`, height.trim() === '172.0 cm');
  check(`/analyze에 X-Beta-Code 헤더 전파 (${analyzeCodeHeader})`, analyzeCodeHeader === CODE);
} catch (e) {
  console.error('FAIL  예외 발생:', e.message);
  failures += 1;
} finally {
  backend.kill();
  await browser.close();
}

console.log(failures === 0 ? '\n전체 통과' : `\n실패 ${failures}건`);
process.exit(failures === 0 ? 0 : 1);
