// 2-8e E2E — 7프레임 캡처 + analyzeBody 실연동 + 측정 결과 화면
//
// 사전 조건: npm run dev (5173) 만 떠 있으면 됨. 백엔드(8000)는 이 스크립트가
// 시나리오에 맞춰 직접 띄운다 (tests/e2e_fake_backend.py — AI 호출 0).
// tests/fake-marker.y4m 필요 (tests/gen_fake_camera.py).
//
// 시나리오: 자동 촬영 → 미리보기(7프레임) → [백엔드 다운] 사용 → 오류 화면
//           → 가짜 백엔드 기동 → 다시 시도 → 측정 결과 테이블 (키 172.0)

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

// 백엔드가 이미 떠 있으면 이 시나리오(다운 상태 시작)가 성립하지 않음
if (!(await waitBackend(false, 1))) {
  console.error('8000 포트에 백엔드가 이미 떠 있음 — 내리고 다시 실행하세요');
  process.exit(1);
}

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

let backend = null;
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844 });

  // /analyze 요청 본문 검사 — 프레임 7장 + profile 포함 여부
  let framesLen = null;
  let sentProfile = null;
  page.on('request', (req) => {
    if (req.url().includes('/api/analyze') && req.method() === 'POST') {
      try {
        const body = JSON.parse(req.postData());
        framesLen = body.image?.frames?.length ?? 0;
        sentProfile = body.profile ?? null;
      } catch {
        /* postData 미제공 시 무시 */
      }
    }
  });

  await page.goto(URL, { waitUntil: 'networkidle2', timeout: 20000 });
  await page.click('.mode-card--precise');
  await page.waitForSelector('.profile input');
  await page.type('.profile__field:nth-of-type(1) input', '172');
  await page.type('.profile__field:nth-of-type(2) input', '78');
  await page.click('.profile__btn--primary');
  await page.waitForSelector('.camera-guide', { timeout: 10000 });
  await page.click('.camera-guide__confirm');

  // 자동 촬영(층위 3, 판정 서버 다운이므로 수동 경로) — 서버가 죽어도 수동
  // 셔터가 살아 있어야 한다 (2-8d 설계). 셔터 준비 후 직접 탭.
  await page.waitForSelector('.camera__shutter:not([disabled])', { timeout: 15000 });
  await page.click('.camera__shutter');
  await page.waitForSelector('.preview', { timeout: 20000 });
  check('판정 서버 다운 상태에서 수동 촬영 → 미리보기', true);

  // 미리보기 → 사용 → 측정 화면 (백엔드 다운 → 오류 UI)
  await page.click('.preview__btn--primary');
  await page.waitForSelector('.result', { timeout: 5000 });
  check('이 사진 사용 → 측정 화면 진입', true);
  await page.waitForFunction(
    () => document.querySelector('.result h2')?.textContent?.includes('실패'),
    { timeout: 20000 },
  );
  check(`요청 본문 frames=7 (실제 ${framesLen})`, framesLen === 7);
  check(
    `요청 본문 profile 포함 (${JSON.stringify(sentProfile)})`,
    sentProfile?.heightCm === 172 && sentProfile?.weightKg === 78,
  );
  check('백엔드 다운 → 오류 화면 + 다시 시도 버튼',
    (await page.$('.result__btn--primary')) !== null);

  // 가짜 백엔드 기동 (AI 0회 — 랜드마크만 합성으로 패치된 실제 앱)
  backend = spawn(
    PYTHON,
    ['-m', 'uvicorn', 'tests.e2e_fake_backend:app', '--port', '8000'],
    { cwd: ROOT, stdio: 'ignore' },
  );
  check('가짜 백엔드 기동', await waitBackend(true));

  // 다시 시도 → 로딩 → 측정 결과 테이블
  await page.click('.result__btn--primary');
  await page.waitForSelector('.result__table', { timeout: 30000 });
  const rows = await page.$$eval('.result__table tr', (l) => l.length);
  check(`측정 결과 테이블 8행 (실제 ${rows})`, rows === 8);
  const height = await page.$eval(
    '.result__table tr:first-child .result__value',
    (el) => el.textContent,
  );
  check(`키 캘리브레이션 반영: 첫 행 = "172.0 cm" (실제 "${height}")`,
    height.trim() === '172.0 cm');
  const badges = await page.$$eval('.result__conf', (l) => l.length);
  check(`신뢰도 배지 8개 (실제 ${badges})`, badges === 8);
  check('경고 섹션 표시 (합성 조건상 척도 경고 예상)',
    (await page.$('.result__warnings')) !== null);

  // 다시 촬영 → 카메라 복귀 (결과 화면에서의 재촬영 경로)
  await page.click('.result__actions .result__btn:not(.result__btn--primary)');
  await page.waitForSelector('.camera', { timeout: 10000 });
  check('결과 화면 → 다시 촬영 → 카메라 복귀', true);
} catch (e) {
  console.error('FAIL  예외 발생:', e.message);
  failures += 1;
} finally {
  if (backend) backend.kill();
  await browser.close();
}

console.log(failures === 0 ? '\n전체 통과' : `\n실패 ${failures}건`);
process.exit(failures === 0 ? 0 : 1);
