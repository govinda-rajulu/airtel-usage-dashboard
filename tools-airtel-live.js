/* Airtel Live Overlay: runs on your logged-in airtel.in tab. Attended, per-run only. Nothing stored or uploaded. */
(()=>{
'use strict';
if(location.hostname!=='www.airtel.in')throw Error('Run on your logged-in airtel.in tab.');
if(window.__airtelLive)throw Error('Overlay already running.');
window.__airtelLive=true;
const MAX=60;
const cap=[];let fresh=null;
const of=window.fetch, os=XMLHttpRequest.prototype.setRequestHeader, oS=XMLHttpRequest.prototype.send;
const host=u=>{try{return new URL(u,location.href).origin==='https://digi-api.airtel.in';}catch{return false;}};
const H=h=>{const o={};if(!h)return o;const src=h instanceof Headers?Object.fromEntries(h.entries()):h;for(const k in src)o[k.toLowerCase()]=String(src[k]);return o;};
window.fetch=function(u,i={}){try{if(host(u)){fresh={url:String(u),method:(i.method||'GET').toUpperCase(),headers:H(i.headers),body:typeof i.body==='string'?i.body:null};}}catch(e){}return of.apply(this,arguments);};
XMLHttpRequest.prototype.setRequestHeader=function(k,v){try{if(k.toLowerCase()!=='cookie'){this.__h=this.__h||{};this.__h[k.toLowerCase()]=v;}}catch(e){}return os.apply(this,arguments);};
XMLHttpRequest.prototype.send=function(b){try{this.addEventListener('load',()=>{try{
 if(!host(this.responseURL))return;
 const u=new URL(this.responseURL);
 fresh={url:this.responseURL,method:(this.__m||'GET'),headers:this.__h||{},body:typeof b==='string'?b:null};
 let d=null;try{d=this.responseType==='json'?this.response:JSON.parse(this.responseText);}catch(e){}
 if(d)cap.push({path:u.pathname,lob:u.searchParams.get('lob')||'',si:u.searchParams.get('siNumber')||'',data:d});
 if(cap.length>MAX)cap.shift();
}catch(e){}},{once:true});}catch(e){}return oS.apply(this,arguments);};
const oo=XMLHttpRequest.prototype.open;XMLHttpRequest.prototype.open=function(m){this.__m=(m||'GET').toUpperCase();return oo.apply(this,arguments);};
const mask=v=>String(v==null?'':v).replace(/\d(?=\d{4})/g,'*').replace(/(^[^@\s]{3})[^@\s]*(@.*)/,'$1***$2');
function deepMask(x){if(Array.isArray(x))return x.map(deepMask);if(x&&typeof x==='object'){const o={};for(const k in x)o[k]=deepMask(x[k]);return o;}if(typeof x==='string')return mask(x);return x;}
const css='position:fixed;inset:4vh 4vw;z-index:2147483647;background:#0b1e22;color:#eef4e8;font:14px/1.5 system-ui;overflow:auto;border:1px solid #2b4b4f;padding:18px;box-shadow:0 30px 80px #000c';
const root=document.createElement('div');root.id='airtel-live';root.style.cssText=css;
root.innerHTML='<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><b style="font-size:18px;color:#f6c200">Airtel Live Dashboard</b><button id="alBuild">Build / refresh</button><button id="alJson">Copy sanitized JSON</button><button id="alClose">Close</button><span id="alStat" style="color:#9fb3aa">navigate the site normally, then Build</span></div><div id="alBody" style="margin-top:14px"></div>';
document.body.appendChild(root);
const el=id=>root.querySelector('#'+id);
el('alClose').onclick=()=>{window.fetch=of;XMLHttpRequest.prototype.setRequestHeader=os;XMLHttpRequest.prototype.send=oS;XMLHttpRequest.prototype.open=oo;delete window.__airtelLive;root.remove();};
async function probeUsage(){
 if(!fresh||!fresh.headers['x-bsy-utkn']){return {note:'no live Airtel request captured yet: navigate one section, then Build again'};}
 const base='https://digi-api.airtel.in/guardian/api/services/widgets/webApp/basePlanUsage/v1/details';
 const seen=new Set();for(const c of cap){if(c.si)seen.add(c.si+'|'+c.lob);}
 const here=new URL(location.href);const si=here.searchParams.get('siNumber');
 if(si){for(const lob of ['AIRFIBER','DSL','DTH'])seen.add(si+'|'+lob);}
 const out=[];
 for(const key of seen){const[s,l]=key.split('|');const u=base+'?siNumber='+encodeURIComponent(s)+'&lob='+encodeURIComponent(l||'DSL');
  try{const r=await of(u,{headers:fresh.headers,credentials:'omit'});const t=await r.text();let j=null;try{j=JSON.parse(t);}catch(e){}
   out.push({si:mask(s),lob:l,status:r.status,hasUsage:!!(j&&JSON.stringify(j).match(/used|remaining|total|consumed/i)),body:j&&j.data?undefined:j});}catch(e){out.push({si:mask(s),lob:l,status:'ERR'});}}
 return out;
}
function render(usage){
 const cards=cap.map(c=>'<div style="border:1px solid #2b4b4f;padding:10px;margin:8px 0"><b>'+c.path+'</b> <span style="color:#9fb3aa">lob='+(c.lob||'-')+'</span><pre style="white-space:pre-wrap;max-height:180px;overflow:auto;background:#07161a;padding:8px">'+JSON.stringify(deepMask(c.data),null,1).slice(0,4000)+'</pre></div>').join('');
 el('alBody').innerHTML='<h3 style="color:#f6c200">Usage probe (realtime)</h3><pre style="background:#07161a;padding:8px;white-space:pre-wrap">'+JSON.stringify(usage,null,1)+'</pre><h3 style="color:#f6c200">Captured this session ('+cap.length+')</h3>'+(cards||'<i>nothing yet</i>');
 el('alStat').textContent='built '+new Date().toLocaleTimeString();
}
el('alBuild').onclick=async()=>{el('alStat').textContent='probing...';render(await probeUsage());};
el('alJson').onclick=()=>{const out={capturedAt:new Date().toISOString(),responses:deepMask(cap)};navigator.clipboard.writeText(JSON.stringify(out,null,1));el('alStat').textContent='sanitized JSON copied (PII masked)';};
})();
