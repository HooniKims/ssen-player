'use strict';
// ssen-auth-kit: 앱 이름이 서버 요청(/devices/register·/license/token)에 "ssen-<앱>"으로 들어가는지, 잘못된 이름은 거부하는지
const test = require('node:test'), assert = require('node:assert/strict');
const { createAuthService } = require('../../assets/auth/auth-service.cjs');
const APP = process.env.SSEN_APP_ID || 'clean';
function fakeBridge(seen) {
  const store = { revision: 0, state: null };
  return async r => {
    if (r.op === 'read') return { revision: store.revision, state: store.state };
    if (r.op === 'write') { store.revision++; store.state = JSON.parse(JSON.stringify(r.state)); return { revision: store.revision }; }
    seen.push({ path: r.path, body: r.body ? JSON.parse(r.body) : null });
    const ok = data => ({ status: 200, body: JSON.stringify(data), spec: '5.0.0', serverTime: Math.floor(Date.now() / 1000) });
    if (r.path === '/auth/otp/verify') return ok({ accountToken: 'a'.repeat(43), accountId: 'acc-1', expiresAt: Math.floor(Date.now() / 1000) + 86400 });
    if (r.path === '/status') return ok({ edu: null, devices: [] });
    if (r.path === '/challenge') return ok({ nonce: 'n-' + seen.length });
    if (r.path === '/devices/register') return ok({ regId: 'reg-1' });
    if (r.path === '/keys') return ok({ keyList: null }); // 진짜 서명 키 목록이 아니므로 여기서 KEYS로 멈춤(정상)
    if (r.path === '/license/token') return ok({ token: 'x.y.z' });
    return { status: 404, body: '{"error":{"code":"NOT_FOUND"}}' };
  };
}
test(`앱 이름 "${APP}" → 기기 등록 요청에 app: "ssen-${APP}"`, async () => {
  const seen = [];
  const svc = createAuthService(fakeBridge(seen), APP);
  await svc.act('peek');
  await svc.act('login', { email: 'teacher@senedu.kr', code: '123456' });
  const reg = seen.find(s => s.path === '/devices/register');
  assert.ok(reg, '기기 등록 요청이 나가야 함: ' + JSON.stringify(seen.map(s => s.path)));
  assert.equal(reg.body.app, 'ssen-' + APP);
  assert.equal(reg.body.os, 'Windows');
});
test('잘못된 앱 이름은 거부', () => {
  for (const bad of ['', 'PDF', 'ssen-pdf', 'a', '../x', 'toolongappname12345']) assert.throws(() => createAuthService(async () => ({}), bad), /BAD_APP_ID/);
});
