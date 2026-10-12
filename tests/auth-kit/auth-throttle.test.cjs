'use strict';
// 이용권 확인 줄이기(auth-throttle) 시험. 가짜 인증 서비스는 실제 비용을 흉내 낸다:
// sync/init = PowerShell 4번(읽기·읽기·쓰기·다시 읽기), peek = 1번, authorize = 1번, 사용자 동작 = 4번
const test = require('node:test'), assert = require('node:assert/strict');
const { createAuthThrottle } = require('../../assets/auth/auth-throttle.cjs');

function fakeAuth() {
  const f = { ps: 0, calls: [], summary: () => ({ ready: true, canEdit: true, n: f.ps }) };
  f.act = async a => { f.calls.push(a); f.ps += a === 'peek' ? 1 : 4; await new Promise(r => setTimeout(r, 1)); return { ok: true, state: f.summary() }; };
  f.authorize = async () => { f.calls.push('authorize'); f.ps += 1; return true; };
  return f;
}

test('시작: 한 번만 읽고 바로 응답, 전체 확인은 2분 뒤 손을 뗐을 때 하고 결과를 화면에 보냄 (1.0.2)', async () => {
  const a = fakeAuth(), sent = [], jobs = []; let t = 0, idle = false;
  const th = createAuthThrottle(a, { now: () => t, onState: s => sent.push(s), defer: () => assert.fail('바로 하면 안 됨'), schedule: (fn, ms) => jobs.push([fn, ms]), isIdle: () => idle });
  const r = await th.act('init');
  assert.equal(r.ok, true);
  assert.deepEqual(a.calls, ['peek']);
  assert.equal(a.ps, 1, '시작 때 PowerShell 1번뿐');
  assert.equal(jobs.length, 1); assert.equal(jobs[0][1], 120000, '2분 뒤로 예약');
  t = 120000; jobs.shift()[0]();
  assert.deepEqual(a.calls, ['peek'], '작업 중이면 미룸');
  assert.equal(jobs[0][1], 15000, '15초 뒤 다시 확인');
  idle = true; t = 135000; jobs.shift()[0](); await new Promise(r => setTimeout(r, 10));
  assert.deepEqual(a.calls, ['peek', 'sync']);
  assert.equal(sent.length, 1, '확인 결과를 화면에 보냄');
});

test('지금 편집할 수 없는 상태(등록 PC, 갱신 필요)면 시작 직후 바로 전체 확인', async () => {
  const a = fakeAuth(); let deferred = null;
  a.act = async x => { a.calls.push(x); return { ok: true, state: { ready: true, registered: true, canEdit: false } }; };
  const th = createAuthThrottle(a, { now: () => 0, defer: fn => { deferred = fn; }, schedule: () => assert.fail('미루면 안 됨') });
  await th.act('init');
  assert.ok(deferred, '바로 확인 예약'); deferred(); await new Promise(r => setTimeout(r, 5));
  assert.deepEqual(a.calls, ['peek', 'sync']);
});

test('10분마다의 자동 확인도 작업 중이면 미루고, 30분 넘게 밀리면 그때는 함', async () => {
  const a = fakeAuth(); let t = 0, idle = false;
  const th = createAuthThrottle(a, { now: () => t, defer: () => {}, schedule: () => {}, isIdle: () => idle });
  await th.act('init'); a.calls.length = 0;
  t = 11 * 60e3; const r = await th.act('sync');
  assert.equal(r.cached, true); assert.deepEqual(a.calls, []);
  t = 31 * 60e3; await th.act('sync');
  assert.deepEqual(a.calls, ['sync'], '너무 오래 밀리면 실행');
});

test('자동 확인은 10분에 한 번만 실제 수행, 그 사이는 마지막 결과', async () => {
  const a = fakeAuth(); let t = 0;
  const th = createAuthThrottle(a, { now: () => t, defer: () => {} });
  await th.act('init'); a.calls.length = 0;
  for (let i = 1; i <= 9; i++) { t = i * 60e3; const r = await th.act('sync'); assert.equal(r.cached, true); }
  assert.deepEqual(a.calls, []);
  t = 10 * 60e3; await th.act('sync');
  assert.deepEqual(a.calls, ['sync']);
});

