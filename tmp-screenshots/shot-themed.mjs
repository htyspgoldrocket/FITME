// UX-2 그레이지 육안 확인용 — 테마 적용 화면 5종 스크린샷 (가짜 백엔드 주행)
// 사전 조건: npm run dev (5173), 8000 비어 있음. e2e-fit.mjs 주행 코드 재사용.
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const ROOT = 'C:\\claude_code\\FITME';
const OUT_DIR = join(dirname(fileURLToPath(import.meta.url)), 'shots');
const Y4M = join(ROOT, 'tests', 'fake-marker.y4m');
const PYTHON = join(ROOT, 'server', 'venv', 'Scripts', 'python.exe');
const MUSINSA_URL = 'https://www.musinsa.com/products/1234567';

if (!existsSync(Y4M)) {
  console.error('fake-marker.y4m 없음');
  process.exit(1);
}
mkdirSync(OUT_DIR, { recursive: true });

const backend = spawn(
  PYTHON,
  ['-m', 'uvicorn', 'tests.e2e_fake_backend:app', '--port', '8000'],
  { cwd: ROOT, stdio: 'ignore' },
);
for (let i = 0; i < 40; i += 1) {
  try {
    await fetch('http://127.0.0.1:8000/health');
    break;
  } catch {
    await new Promise((r) => setTimeout(r, 500));
  }
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

try {
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844 });
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle2', timeout: 20000 });
  await page.screenshot({ path: join(OUT_DIR, '01-mode-select.png') });

  await page.click('.mode-card--precise');
  await page.waitForSelector('.profile input');
  await page.type('.profile__field:nth-of-type(1) input', '172');
  await page.screenshot({ path: join(OUT_DIR, '02-profile.png') });

  await page.click('.profile__btn--primary');
  await page.waitForSelector('.camera-guide', { timeout: 10000 });
  await page.click('.camera-guide__confirm');
  await page.waitForSelector('.preview', { timeout: 30000 });
  await page.click('.preview__btn--primary');
  await page.waitForSelector('.result__table', { timeout: 30000 });
  await page.screenshot({ path: join(OUT_DIR, '03-result.png') });

  await page.click('.result__actions .result__btn--primary');
  await page.waitForSelector('.clothing input', { timeout: 5000 });
  await page.type('.clothing input', MUSINSA_URL);
  await page.screenshot({ path: join(OUT_DIR, '04-clothing-url.png') });

  await page.click('.clothing .profile__btn--primary');
  await page.waitForSelector('.clothing-spec .spec__table', { timeout: 15000 });
  await page.screenshot({ path: join(OUT_DIR, '05-clothing-spec.png') });

  const fitBtn = await page.$('.clothing-spec .result__actions .result__btn--primary');
  await fitBtn.click();
  await page.waitForSelector('.fit__recommend', { timeout: 15000 });
  await page.screenshot({ path: join(OUT_DIR, '06-fit.png') });

  console.log('saved 6 shots to', OUT_DIR);
} finally {
  await browser.close();
  backend.kill();
}
