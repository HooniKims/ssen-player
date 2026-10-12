"""Run supplied public test vectors in real Chromium with the shipped Buffer shim."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PySide6.QtCore import Qt,QUrl,QTimer
from PySide6.QtWidgets import QApplication
QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
application=QApplication([])
from PySide6.QtWebEngineCore import QWebEnginePage
page=QWebEnginePage()
source=(ROOT/'assets/auth/auth-service.cjs').read_text('utf-8')
shim=(ROOT/'assets/auth/buffer-shim.js').read_text('utf-8')
vectors=[json.loads(p.read_text('utf-8')) for p in (ROOT/'tests/auth-vectors').glob('*.json')]
harness=r"""
const checks=[];
for(const data of vectors){
 let cache=emptyCache();
 for(const step of data.keyListSteps){
  const r=acceptKeyList(step.keyList,data.trust,step.now||data.now,cache);
  const got=r.ok?(r.changed?'ACCEPT':'SAME'):r.reason;
  checks.push({name:step.name,ok:got===step.expect,got,want:step.expect});
  if(r.ok)cache=r.cache;
 }
 for(const test of data.tokens){
  const ctx=test.expectArgs==='missing'?undefined:{...data.expect,...test.ctx};
  const got=verifyLicense(test.token,cache,test.now||data.now,ctx);
  checks.push({name:test.name,ok:got===test.expect,got,want:test.expect});
 }
 for(const test of data.requestSignatures){
  const h=test.headers;
  const canon=canonicalV3(test.method,test.pathAndQuery,h['X-Ssen-Nonce'],h['X-Ssen-Reg'],test.bearer,test.rawBody);
  checks.push({name:test.name+' canonical',ok:canon===test.canonical});
  checks.push({name:test.name+' signature',ok:verify(d64(h['X-Ssen-Signature']),enc.encode(canon),d64(test.signerPublicKey))});
 }
 // A legitimate test license for cut/pdf/img must not authorize player.
 const valid=data.tokens.find(t=>t.expect==='OK');
 checks.push({name:'player scope required',ok:verifyLicense(valid.token,cache,data.now,{...data.expect,app:'player'})==='SCOPE'});
}
return JSON.stringify(checks);
"""
script=shim+';(()=>{const module={exports:{}};const exports=module.exports;'+source+';const vectors='+json.dumps(vectors)+';'+harness+'})()'
def loaded(ok):
 if not ok: application.exit(2); return
 def done(result):
  try:
   checks=json.loads(result)
   failed=[r for r in checks if not r['ok']]
   print(json.dumps({'checks':len(checks),'failed':failed}),flush=True)
   application.exit(1 if failed else 0)
  except Exception: application.exit(2)
 page.runJavaScript(script,done)
page.loadFinished.connect(loaded)
page.setHtml('<html><body>Isolated crypto QA</body></html>',QUrl.fromLocalFile(str(ROOT/'tests/')))
QTimer.singleShot(30000,lambda:application.exit(3))
result=application.exec()
import shiboken6
shiboken6.delete(page)
raise SystemExit(result)