test('동시에 여러 번 요청해도 실제 확인은 한 번(진행 중 결과 공유)', async () => {
  const a = fakeAuth(); let t = 0;
  const th = createAuthThrottle(a, { now: () => t, defer: () => {} });
  await th.act('init'); t = 11 * 60e3; a.calls.length = 0;
  await Promise.all([th.act('sync'), th.act('sync'), th.act('init'), th.act('sync')]);
  assert.deepEqual(a.calls, ['sync']);
});

test('사용자가 직접 누른 동작은 바로 수행하고 자동 확인 시계를 새로 맞춤', async () => {
  const a = fakeAuth(); let t = 0;
  const th = createAuthThrottle(a, { now: () => t, defer: () => {} });
  await th.act('init'); a.calls.length = 0;
  t = 3 * 60e3; await th.act('refresh', {}); await th.act('login', { email: 'x', code: '1' });
  assert.deepEqual(a.calls, ['refresh', 'login']);
  t = 12 * 60e3; await th.act('sync');
  assert.deepEqual(a.calls, ['refresh', 'login'], '방금 확인했으므로 다시 하지 않음');
});

test('저장·내보내기 권한 확인은 60초 동안 재사용(이미지 30쪽 내보내기 = 1번)', async () => {
  const a = fakeAuth(); let t = 0;
  const th = createAuthThrottle(a, { now: () => t, defer: () => {} });
  for (let i = 0; i < 32; i++) { t = i * 500; await th.authorize(); }
  assert.equal(a.calls.filter(c => c === 'authorize').length, 1);
  t = 70e3; await th.authorize();
  assert.equal(a.calls.filter(c => c === 'authorize').length, 2);
});

test('권한 확인이 실패하면 기억하지 않음(다음에 다시 확인)', async () => {
  const a = fakeAuth(); let fail = true;
  a.authorize = async () => { a.calls.push('authorize'); if (fail) throw Error('이용권 확인이 필요합니다'); return true; };
  const th = createAuthThrottle(a, { now: () => 0, defer: () => {} });
  await assert.rejects(th.authorize());
  fail = false; await th.authorize();
  assert.equal(a.calls.length, 2);
});

test('실사용 1시간 비교: PowerShell 실행 횟수', async () => {
  // 2.5.1: 본체 1분 + 화면 1분 타이머, 창 활성화 20번, 이미지 30쪽 내보내기 2번, 저장 3번
  const scenario = async (act, authorize, setT) => {
    await act('init');
    for (let m = 1; m <= 60; m++) { setT(m * 60e3); await act('sync'); await act('sync'); if (m % 3 === 0) await act('sync'); }
    for (let k = 0; k < 2; k++) for (let i = 0; i < 32; i++) { setT(20 * 60e3 + k * 600e3 + i * 300); await authorize(); }
    for (let k = 0; k < 3; k++) { setT((10 + k * 15) * 60e3); await authorize(); }
  };
  const before = fakeAuth(); let t = 0;
  await scenario(a => before.act(a === 'init' ? 'sync' : a), () => before.authorize(), v => { t = v; });
  const after = fakeAuth(); let t2 = 0;
  const th = createAuthThrottle(after, { now: () => t2, defer: fn => fn(), schedule: () => {} });
  await scenario(a => th.act(a), () => th.authorize(), v => { t2 = v; });
  await new Promise(r => setTimeout(r, 20));
  console.log(`  1시간 PowerShell 실행: 2.5.1 ${before.ps}번 → 2.5.2 ${after.ps}번`);
  assert.ok(after.ps * 10 < before.ps, `10분의 1 이하로 줄어야 함 (${before.ps} → ${after.ps})`);
});

