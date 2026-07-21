// 카메라 화면 스크린샷 도구 — 촬영 가이드 UI(카드 박스·거리 자 등) 육안 확인용
// (5-4 백로그 B-1/B-2 검증에서 사용, 13-4 검증 자산으로 보존)
//
// 사용: node tests/screenshot-camera.mjs <출력경로.png> [키cm=172] [모드=simple|precise]
// 사전 조건: npm run dev (5173). 백엔드는 불필요(판정 배너는 서버 다운 표시 — 정상)
import puppeteer from 'puppeteer-core';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const OUT = process.argv[2] ?? 'camera-screenshot.png';
const HEIGHT = process.argv[3] ?? '172';
const MODE = process.argv[4] === 'precise' ? 'precise' : 'simple';

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: [
    '--use-fake-device-for-media-stream',
    '--use-fake-ui-for-media-stream',
    '--no-sandbox',
  ],
});
const page = await browser.newPage();
await page.setViewport({ width: 390, height: 844 }); // 모바일 비율
await page.goto('http://localhost:5173', { waitUntil: 'networkidle2' });
await page.click(`.mode-card--${MODE}`);
await page.waitForSelector('.profile');
await page.type('.profile__field:nth-of-type(1) input', HEIGHT);
await page.click('.profile__btn--primary');
await page.waitForSelector('.camera');
// 층위 1 안내가 떠 있으면 닫는다 (세션 첫 진입)
const confirm = await page.$('.camera-guide__confirm');
if (confirm) await confirm.click();
await new Promise((r) => setTimeout(r, 800)); // 오버레이 렌더 안정화
await page.screenshot({ path: OUT });
await browser.close();
console.log('saved:', OUT, 'height:', HEIGHT, 'mode:', MODE);
