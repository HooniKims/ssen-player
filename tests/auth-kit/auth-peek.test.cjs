'use strict';
// 실제 인증 서비스(auth-service.cjs)의 peek: 저장소 읽기 1번만, 화면 준비(ready) 상태로 응답
const test = require('node:test'), assert = require('node:assert/strict');
const { createAuthService } = require('../../assets/auth/auth-service.cjs');
test('peek은 저장소를 한 번만 읽고 ready 상태를 돌려줌', async () => {
  const ops = [];
  const store = { revision: 0, state: null };
  const bridge = async r => { ops.push(r.op); if (r.op === 'read') return { revision: store.revision, state: store.state }; if (r.op === 'write') { store.revision++; store.state = r.state; return { revision: store.revision }; } throw Error('NETWORK'); };
  const svc = createAuthService(bridge);
  const r = await svc.act('peek');
  assert.equal(r.ok, true, JSON.stringify(r));
  assert.equal(r.state.ready, true);
  assert.equal(ops.filter(o => o === 'read').length, 1);
  assert.equal(ops.filter(o => o === 'api').length, 0, 'peek은 네트워크를 쓰지 않음');
});

test('1.0.4: 인증 서버 연결 실패 원인(netCause·netVia)이 진단 정보에 남음', async () => {
  const store = { revision: 0, state: null };
  const bridge = async r => { if (r.op === 'read') return { revision: store.revision, state: store.state }; if (r.op === 'write') { store.revision++; store.state = r.state; return { revision: store.revision }; } throw Object.assign(Error('NETWORK'), { netCause: 'net::ERR_CERT_AUTHORITY_INVALID', netVia: 'chromium' }); };
  const svc = createAuthService(bridge);
  await svc.act('peek');
  const r = await svc.act('send', { email: 'teacher@senedu.kr' });
  assert.equal(r.ok, false);
  const f = svc.summary().lastFailure;
  assert.equal(f.code, 'NETWORK');
  assert.equal(f.netCause, 'net::ERR_CERT_AUTHORITY_INVALID');
  assert.equal(f.netVia, 'chromium');
});