// ── 1.0.1: 시작 표시(기억해 둔 상태 + 미리 읽기) ──
function memCache(initial) { let v = initial || null; return { read: () => v, write: x => { v = x; }, get value() { return v; } }; }
function slowAuth(real) {
  const f = fakeAuth(); let release;
  const gate = new Promise(r => { release = r; });
  f.summary = () => real;
  f.act = async a => { f.calls.push(a); f.ps += a === 'peek' ? 1 : 4; if (a === 'peek') await gate; return { ok: true, state: real }; };
  f.release = release; return f;
}
const REAL = { ready: true, canEdit: true, verdict: 'OK', plan: 'edu_free', hasLicense: true, accountPresent: true, loggedIn: true, registered: true, expiresAt: null, edu: { status: 'active' }, email: 'teacher@senedu.kr', diagnostics: [{ x: 1 }] };

test('기억해 둔 상태가 있으면 첫 읽기를 기다리지 않고 바로 보여 주고, 실제 결과가 오면 화면에 보냄', async () => {
  const c = memCache({ savedAt: 1000, verdict: 'OK', canEdit: true, plan: 'edu_free', hasLicense: true, accountPresent: true });
  const a = slowAuth(REAL), sent = []; let t = 2000;
  const th = createAuthThrottle(a, { now: () => t, cache: c, onState: s => sent.push(s), defer: fn => fn() });
  const r = await th.act('init');
  assert.equal(r.provisional, true);
  assert.equal(r.state.canEdit, true);
  assert.equal(r.state.plan, 'edu_free');
  assert.equal(r.state.ready, true);
  assert.equal(sent.length, 0, '아직 실제 결과 전');
  a.release(); await new Promise(r => setTimeout(r, 10));
  assert.ok(sent.length >= 1, '실제 결과를 화면에 보냄');
  assert.equal(sent[0].verdict, 'OK');
});

test('실제 확인 결과를 기억하되 이메일·진단 정보는 저장하지 않음', async () => {
  const c = memCache(); const a = slowAuth(REAL); a.release();
  const th = createAuthThrottle(a, { now: () => 5000, cache: c, defer: () => {} });
  await th.act('init');
  assert.equal(c.value.plan, 'edu_free');
  assert.equal(c.value.canEdit, true);
  assert.equal(c.value.email, undefined);
  assert.equal(c.value.diagnostics, undefined);
  assert.equal(c.value.savedAt, 5000);
});

test('기한이 지난 기억값은 편집 가능으로 보여 주지 않고, 30일 넘은 기억값은 쓰지 않음', async () => {
  const day = 86400e3;
  const expired = memCache({ savedAt: 10 * day, verdict: 'OK', canEdit: true, plan: 'licensed', expiresAt: 11 * 86400 });
  const a1 = slowAuth(REAL);
  const r1 = await createAuthThrottle(a1, { now: () => 12 * day, cache: expired, defer: () => {} }).act('init');
  assert.equal(r1.state.canEdit, false);
  const old = memCache({ savedAt: 0, verdict: 'OK', canEdit: true, plan: 'edu_free' });
  const a2 = slowAuth(REAL); let done = false;
  const p = createAuthThrottle(a2, { now: () => 31 * day, cache: old, defer: () => {} }).act('init').then(r => { done = true; return r; });
  await new Promise(r => setTimeout(r, 10));
  assert.equal(done, false, '오래된 기억값 대신 실제 읽기를 기다림');
  a2.release(); const r2 = await p; assert.equal(r2.provisional, undefined);
});

test('미리 읽기(prewarm): 창이 뜨기 전에 시작하고, 화면이 물을 때는 다시 읽지 않음', async () => {
  const a = slowAuth(REAL); a.release();
  const th = createAuthThrottle(a, { now: () => 0, cache: memCache(), defer: () => {} });
  th.prewarm(); await new Promise(r => setTimeout(r, 5));
  assert.deepEqual(a.calls, ['peek']);
  const r = await th.act('init');
  assert.deepEqual(a.calls, ['peek'], '이미 읽었으므로 추가 PowerShell 없음');
  assert.equal(r.state.verdict, 'OK');
});
