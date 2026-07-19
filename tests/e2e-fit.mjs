// 4-4b E2E — 핏 결과 화면: /fit 실연동(가짜 랜드마크·가짜 스크래핑·템플릿 피드백)
//
// 사전 조건: npm run dev (5173). 백엔드(8000)는 이 스크립트가 가짜 백엔드로
// 직접 띄운다 (tests/e2e_fake_backend.py — AI·무신사 접속 0. 핏 추천 로직
// 4-1/4-2와 라우트는 실제 코드가 돌고, 피드백만 템플릿 경로 강제).
//
// 핵심 확인: 측정→의류→핏까지 전체 흐름 연결(Phase 4 통합 검증의 데스크톱판),
// 추천 사이즈·부위별 판정 표·추천문 표시, 뒤로가기 재진입 시 재요청 없음(App 캐시)

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

  // /fit 호출 수 추적 — App 캐시(재진입 재요청 방지) 검증용
  let fitCalls = 0;
  page.on('request', (req) => {
    if (req.url().includes('/api/fit') && req.method() === 'POST') {
      fitCalls += 1;
    }
  });

  // 측정 → 의류 스펙 화면까지 주행 (자동 촬영 경로)
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
  await page.type('.clothing input', MUSINSA_URL);
  await page.click('.clothing .profile__btn--primary');
  await page.waitForSelector('.clothing-spec .spec__table', { timeout: 15000 });

  // 핏 분석 진입
  const fitBtn = await page.$('.clothing-spec .result__actions .result__btn--primary');
  check('의류 스펙 화면에 "핏 분석 보기" 버튼 표시 (측정 성공 시)', fitBtn !== null);
  await page.click('.clothing-spec .result__actions .result__btn--primary');
  await page.waitForSelector('.fit .result__table', { timeout: 15000 });
  const baseline = fitCalls;
  check(`핏 결과 도달 (/fit ${baseline}회 — StrictMode 이중 실행 포함)`,
    baseline >= 1 && baseline <= 2);

  // 결과 내용
  const size = await page.$eval('.fit__recommend-size', (el) => el.textContent.trim());
  check(`추천 사이즈 표시 ("${size}")`, size.length > 0);
  const rows = await page.$$eval('.fit .result__table tbody tr', (els) => els.length);
  check(`부위별 판정 행 표시 (${rows}행 — 가짜 아우터는 가슴·어깨 2행)`, rows === 2);
  const chips = await page.$$eval('.fit__status', (els) =>
    els.map((el) => el.className),
  );
  check('판정 배지(tight/good/loose) 표시', chips.length === rows
    && chips.every((c) => /fit__status--(tight|good|loose)/.test(c)));
  const reco = await page.$eval('.fit__recommendation', (el) => el.textContent);
  check('추천문 표시', reco.includes('추천'));
  check(`추천문이 추천 사이즈와 일치`, reco.includes(size));

  // 뒤로(의류 정보) → 재진입 → App 캐시로 재요청 없음
  await page.click('.fit .result__actions .result__btn'); // 의류 정보로
  await page.waitForSelector('.clothing-spec .spec__table', { timeout: 5000 });
  await page.click('.clothing-spec .result__actions .result__btn--primary');
  await page.waitForSelector('.fit .result__table', { timeout: 5000 });
  await new Promise((r) => setTimeout(r, 1000));
  check(`재진입 — 재요청 없음 (/fit 총 ${fitCalls}회)`, fitCalls === baseline);

  // 처음으로 복귀 (전체 흐름 종결)
  await page.click('.fit .result__actions .result__btn:nth-of-type(2)');
  await page.waitForSelector('.mode-card--precise', { timeout: 5000 });
  check('처음으로 복귀', true);
} catch (e) {
  console.error('FAIL  예외 발생:', e.message);
  failures += 1;
} finally {
  backend.kill();
  await browser.close();
}

console.log(failures === 0 ? '\n전체 통과' : `\n실패 ${failures}건`);
process.exit(failures === 0 ? 0 : 1);
