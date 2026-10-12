'use strict';
// 이용권 확인 줄이기·빠르게 (2.5.2~, 1.0.1 시작 표시 개선)
// 공통 인증 저장소 읽기·쓰기는 매번 PowerShell을 새로 띄우고(DPAPI·쎈 시리즈 공통 잠금), 학교 PC 보안 프로그램이 그때마다 검사해
// CPU를 크게 쓴다.
// - 자동 확인(sync/init)은 10분에 한 번만 실제로 수행하고, 그 사이 요청은 마지막 결과를 돌려준다. 진행 중이면 그 결과를 함께 기다린다.
// - 시작: 프로그램이 켜지자마자(창이 뜨기 전) 저장소를 한 번 읽기(peek) 시작하고, 나머지 확인(시계 기록·이용권 갱신)은 뒤에서 이어서 한다.
// - 1.0.1: 마지막으로 확인한 이용권 상태(요금제·기한 등 표시용, 이메일 제외)를 기억해 두고, 시작 화면에 바로 보여 준 뒤 실제 확인 결과로 바꾼다.
//   (쎈Cut처럼 켜자마자 '센스쿨 계정'이 보이게. 저장·내보내기는 authorize가 매번 실제 저장소로 확인하므로 기억값으로는 열리지 않음)
// - 1.0.2: 시작 직후 전체 확인(PowerShell 3번)이 켤 때의 버벅임(약 10초) 원인 → 시작 2분 뒤, 사용자가 잠시 손을 뗐을 때(입력 없음 10초) 하고,
//   10분마다의 자동 확인도 작업 중이면 미룬다(최대 30분). 단, 지금 편집할 수 없는 상태(갱신 필요)면 바로 확인한다.
// - 저장·내보내기 권한 확인(authorize)은 성공 후 60초 동안 다시 묻지 않는다.
// - 사용자가 직접 누른 동작(로그인·이용권 다시 확인·등록 등)은 바로 수행하고, 자동 확인 시계를 새로 맞춘다.
const SYNC_EVERY = 10 * 60 * 1000;
const AUTHORIZE_TTL = 60 * 1000;
const CACHE_MAX_AGE = 30 * 24 * 60 * 60 * 1000;
const STARTUP_SYNC_DELAY = 2 * 60 * 1000;
const IDLE_RETRY = 15 * 1000;
const MAX_POSTPONE = 30 * 60 * 1000;
const CACHE_FIELDS = ['verdict', 'canEdit', 'hasLicense', 'accountPresent', 'loggedIn', 'registered', 'plan', 'expiresAt', 'unlimited', 'edu'];

function fileCache(file) {
  const fs = require('fs'), path = require('path');
  return {
    read() { try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return null; } },
    write(v) { try { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file + '.tmp', JSON.stringify(v)); fs.renameSync(file + '.tmp', file); } catch {} }
  };
}

function createAuthThrottle(auth, { now = Date.now, syncEvery = SYNC_EVERY, authorizeTtl = AUTHORIZE_TTL, onState = () => {}, defer = fn => setTimeout(fn, 0), cache = null, isIdle = () => true, schedule = (fn, ms) => { const t = setTimeout(fn, ms); t.unref?.(); return t; }, startupDelay = STARTUP_SYNC_DELAY } = {}) {
  let lastSync = 0, inflight = null, lastAuthorize = -Infinity, firstPeek = null, peekDone = false, pushWhenDone = false;
  const cached = () => ({ ok: true, already: false, state: auth.summary(), syncError: null, cached: true });
  function remember(state) {
    if (!cache || !state || !state.ready) return;
    const keep = { savedAt: now() };
    for (const k of CACHE_FIELDS) if (state[k] !== undefined) keep[k] = state[k];
    cache.write(keep);
  }
  function recalled() {
    const c = cache && cache.read();
    if (!c || typeof c.savedAt !== 'number' || now() - c.savedAt > CACHE_MAX_AGE || now() < c.savedAt - 60000) return null;
    const state = { ...c, ready: true, provisional: true, email: '', diagnostics: [], lastFailure: null, activeError: null, message: '' };
    delete state.savedAt;
    // 기한이 지난 기억값은 편집 가능으로 보여 주지 않음
    if (state.expiresAt && state.expiresAt * 1000 < now()) { state.canEdit = false; state.verdict = 'ENT_EXPIRED'; }
    return state;
  }
  function fullSync() {
    inflight = Promise.resolve(auth.act('sync')).then(r => { if (r && r.ok) remember(r.state); return r; }).finally(() => { lastSync = now(); inflight = null; });
    return inflight;
  }
  function startPeek() {
    if (firstPeek) return firstPeek;
    firstPeek = Promise.resolve(auth.act('peek')).then(r => {
      peekDone = true; lastSync = now();
      if (r && r.ok) remember(r.state);
      if (pushWhenDone && r) onState(r.state);
      const st = r && r.state;
      if (st && st.registered && !st.canEdit) defer(backgroundSync); // 갱신이 필요하면 바로
      else schedule(idleSync, startupDelay);                          // 아니면 2분 뒤, 손을 뗐을 때
      return r;
    }, e => { peekDone = true; throw e; });
    return firstPeek;
  }
  function backgroundSync() { if (inflight) return; fullSync().then(r2 => onState(r2.state)).catch(() => {}); }
  function idleSync() {
    if (inflight || now() - lastSync < startupDelay / 2) return;
    if (isIdle() || now() - lastSync > MAX_POSTPONE) backgroundSync(); else schedule(idleSync, IDLE_RETRY);
  }
  async function act(action, args) {
    if (action === 'init' || action === 'sync') {
      startPeek();
      if (!peekDone) {
        // 첫 읽기가 아직이면: 기억해 둔 상태를 바로 보여 주고, 실제 결과는 끝나는 대로 화면에 보냄
        const r = recalled();
        if (r) { pushWhenDone = true; return { ok: true, already: false, state: r, syncError: null, cached: true, provisional: true }; }
        return firstPeek;
      }
      if (inflight) return inflight;
      if (now() - lastSync < syncEvery) return cached();
      if (!isIdle() && now() - lastSync < MAX_POSTPONE) return cached(); // 작업 중이면 다음 기회에
      return fullSync();
    }
    const r = await auth.act(action, args);
    lastSync = now(); lastAuthorize = -Infinity;
    if (r && r.ok) remember(r.state);
    return r;
  }
  async function authorize() {
    if (now() - lastAuthorize < authorizeTtl) return true;
    await auth.authorize();
    lastAuthorize = now();
    return true;
  }
  return { act, authorize, summary: () => auth.summary(), prewarm: () => { startPeek().catch(() => {}); } };
}

module.exports = { createAuthThrottle, fileCache, SYNC_EVERY, AUTHORIZE_TTL, CACHE_MAX_AGE, STARTUP_SYNC_DELAY, MAX_POSTPONE };
