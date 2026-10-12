import {initAuthUI} from './auth-ui.mjs';
new QWebChannel(qt.webChannelTransport, channel=>{
 const native=channel.objects.native;let next=0;const pending=new Map();let listener=()=>{};
 native.reply.connect((id,text)=>{const resolve=pending.get(id);if(resolve){pending.delete(id);resolve(JSON.parse(text));}});
 native.changed.connect(text=>listener(JSON.parse(text)));
 window.desktop={authCommand:(action,args)=>new Promise(resolve=>{const id=String(++next);pending.set(id,resolve);native.command(id,action,JSON.stringify(args||{}));}),onAuthState:fn=>{listener=fn;},copyText:text=>native.copyText(text),openExternal:url=>native.openExternal(url)};
 native.info(text=>{const info=JSON.parse(text);const ui=initAuthUI({appName:'SsenPlayer',version:info.version,protectHint:'영상 열기와 재생은 계속 사용할 수 있습니다.'});window.SsenAuthUI=ui;ui.open();
 document.getElementById('authClose').textContent='닫기';
 document.getElementById('authViewOnly').textContent='영상 열고 재생하기';
 const dialog=document.getElementById('authDialog');dialog?.addEventListener('close',()=>native.close());
 document.getElementById('authViewOnly')?.addEventListener('click',()=>native.close());
 });
});
