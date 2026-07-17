// 2-8d E2E — 층위 3 실시간 검증 + 자동 촬영 (서버 폴링)
//
// 사전 조건:
//   1) 백엔드: server/venv 로 uvicorn main:app --port 8000
//   2) 프론트: npm run dev (5173, /api 프록시)
//   3) tests/fake-marker.y4m 생성: server\venv\Scripts\python.exe tests\gen_fake_camera.py
// 실행: node tests/e2e-autoshoot.mjs
//
// 케이스 A(음성): 기본 가짜 카메라(초록 패턴) → 마커 미검출 사유 배너, 자동 촬영 없음
// 케이스 B(양성): 마커 y4m → ready 배너 → 자동 카운트다운 → 셔터 탭 없이 미리보기 진입

import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const URL = 'http://localhost:5173';
const Y4M = join(dirname(fileURLToPath(import.meta.url)), 'fake-marker.y4m');

let failures = 0;
function check(name, cond) {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}`);
  if (!cond) failures += 1;
}

async function launch(extraArgs = []) {
  return puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: [
      '--use-fake-device-for-media-stream',
      '--use-fake-ui-for-media-stream',
      '--no-sandbox',
      ...extraArgs,
    ],
  });
}

/** 공통 주행: 정밀 모드 → 키 입력 → 카메라 진입 → 안내 닫기 */
async function driveToCamera(page) {
  await page.setViewport({ width: 390, height: 844 });
  await page.goto(URL, { waitUntil: 'networkidle2', timeout: 20000 });
  await page.click('.mode-card--precise');
  await page.waitForSelector('.profile input');
  await page.type('.profile__field:nth-of-type(1) input', '172');
  await page.click('.profile__btn--primary');
  await page.waitForSelector('.camera-guide', { timeout: 10000 });
  await page.click('.camera-guide__confirm');
}

// ---------- 케이스 A: 마커 없음 (기본 초록 패턴) ----------
{
  const browser = await launch();
  try {
    const page = await browser.newPage();
    await driveToCamera(page);

    await page.waitForSelector('.camera__banner--warn', { timeout: 15000 });
    const text = await page.$eval('.camera__banner--warn', (el) => el.textContent);
    check(`미검출 사유 배너 표시 ("${text.slice(0, 20)}…")`, text.includes('마커'));

    // 8초 더 관찰 — 자동 카운트다운·촬영이 일어나면 안 됨
    await new Promise((r) => setTimeout(r, 8000));
    check('마커 없으면 자동 촬영 안 함 (카메라 화면 유지)', (await page.$('.camera')) !== null);
    check('카운트다운 미표시', (await page.$('.camera__countdown')) === null);

    // 토글 OFF → 배너 사라짐 + ON 복귀
    await page.click('.camera__auto');
    check('자동 촬영 OFF 시 배너 숨김', (await page.$('.camera__banner')) === null);
    await page.click('.camera__auto');
    await page.waitForSelector('.camera__banner', { timeout: 10000 });
    check('자동 촬영 ON 복귀 시 배너 재개', true);
  } catch (e) {
    console.error('FAIL  케이스 A 예외:', e.message);
    failures += 1;
  } finally {
    await browser.close();
  }
}

// ---------- 케이스 B: 마커 보임 (y4m) → 자동 촬영 ----------
{
  if (!existsSync(Y4M)) {
    console.error(`FAIL  ${Y4M} 없음 — tests/gen_fake_camera.py 먼저 실행`);
    failures += 1;
  } else {
    const browser = await launch([`--use-file-for-fake-video-capture=${Y4M}`]);
    try {
      const page = await browser.newPage();
      await driveToCamera(page);

      await page.waitForSelector('.camera__banner--ok', { timeout: 15000 });
      check('조건 충족 배너(ready) 표시', true);

      // 셔터를 탭하지 않고 자동으로 미리보기까지 진입해야 함
      await page.waitForSelector('.preview', { timeout: 20000 });
      check('자동 카운트다운 → 셔터 탭 없이 미리보기 진입', true);
    } catch (e) {
      console.error('FAIL  케이스 B 예외:', e.message);
      failures += 1;
    } finally {
      await browser.close();
    }
  }
}

console.log(failures === 0 ? '\n전체 통과' : `\n실패 ${failures}건`);
process.exit(failures === 0 ? 0 : 1);
