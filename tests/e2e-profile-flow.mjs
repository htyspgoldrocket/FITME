// 2-8b/2-8c E2E 스모크 — 모드 선택 → 신체 정보 입력 → 카메라(층위 1 안내
// 오버레이) → 뒤로가기(입력 유지) → 재진입(안내 생략 + ❓ 재열람)
//
// 실행: node tests/e2e-profile-flow.mjs  (사전에 npm run dev가 5173에서 떠 있어야 함)
// Chrome 가짜 카메라 방식 (Phase 1 검증 스크립트와 동일 — CLAUDE.md 13-4 누적 자산)

import puppeteer from 'puppeteer-core';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const URL = 'http://localhost:5173';

let failures = 0;
function check(name, cond) {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}`);
  if (!cond) failures += 1;
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: [
    '--use-fake-device-for-media-stream',
    '--use-fake-ui-for-media-stream',
    '--no-sandbox',
  ],
});

try {
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844 }); // 모바일 비율
  await page.goto(URL, { waitUntil: 'networkidle2', timeout: 20000 });

  // 1) 모드 선택 → 프로필 화면 진입
  await page.waitForSelector('.mode-card--simple', { timeout: 10000 });
  await page.click('.mode-card--simple');
  await page.waitForSelector('.profile', { timeout: 5000 });
  check('모드 선택 후 신체 정보 입력 화면 진입', true);

  const nextBtn = '.profile__btn--primary';
  const heightInput = '.profile__field:nth-of-type(1) input';
  const weightInput = '.profile__field:nth-of-type(2) input';

  // 2) 키 미입력 → 다음 비활성
  check('키 미입력 시 다음 버튼 비활성', await page.$eval(nextBtn, (b) => b.disabled));

  // 3) 범위 밖 키(999) → 에러 힌트 + 비활성
  await page.type(heightInput, '999');
  const hasError = await page
    .waitForSelector('.profile__hint--error', { timeout: 3000 })
    .then(() => true, () => false);
  check('범위 밖 키 입력 시 에러 힌트 표시', hasError);
  check('범위 밖 키 입력 시 다음 버튼 비활성', await page.$eval(nextBtn, (b) => b.disabled));

  // 4) 유효 입력 → 활성 → 카메라 진입
  await page.$eval(heightInput, (el) => (el.value = ''));
  await page.type(heightInput, '172');
  await page.type(weightInput, '68');
  check('유효 입력 시 다음 버튼 활성', await page.$eval(nextBtn, (b) => !b.disabled));
  await page.click(nextBtn);
  await page.waitForSelector('.camera', { timeout: 10000 });
  check('다음 → 카메라 화면 진입', true);

  // 5) 층위 1 — 첫 카메라 진입 시 정적 안내 오버레이 자동 표시 (2-8c)
  await page.waitForSelector('.camera-guide', { timeout: 5000 });
  const itemCount = await page.$$eval('.camera-guide__list li', (l) => l.length);
  check(`안내 오버레이 자동 표시 + 항목 5개 (실제 ${itemCount})`, itemCount === 5);
  await page.click('.camera-guide__confirm');
  const guideGone = (await page.$('.camera-guide')) === null;
  check('확인했어요 → 안내 오버레이 닫힘', guideGone);

  // 6) 층위 2 — 실루엣 가이드 표시
  check('실루엣 가이드 표시', (await page.$('.camera__silhouette')) !== null);

  // 6a) 5-4 백로그 ④ — 거리 자: 머리·발 기준선 2개 + 2m 안내 라벨 (SVG 내부)
  const rulerCount = (await page.$$('.camera__ruler-line')).length;
  check(`거리 자 기준선 2개 표시 (실제 ${rulerCount})`, rulerCount === 2);
  const rulerLabels = await page.$$eval('.camera__ruler-text', (els) =>
    els.map((el) => el.textContent.trim()).join(' / '),
  );
  check(`거리 자 라벨에 2m 안내 (${rulerLabels})`, rulerLabels.includes('약 2m'));

  // 6b) 5-4 백로그 ⑤ — 간편 모드: 가로 카드 박스 + 방향·대비 안내 문구
  check('간편 모드 카드 박스 표시', (await page.$('.camera__card-box')) !== null);
  const refText = await page.$eval('.camera__ref-guide', (el) => el.textContent);
  check(
    `카드 안내 문구에 방향·대비 조건 포함 (${refText})`,
    refText.includes('가로') && refText.includes('어두운'),
  );

  // 7) 카메라 뒤로 → 프로필 화면, 입력값 유지 (App 보관 원칙)
  await page.waitForSelector('.camera__back', { timeout: 5000 });
  await page.click('.camera__back');
  await page.waitForSelector('.profile', { timeout: 5000 });
  const kept = await page.$eval(heightInput, (el) => el.value);
  const keptW = await page.$eval(weightInput, (el) => el.value);
  check(`뒤로가기 후 키 입력값 유지 (${kept})`, kept === '172');
  check(`뒤로가기 후 몸무게 입력값 유지 (${keptW})`, keptW === '68');

  // 8) 카메라 재진입 — 안내는 다시 자동 표시되지 않음 (guideSeen, App 보관)
  await page.click(nextBtn);
  await page.waitForSelector('.camera', { timeout: 10000 });
  check('재진입 시 안내 자동 표시 안 함', (await page.$('.camera-guide')) === null);

  // 9) ❓ 버튼으로 안내 재열람 가능
  await page.click('.camera__help');
  await page.waitForSelector('.camera-guide', { timeout: 3000 });
  check('❓ 버튼으로 안내 재열람', true);
  await page.click('.camera-guide__confirm');

  // 9b) 5-4 백로그 ④ 보완 — 실루엣·거리 자 키 비례 스케일 (발 기준 고정).
  // 고정 실루엣은 작은 키를 근거리로 유도(마커 밴드와 충돌)하므로 키에 비례
  const rect172 = await page.$eval('.camera__silhouette', (el) => {
    const r = el.getBoundingClientRect();
    return { height: r.height, bottom: r.bottom };
  });
  await page.click('.camera__back');
  await page.waitForSelector('.profile', { timeout: 5000 });
  await page.$eval(heightInput, (el) => (el.value = ''));
  await page.type(heightInput, '150');
  await page.click(nextBtn);
  await page.waitForSelector('.camera', { timeout: 10000 });
  const rect150 = await page.$eval('.camera__silhouette', (el) => {
    const r = el.getBoundingClientRect();
    return { height: r.height, bottom: r.bottom };
  });
  const ratio = rect150.height / rect172.height;
  check(
    `키 150 실루엣이 172보다 비례 축소 (비율 ${ratio.toFixed(3)}, 기대 ${(150 / 172).toFixed(3)})`,
    Math.abs(ratio - 150 / 172) < 0.01,
  );
  check(
    `발 위치는 키와 무관하게 고정 (bottom 차 ${Math.abs(rect150.bottom - rect172.bottom).toFixed(1)}px)`,
    Math.abs(rect150.bottom - rect172.bottom) < 1,
  );

  // 10) 프로필에서 뒤로 → 모드 선택
  await page.click('.camera__back');
  await page.waitForSelector('.profile', { timeout: 5000 });
  await page.click('.profile__btn:not(.profile__btn--primary)');
  await page.waitForSelector('.mode-select', { timeout: 5000 });
  check('프로필 뒤로 → 모드 선택 화면', true);

  // 11) 5-4 백로그 ⑤ — 정밀 모드: 카드 박스 없음 + 마커 안내 유지
  await page.click('.mode-card--precise');
  await page.waitForSelector('.profile', { timeout: 5000 });
  await page.click(nextBtn);
  await page.waitForSelector('.camera', { timeout: 10000 });
  check('정밀 모드 카드 박스 없음', (await page.$('.camera__card-box')) === null);
  const refTextPrecise = await page.$eval('.camera__ref-guide', (el) => el.textContent);
  check(`정밀 모드 마커 안내 유지 (${refTextPrecise})`, refTextPrecise.includes('마커'));
} catch (e) {
  console.error('FAIL  예외 발생:', e.message);
  failures += 1;
} finally {
  await browser.close();
}

console.log(failures === 0 ? '\n전체 통과' : `\n실패 ${failures}건`);
process.exit(failures === 0 ? 0 : 1);
