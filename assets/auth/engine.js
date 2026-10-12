new QWebChannel(qt.webChannelTransport, channel => {
 const native=channel.objects.native;
 const pending=new Map(); let next=0, queue=Promise.resolve();
 native.reply.connect((id,text)=>{const pair=pending.get(id);if(!pair)return;pending.delete(id);clearTimeout(pair.timer);const result=JSON.parse(text);if(result.bridgeError)pair.reject(Object.assign(Error(result.bridgeError),result));else pair.resolve(result);});
 function bridge(request){return new Promise((resolve,reject)=>{const id=String(++next);const timer=setTimeout(()=>{pending.delete(id);reject(Error('BRIDGE_TIMEOUT'));},25000);pending.set(id,{resolve,reject,timer});native.rpc(id,JSON.stringify(request));});}
 const service=SsenService.createAuthService(bridge,'player');
 const serial=fn=>{const r=queue.then(fn);queue=r.catch(()=>{});return r;};
 let idle=true, memory=null;
 const push=state=>native.state(JSON.stringify(state));
 const auth=SsenThrottle.createAuthThrottle({act:(...args)=>serial(()=>service.act(...args)),authorize:()=>serial(()=>service.authorize()),summary:service.summary},
 {onState:push,isIdle:()=>idle,cache:{read:()=>memory,write:value=>{memory=value;native.saveCache(JSON.stringify(value));}}});
 globalThis.SsenRuntime={
  command:async(id,action,args)=>{try{let result;if(action==='authorize'){await auth.authorize();result={ok:true,state:auth.summary()};}else result=await auth.act(action,args);push(result.state);native.complete(id,JSON.stringify(result));}catch(error){native.complete(id,JSON.stringify({ok:false,error:'AUTH_REQUIRED',state:auth.summary()}));}},
  idle:value=>{idle=!!value;},
 };
 native.loadCache(text=>{try{memory=JSON.parse(text);}catch{} auth.prewarm();auth.act('init').then(r=>push(r.state));native.ready();});
 setInterval(()=>auth.act('sync').then(r=>push(r.state)),60000);
});
