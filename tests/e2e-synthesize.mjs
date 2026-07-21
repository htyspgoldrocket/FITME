// 5-3c E2E — 가상 착용 보기: /synthesize 실연동(가짜 VTON, API 0회)
//
// 사전 조건: npm run dev (5173). 백엔드(8000)는 이 스크립트가 가짜 백엔드로
// 직접 띄운다 (tests/e2e_fake_backend.py — VTON 호출 0. 라우트 로직
// (imageUrl 검증, base64 처리)은 실코드가 돌고, 합성만 고정 이미지로 대체).
//
// 핵심 확인: 버튼 클릭 전엔 자동 호출 없음(비용 절약), 클릭 시 합성 이미지
// 표시, 뒤로가기 재진입 시 재요청 없음(App 캐시)

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

  let synthCalls = 0;
  page.on('request', (req) => {
    if (req.url().includes('/api/synthesize') && req.method() === 'POST') {
      synthCalls += 1;
    }
  });

  // 측정 → 의류 → 핏 결과 화면까지 주행 (e2e-fit.mjs와 동일 경로)
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
  await page.click('.clothing-spec .result__actions .result__btn--primary');
  await page.waitForSelector('.fit .result__table', { timeout: 15000 });

  // 가상 착용 섹션 — 버튼 클릭 전에는 자동 호출 없음
  const synthSection = await page.$('.fit__synth');
  check('"가상 착용 보기" 섹션 표시', synthSection !== null);
  await new Promise((r) => setTimeout(r, 500));
  check(`버튼 클릭 전 /synthesize 자동 호출 없음 (${synthCalls}회)`, synthCalls === 0);

  const synthBtn = await page.$('.fit__synth .result__btn--primary');
  check('"가상 착용 이미지 생성" 버튼 표시', synthBtn !== null);
  await page.click('.fit__synth .result__btn--primary');
  // fake 백엔드가 landmarks를 채워 반환하므로(5-3b) <img> 대신 히트맵 <canvas> 렌더
  await page.waitForSelector('.fit__heatmap', { timeout: 15000 });
  const baseline = synthCalls;
  check(`합성 요청 (/synthesize ${baseline}회 — StrictMode 이중 실행 포함)`,
    baseline >= 1 && baseline <= 2);

  // 가짜 합성 이미지는 270×360 단색 회색(128,128,128) — 원본(1080×1440)과
  // 종횡비 동일(0.75), 스케일 0.25. FAKE_LANDMARKS의 chest는 x:390~610,y:400
  // → 캔버스 좌표로 x:97.5~152.5,y:100 (중심 125,100). 배경(코너, 10,10)과
  // 밴드 중심 픽셀 색을 비교해 5-3d 스케일링·배치 로직이 실제로 그렸는지 확인.
  const [canvasW, canvasH, bg, chestPixel] = await page.$eval('.fit__heatmap', (el) => {
    const ctx = el.getContext('2d');
    const bgPixel = ctx.getImageData(10, 10, 1, 1).data;
    const chest = ctx.getImageData(125, 100, 1, 1).data;
    return [el.width, el.height, Array.from(bgPixel), Array.from(chest)];
  });
  check(`히트맵 캔버스가 합성 이미지 크기로 그려짐 (${canvasW}x${canvasH})`,
    canvasW === 270 && canvasH === 360);
  check(`배경(코너)은 원본 단색 유지 (${bg.slice(0, 3)})`,
    bg[0] > 100 && bg[0] < 150 && bg[1] > 100 && bg[1] < 150);
  check(`가슴 밴드 중심 픽셀이 배경과 다름 = 실제 위치에 그려짐 (${chestPixel.slice(0, 3)} vs 배경 ${bg.slice(0, 3)})`,
    Math.abs(chestPixel[0] - bg[0]) + Math.abs(chestPixel[1] - bg[1]) + Math.abs(chestPixel[2] - bg[2]) > 20);
  const note = await page.$eval('.fit__synth .result__note', (el) => el.textContent);
  check('부위 밴드는 대략 위치·수치가 진짜 정보라는 안내 표시 (그림≠실핏 오해 차단)',
    note.includes('cm 수치'));

  // 뒤로(의류 정보) → 재진입 → App 캐시로 재요청 없음, 히트맵도 즉시 복원
  await page.click('.fit .result__actions .result__btn'); // 의류 정보로
  await page.waitForSelector('.clothing-spec .spec__table', { timeout: 5000 });
  await page.click('.clothing-spec .result__actions .result__btn--primary');
  await page.waitForSelector('.fit__heatmap', { timeout: 5000 });
  await new Promise((r) => setTimeout(r, 500));
  check(`재진입 — 재요청 없음 (/synthesize 총 ${synthCalls}회)`, synthCalls === baseline);
} catch (e) {
  console.error('FAIL  예외 발생:', e.message);
  failures += 1;
} finally {
  backend.kill();
  await browser.close();
}

console.log(failures === 0 ? '\n전체 통과' : `\n실패 ${failures}건`);
process.exit(failures === 0 ? 0 : 1);
