// ssen-auth-kit 1.0 — 쎈PDF 1.0.4 auth-ui 기반. initAuthUI({ appName, version, seriesText, protectHint, buttonParent, onProtect, copyright, origin })
window.addEventListener("keydown", (e) => {
  if (document.querySelector("#authDialog")?.open) e.stopImmediatePropagation();
}, true);
let snapshot = { ready: false, canEdit: false, verdict: "LOGIN" }, onProtect;
const canEdit = () => !!snapshot.canEdit;
function requireEdit() {
  if (canEdit()) return true;
  window.dispatchEvent(new Event("sen-auth-required"));
  return false;
}
const messages = {};
// ssen-auth-kit: initAuthUI(options)로 앱 정보를 받는다(아래 cfg 기본값 참고).
let cfg = { appName: "SsenApp", version: "0.0.0", copyright: "© 2026 상명초 김승현, 등촌중 김형훈", origin: null, seriesText: "한 계정으로 쎈 시리즈 프로그램을 함께 사용합니다.", protectHint: "열어 보기는 계속 사용할 수 있습니다.", buttonParent: "header .save-actions" };
function report() {
  return { app: cfg.appName, version: cfg.version, copyright: cfg.copyright, ...(cfg.origin ? { origin: cfg.origin } : {}), lastFailure: snapshot.lastFailure || null, events: snapshot.diagnostics || [] };
}
function apply(next) {
  const recovered = snapshot.activeError && !next.activeError;
  snapshot = next;
  if (ready) {
    if (recovered) el("authNotice").textContent = "공통 인증 상태를 정상적으로 확인했습니다.";
    paint();
  }
}
async function command(action2, args = {}) {
  if (client.busy) return;
  client.busy = true;
  try {
    paint();
    const r = await window.desktop.authCommand(action2, args);
    apply(r.state);
    if (!r.ok) throw Error(r.error);
    return r;
  } finally {
    client.busy = false;
    paint();
  }
}
const client = {
  busy: false,
  error: "",
  onchange: () => {
  },
  get state() {
    return { accountId: snapshot.accountPresent ? "present" : null, accountToken: snapshot.loggedIn ? "present" : null, email: snapshot.email, regId: snapshot.registered ? "current" : null, token: snapshot.hasLicense ? "present" : null, edu: snapshot.edu, redeemRetryAt: snapshot.retryAt, claims: snapshot.hasLicense ? { plan: snapshot.plan, ent_exp: snapshot.expiresAt } : null };
  },
  get status() {
    return { edu: snapshot.edu, devices: (snapshot.devices || []).map((d) => ({ ...d, regId: d.current ? "current" : d.regId })), devicesUsed: snapshot.devicesUsed ?? snapshot.devices?.length, maxDevices: snapshot.maxDevices };
  },
  verdict: () => snapshot.verdict,
  canEdit,
  load: () => command("init"),
  tick: () => command("sync"),
  send: (email) => command("send", { email }),
  login: (email, code) => command("login", { email, code }),
  redeem: (code) => command("redeem", { code }),
  sendEdu: () => command("eduSend"),
  reverifyEdu: (code) => command("eduVerify", { code }),
  startTrial: () => command("trial"),
  registerAgain: () => command("register"),
  refresh: () => command("refresh"),
  devices: () => command("devices"),
  logout: () => command("logout"),
  deactivate: (regId) => command("deactivate", { regId: regId === "current" ? snapshot.devices?.find((d) => d.current)?.regId : regId })
};
const el = (id) => document.getElementById(id);
const escape = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const descriptions = { OK: "편집과 내보내기를 사용할 수 있습니다.", OFFLINE_GRACE: "인터넷에 연결해 이용권을 다시 확인해 주세요. 지금은 정상 사용 가능합니다.", EXPIRED: "오프라인 허가증이 만료됐습니다. 인터넷 연결 후 다시 확인해 주세요.", ENT_EXPIRED: "이용 기간이 끝났습니다. 기존 작업은 열고 저장할 수 있습니다.", LOGIN: "이메일 인증 후 90일 무료 체험 또는 통합 이용권을 사용하세요." };
function describe(code) {
  return descriptions[code] || snapshot.message || messages[code] || "인증 정보를 다시 확인해 주세요. 기존 작업 파일은 보존됩니다.";
}
let ready = false, lastFull = false, cooldown = 0, eduCooldown = 0, loginExpanded = false;
function show() {
  if (!ready) return;
  const dlg = el("authDialog");
  if (!dlg.open) dlg.showModal();
  paint();
}
window.SsenAuth = { status: () => client.verdict(), canEdit: () => client.canEdit(), requireEdit, open: show };
function paint() {
  if (!ready) return;
  // 1.0.1: 첫 상태를 받기 전에는 '작업 보호 모드'로 단정하지 않고 확인 중으로 표시
  if (!snapshot.ready) {
    el("authButton").textContent = "이용권 확인 중…";
    el("authBar").hidden = true;
    return;
  }
  const v = client.verdict(), full = client.canEdit(), state = client.state;
  const edu = client.status?.edu || state?.edu;
  const label = full ? state?.claims?.plan === "trial" ? "무료 체험" : state?.claims?.plan === "edu_free" ? "센스쿨 계정" : "통합 이용권" : "작업 보호 모드";
  el("authButton").textContent = label;
  el("authBadge").textContent = label;
  el("authBadge").dataset.mode = full ? "full" : "protect";
  el("authSummary").textContent = describe(v);
  el("authBarText").textContent = full ? describe(v) : describe(v) + " " + cfg.protectHint;
  el("authBar").hidden = v === "OK" && !client.error;
  el("authAccount").textContent = state?.email || "아직 인증하지 않았습니다.";
  el("authExpiry").textContent = !snapshot.hasLicense ? "" : state?.claims?.ent_exp ? "이용 기한 · " + new Date(state.claims.ent_exp * 1e3).toLocaleString("ko-KR") : snapshot.unlimited ? "무기한 이용권" : "이용 기한 확인 필요";
  el("authError").textContent = snapshot.activeError?.message || "";
  el("authError").hidden = !snapshot.activeError;
  el("authBusy").hidden = !client.busy;
  for (const b of el("authDialog").querySelectorAll("button[data-auth-action]")) b.disabled = client.busy;
  el("authForm").hidden = !!state?.accountId && !loginExpanded;
  el("authChangeLogin").hidden = !state?.accountId;
  el("authRedeemPanel").hidden = !state?.accountId || !!edu;
  const lockedUntil = state?.redeemRetryAt || 0, locked = Date.now() / 1e3 < lockedUntil;
  el("authRedeemSubmit").disabled = client.busy || locked || !state?.regId;
  el("authLicenseCode").disabled = client.busy || locked;
  el("authRedeemHint").textContent = locked ? "다시 입력 가능 · " + new Date(lockedUntil * 1e3).toLocaleString("ko-KR") : !state?.regId ? "먼저 이 PC를 등록해 주세요." : "메일로 받은 이용권 코드를 입력하세요. 발급받은 이메일 계정으로 로그인해야 합니다.";
  el("authEduInfo").hidden = !edu;
  el("authEduInfo").textContent = edu ? "센스쿨 계정 · " + new Date(edu.expiresAt * 1e3).toLocaleDateString("ko-KR") + "까지" + (edu.status === "revoked" ? " · 정지됨" : " · 매년 이메일을 재인증하면 계속 무료로 이용할 수 있습니다.") : "";
  el("authEduPanel").hidden = !state?.accountToken || !edu || edu.status === "revoked" || Date.now() / 1e3 < (edu.reverifyFrom ?? Infinity);
  el("authEduSend").disabled = client.busy || Date.now() < eduCooldown;
  el("authSend").disabled = client.busy || Date.now() < cooldown;
  el("authRefresh").hidden = !state?.accountId;
  el("authLogout").hidden = !state?.accountId;
  el("authTrial").hidden = !state?.regId || v !== "TRIAL_NOT_STARTED";
  el("authRegister").hidden = !state?.accountToken || !!state?.regId;
  el("authDevicesButton").hidden = !state?.accountToken;
  const ds = client.status?.devices || [];
  el("authDevices").innerHTML = ds.length ? "<h3>등록 PC · " + escape(client.status.devicesUsed) + " / " + escape(client.status.maxDevices) + "대</h3>" + ds.map((d) => `<div class="auth-device"><span>${escape(d.os || "Windows PC")}${d.regId === state?.regId ? " · 이 PC" : ""}<small>등록 ${new Date(d.registeredAt * 1e3).toLocaleDateString("ko-KR")} · ${escape((d.apps || []).join(", "))}</small></span><button type="button" data-reg="${escape(d.regId)}" ${client.busy ? "disabled" : ""}>인증 해제</button></div>`).join("") : "";
  document.body.classList.toggle("auth-protected", !full);
  el("authDiagnosticText").textContent = JSON.stringify(report(), null, 2);
  document.dispatchEvent(new CustomEvent("sen-auth-change", { detail: { canEdit: full } }));
  const input = el("projectName");
  if (input) input.readOnly = !full;
  if (lastFull && !full) onProtect?.();
  lastFull = full;
}
async function action(fn) {
  el("authNotice").textContent = "";
  try {
    await fn();
  } catch (e) {
    if (e.message === "UNAUTHORIZED") {
      loginExpanded = true;
      el("authEmail").value = client.state?.email || "";
    }
  }
  paint();
}
function init() {
  document.body.insertAdjacentHTML("beforeend", `<dialog id="authDialog" aria-labelledby="authTitle"><div class="dialog-head"><h2 id="authTitle">쎈 시리즈 이용권</h2><button id="authClose" aria-label="닫기">✕</button></div><span id="authBadge"></span><h3 id="authAccount"></h3><p id="authExpiry"></p><p id="authSummary"></p><p class="auth-note">${escape(cfg.seriesText)}</p><form id="authForm"><label for="authEmail">이메일</label><input id="authEmail" type="email" autocomplete="email" maxlength="254" placeholder="사용할 이메일 주소" required><button type="button" id="authSend" data-auth-action>인증번호 받기</button><label for="authCode">인증번호</label><input id="authCode" type="text" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" placeholder="6자리 숫자"><button type="submit" id="authVerify" data-auth-action class="primary">인증하고 PC 등록</button></form><button id="authChangeLogin" type="button" hidden>이메일 다시 인증 / 계정 변경</button><p id="authEduInfo" class="auth-note" hidden></p>
<section id="authRedeemPanel" class="auth-section" hidden><h3>이용권 등록</h3><p id="authRedeemHint" class="auth-note"></p><form id="authRedeemForm"><label for="authLicenseCode">이용권 코드</label><div class="auth-inline"><input id="authLicenseCode" autocomplete="off" spellcheck="false" maxlength="64" placeholder="SSEN-XXXX-XXXX-XXXX" required><button id="authRedeemSubmit" data-auth-action class="primary">등록</button></div></form></section>
<section id="authEduPanel" class="auth-section" hidden><h3>교육용 자격 재인증</h3><p class="auth-note">인증에 성공하면 오늘부터 다시 1년 사용할 수 있습니다.</p><button type="button" id="authEduSend" data-auth-action>재인증 번호 받기</button><form id="authEduForm"><label for="authEduCode">교육용 재인증번호</label><div class="auth-inline"><input id="authEduCode" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" placeholder="6자리 숫자" required><button id="authEduSubmit" data-auth-action class="primary">1년 갱신</button></div></form></section><p id="authNotice" role="status"></p><p id="authError" role="alert" hidden></p><p id="authBusy" role="status" hidden>확인 중…</p><div class="auth-actions"><button id="authTrial" data-auth-action class="primary" hidden>90일 무료 체험 시작</button><button id="authRegister" data-auth-action hidden>이 PC 다시 등록</button><button id="authRefresh" data-auth-action hidden>이용권 다시 확인</button><button id="authDevicesButton" data-auth-action hidden>등록 PC 확인</button><button id="authLogout" data-auth-action hidden>로그아웃</button></div><div id="authDevices"></div><p class="auth-note">@senedu.kr 이메일로 인증하면 무료로 이용할 수 있으며, 매년 재인증하면 계속 무료로 사용할 수 있습니다. 일반 계정은 무료 체험 또는 통합 이용권을 사용합니다.</p><p class="auth-note">이메일·기기 정보는 기존 해외 인증 서버에서 처리하고 이메일은 계정에 저장합니다. 인증 메일은 Resend로 발송합니다. PDF·이미지·작업 파일은 전송하지 않습니다. 업데이트 확인은 GitHub에서 버전 정보만 받아 옵니다. <a href="https://ssenbox.lovable.app/privacy" target="_blank" rel="noopener noreferrer">개인정보 처리 안내</a></p><button id="authViewOnly">기존 작업 열고 확인하기</button></dialog>`);
  const header = document.querySelector("header");
  const b = document.createElement("button");
  b.id = "authButton";
  b.title = "로그인·이용권·등록 PC";
  b.textContent = "이용권 확인";
  ((cfg.buttonParent && document.querySelector(cfg.buttonParent)) || header || document.body).appendChild(b);
  const bar = document.createElement("div");
  bar.id = "authBar";
  bar.innerHTML = '<span id="authBarText"></span><button id="authBarOpen">이용권 확인</button>';
  document.body.appendChild(bar);
  ready = true;
  client.onchange = paint;
  const md = b.cloneNode(true);
  md.id = "mdAccountButton";
  md.onclick = show;
  document.querySelector("#mdHeader")?.append(md);
  el("authDialog").insertAdjacentHTML("beforeend", '<details id="authDiagnostics"><summary>인증 진단 정보</summary><pre id="authDiagnosticText"></pre><button id="authCopyDiagnostics" type="button">진단 정보 복사</button></details>');
  el("authCopyDiagnostics").onclick = () => window.desktop.copyText(JSON.stringify(report(), null, 2));
  el("authDialog").querySelector("a").onclick = (e) => {
    e.preventDefault();
    (window.desktop.openExternal || window.desktop.openMarkdownLink)?.(e.currentTarget.href);
  };
  window.addEventListener("sen-auth-required", show);
  window.desktop?.onAuthState?.(apply);
  window.addEventListener("focus", () => action(() => client.tick()));
  el("authButton").onclick = el("authBarOpen").onclick = show;
  el("authClose").onclick = el("authViewOnly").onclick = () => el("authDialog").close();
  el("authSend").onclick = () => action(async () => {
    await client.send(el("authEmail").value);
    cooldown = Date.now() + 6e4;
    el("authNotice").textContent = "인증번호를 보냈습니다. 메일함을 확인해 주세요.";
    el("authCode").focus();
  });
  el("authForm").onsubmit = (e) => {
    e.preventDefault();
    action(async () => {
      await client.login(el("authEmail").value, el("authCode").value);
      el("authCode").value = "";
      loginExpanded = false;
      el("authNotice").textContent = client.state?.edu ? "교육용 이메일 인증이 완료됐습니다. 이용 기한을 확인해 주세요." : "이메일 인증이 완료됐습니다.";
    });
  };
  el("authChangeLogin").onclick = () => {
    loginExpanded = !loginExpanded;
    el("authEmail").value = client.state?.email || "";
    paint();
  };
  el("authRedeemForm").onsubmit = (e) => {
    e.preventDefault();
    action(async () => {
      const r = await client.redeem(el("authLicenseCode").value);
      el("authLicenseCode").value = "";
      el("authNotice").textContent = r.syncError ? "이용권 등록은 확인됐습니다. 권한 갱신에 실패했으니 ‘이용권 다시 확인’을 눌러 주세요." : r.already ? "이미 등록된 이용권입니다. 기존 이용 기간을 유지합니다." : "이용권 등록이 완료됐습니다.";
    });
  };
  el("authEduSend").onclick = () => action(async () => {
    await client.sendEdu();
    eduCooldown = Date.now() + 6e4;
    el("authNotice").textContent = "교육용 재인증번호를 보냈습니다. 메일함을 확인해 주세요.";
    el("authEduCode").focus();
  });
  el("authEduForm").onsubmit = (e) => {
    e.preventDefault();
    action(async () => {
      const r = await client.reverifyEdu(el("authEduCode").value);
      el("authEduCode").value = "";
      el("authNotice").textContent = r.syncError ? "교육용 자격 갱신은 완료됐습니다. ‘이용권 다시 확인’을 눌러 주세요." : "교육용 자격이 오늘부터 1년 갱신됐습니다.";
    });
  };
  el("authTrial").onclick = () => action(() => client.startTrial());
  el("authRegister").onclick = () => action(() => client.registerAgain());
  el("authRefresh").onclick = () => action(() => client.refresh());
  el("authDevicesButton").onclick = () => action(() => client.devices());
  el("authLogout").onclick = () => {
    if (confirm("쎈 시리즈 공통 계정에서 로그아웃할까요? 작업 파일은 유지됩니다.")) action(() => client.logout());
  };
  el("authDevices").onclick = (e) => {
    const b2 = e.target.closest("[data-reg]");
    if (b2 && confirm("선택한 PC의 인증을 해제할까요? 해당 PC는 다음 확인 시 사용이 제한됩니다.")) action(() => client.deactivate(b2.dataset.reg));
  };
  action(async () => {
    try {
      await client.load();
      paint();
    } finally {
      if (!client.canEdit()) show();
    }
  });
  setInterval(() => {
    paint();
  }, 1e3);
  setInterval(() => action(() => client.tick()), 6e4);
  window.addEventListener("online", () => action(() => client.tick()));
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) action(() => client.tick());
  });
}
function initAuthUI(options = {}) {
  onProtect = options.onProtect;
  for (const k of Object.keys(cfg)) if (options[k] !== undefined) cfg[k] = options[k];
  init();
  return { open: show, get state() {
    return snapshot;
  } };
}
export {
  canEdit,
  initAuthUI,
  requireEdit
};
