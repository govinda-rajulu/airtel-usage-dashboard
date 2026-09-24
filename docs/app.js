const $=id=>document.getElementById(id);
const fmtGB=v=>v==null?'—':`${v} GB`;
fetch('data/usage.json').then(r=>r.json()).then(d=>{
  $('title').textContent=d.meta.title;
  $('source').textContent=d.meta.source;
  $('generated').textContent=d.meta.generatedAt;
  const c=d.current||{};
  const pct=(c.usedGB&&c.totalGB)?Math.min(100,Math.round(c.usedGB/c.totalGB*100)):null;
  $('usageHeadline').textContent=pct==null?(c.message||'Usage not available'):`${pct}% used`;
  $('usageMessage').textContent=pct==null?`${d.meta.usageStatus} Cycle: ${c.cycle||'not available'}`:`Cycle: ${c.cycle||'not available'}`;
  $('dialValue').textContent=pct==null?'—':pct+'%';
  $('dial').style.background=`conic-gradient(var(--accent) 0 ${pct||0}%,var(--line) ${pct||0}% 100%)`;
  $('used').textContent=fmtGB(c.usedGB);$('total').textContent=fmtGB(c.totalGB);$('remaining').textContent=fmtGB(c.remainingGB);$('days').textContent=c.daysLeft==null?'—':c.daysLeft;
  $('barFill').style.width=(pct||0)+'%';
  $('planName').textContent=d.plan.name;
  facts($('planFacts'),{Account:d.plan.accountId,Status:d.plan.status,Price:d.plan.price,'Bill mode':d.plan.billMode,'Bill receiver':d.plan.billReceiver});
  $('billAmount').textContent=d.billing.amount;
  facts($('billFacts'),{Status:d.billing.status,Payable:d.billing.payable,Generated:d.billing.generatedOn,'Due date':d.billing.dueDate,Cycle:c.cycle});
  const rows=d.connections.map(x=>`<tr><td>${x.service}</td><td>${x.identifier}</td><td>${x.plan||x.line||'—'}<br><small>${x.accountNumber||''}</small></td><td>${x.speed||'—'}<br><small>${x.data||''}</small></td><td>${x.usageStatus||'—'}</td></tr>`).join('');
  document.querySelector('#connections tbody').innerHTML=rows;
  $('history').innerHTML=d.billing.history.map(h=>`<div><span>${h.month}</span><strong>${h.amount}</strong></div>`).join('');
  facts($('profileFacts'),{'Primary mobile':d.profile.primaryMobile,'E-bill email':d.profile.emailForEBill});
  $('shortcuts').innerHTML=d.shortcuts.map(s=>`<span>${s}</span>`).join('');
  $('fetchLog').innerHTML=d.fetchLog.map(f=>`<div><strong>${f.at}</strong><p>${f.result}: ${f.detail}</p></div>`).join('');
});
function facts(el,obj){el.innerHTML=Object.entries(obj).filter(([,v])=>v).map(([k,v])=>`<dt>${k}</dt><dd>${v}</dd>`).join('')}
