(function(){
const D=window.CLIMATE;if(!D)return;
const Y0=1990,Y1=2022,B=1.61,B15=0.79,NS='http://www.w3.org/2000/svg';
const QN=['Shortfall, within boundary','Shortfall and overshoot','Foundation met, overshoot','Safe and just'];
const QC=['#f2c14e','#ef6f6c','#5aa9ff','#5fd1b0'];
const app=document.getElementById('cs-app');if(!app)return;
const svg=document.getElementById('cs-svg'),tip=document.getElementById('cs-tip'),ctl=document.getElementById('cs-controls'),leg=document.getElementById('cs-legend'),read=document.getElementById('cs-read');
const S={v:'space',year:2022,acc:'cons',cont:'All',hl:new Set(['IND','USA','CHN','CRI','LKA']),timer:null,reqShow:{main:1,health:1,prod:0},pw:false,win:'2011--2022',above:false,country:'IND'};
const isos=Object.keys(D.C).sort((a,b)=>D.C[a].n.localeCompare(D.C[b].n));
const fmt=(v,n=1)=>v==null?'n/a':(+v).toFixed(n);
function quad(c,i,acc){const m=c.met[i],e=c[acc][i];if(m==null||e==null||c.att[i]==null)return null;return m===4?(e<=B?3:2):(e<=B?0:1)}
function el(t,a,p){const n=document.createElementNS(NS,t);for(const k in a)n.setAttribute(k,a[k]);if(p)p.appendChild(n);return n}
function txt(p,x,y,s,a){const n=el('text',Object.assign({x,y,class:'cs-t'},a||{}),p);n.textContent=s;return n}
function dims(){const w=Math.max(300,svg.parentNode.clientWidth),sm=w<620;const h=sm?380:460;svg.setAttribute('viewBox',`0 0 ${w} ${h}`);svg.setAttribute('width',w);svg.setAttribute('height',h);return{w,h,sm,m:{l:sm?44:58,r:sm?12:24,t:18,b:sm?44:50}}}
const lin=(d0,d1,r0,r1)=>v=>r0+(v-d0)/(d1-d0)*(r1-r0);
const lg=(d0,d1,r0,r1)=>{const a=Math.log10(d0),b=Math.log10(d1);return v=>r0+(Math.log10(Math.max(v,d0))-a)/(b-a)*(r1-r0)};
function showTip(html,x,y){tip.innerHTML=html;tip.hidden=false;const W=svg.parentNode.clientWidth,tw=tip.offsetWidth;tip.style.left=Math.min(Math.max(4,x+14),W-tw-4)+'px';tip.style.top=Math.max(4,y-10)+'px'}
function hideTip(){tip.hidden=true}
function axisX(g,dm,sc,ticks,lab,f){const{w,h,m}=dm;ticks.forEach(t=>{const x=sc(t);el('line',{x1:x,x2:x,y1:m.t,y2:h-m.b,class:'cs-grid'},g);txt(g,x,h-m.b+16,f?f(t):t,{'text-anchor':'middle'})});txt(g,(m.l+w-m.r)/2,h-6,lab,{'text-anchor':'middle',class:'cs-t cs-al'})}
function axisY(g,dm,sc,ticks,lab,f){const{w,h,m}=dm;ticks.forEach(t=>{const y=sc(t);el('line',{x1:m.l,x2:w-m.r,y1:y,y2:y,class:'cs-grid'},g);txt(g,m.l-6,y+4,f?f(t):t,{'text-anchor':'end'})});const tl=txt(g,12,(m.t+h-m.b)/2,lab,{'text-anchor':'middle',class:'cs-t cs-al',transform:`rotate(-90 12 ${(m.t+h-m.b)/2})`})}
function stop(){if(S.timer){clearInterval(S.timer);S.timer=null;const b=document.getElementById('cs-play');if(b){b.textContent='▶ Play';b.setAttribute('aria-pressed','false')}}}
function legend(items){leg.innerHTML=items.map(([c,l,s])=>`<span><i style="background:${c}${s?';border-radius:2px;height:3px':''}"></i>${l}</span>`).join('')}
function sel(id,label,opts,val){return `<label class="cs-f"><span>${label}</span><select id="${id}">${opts.map(([v,t])=>`<option value="${v}"${v==val?' selected':''}>${t}</option>`).join('')}</select></label>`}
function chk(id,label,on){return `<label class="cs-c"><input type="checkbox" id="${id}"${on?' checked':''}> ${label}</label>`}
const conts=['All','Africa','America','Asia','Europe','Oceania'];
function controls(){stop();const v=S.v;let h='';
if(v==='space')h=`<div class="cs-yr"><button class="cs-btn" id="cs-play" aria-pressed="false">▶ Play</button><label class="cs-f cs-range"><span>Year <b id="cs-yl">${S.year}</b></span><input type="range" id="cs-year" min="${Y0}" max="${Y1}" value="${S.year}"></label></div>`+sel('cs-acc','Emissions',[['cons','Consumption-based'],['prod','Production-based']],S.acc)+sel('cs-cont','Continent',conts.map(c=>[c,c==='All'?'World':c]),S.cont)+`<label class="cs-f"><span>Highlight a country</span><input id="cs-find" list="cs-list" placeholder="Type a country…"></label><datalist id="cs-list">${isos.map(i=>`<option value="${D.C[i].n}">`).join('')}</datalist><button class="cs-btn cs-ghost" id="cs-clear">Clear highlights</button>`;
if(v==='req')h=chk('cs-r-main','Four thresholds, consumption CO₂',S.reqShow.main)+chk('cs-r-health','Health thresholds only',S.reqShow.health)+chk('cs-r-prod','Four thresholds, production CO₂',S.reqShow.prod);
if(v==='shares')h=chk('cs-pw','Weight by population',S.pw);
if(v==='dec')h=sel('cs-win','Window',[['2001--2010','2001–2010'],['2011--2022','2011–2022']],S.win)+chk('cs-above','Only countries above the boundary',S.above);
if(v==='country')h=sel('cs-ctry','Country',isos.map(i=>[i,D.C[i].n]),S.country);
ctl.innerHTML=h;
const on=(id,ev,f)=>{const n=document.getElementById(id);if(n)n.addEventListener(ev,f)};
on('cs-year','input',e=>{stop();S.year=+e.target.value;document.getElementById('cs-yl').textContent=S.year;draw()});
on('cs-play','click',e=>{if(S.timer){stop();return}if(S.year>=Y1)S.year=Y0;e.target.textContent='❚❚ Pause';e.target.setAttribute('aria-pressed','true');S.timer=setInterval(()=>{S.year++;const r=document.getElementById('cs-year');if(r)r.value=S.year;const l=document.getElementById('cs-yl');if(l)l.textContent=S.year;draw();if(S.year>=Y1)stop()},matchMedia('(prefers-reduced-motion: reduce)').matches?900:450)});
on('cs-acc','change',e=>{S.acc=e.target.value;draw()});on('cs-cont','change',e=>{S.cont=e.target.value;draw()});
on('cs-find','change',e=>{const i=isos.find(k=>D.C[k].n.toLowerCase()===e.target.value.trim().toLowerCase());if(i){S.hl.add(i);e.target.value='';draw()}});
on('cs-clear','click',()=>{S.hl.clear();draw()});
['main','health','prod'].forEach(k=>on('cs-r-'+k,'change',e=>{S.reqShow[k]=e.target.checked?1:0;draw()}));
on('cs-pw','change',e=>{S.pw=e.target.checked;draw()});on('cs-win','change',e=>{S.win=e.target.value;draw()});on('cs-above','change',e=>{S.above=e.target.checked;draw()});
on('cs-ctry','change',e=>{S.country=e.target.value;draw()});
}
function drawSpace(){const dm=dims(),{w,h,m}=dm;svg.innerHTML='';const g=el('g',{},svg);const i=S.year-Y0;
const x=lg(0.05,70,m.l,w-m.r),y=lin(0.2,1.06,h-m.b,m.t);
el('rect',{x:m.l,y:y(1.0)-4,width:x(B)-m.l,height:8,class:'cs-safe'},g);
axisX(g,dm,x,[0.1,0.3,1,3,10,30],`CO₂ per person, ${S.acc==='cons'?'consumption':'production'}-based (t, log scale)`);
axisY(g,dm,y,[0.2,0.4,0.6,0.8,1],'Social attainment (1 = all four met)');
el('line',{x1:x(B),x2:x(B),y1:m.t,y2:h-m.b,class:'cs-bound'},g);txt(g,x(B)+5,m.t+12,'1.61 t boundary',{class:'cs-t cs-bl'});
el('line',{x1:x(B15),x2:x(B15),y1:m.t,y2:h-m.b,class:'cs-bound cs-b15'},g);if(!dm.sm)txt(g,x(B15)-5,m.t+12,'0.79 t (1.5 °C)',{class:'cs-t cs-bl2','text-anchor':'end'});
txt(g,w-m.r-6,h-m.b-10,S.year,{class:'cs-t cs-big','text-anchor':'end'});
const cnt=[0,0,0,0];let n=0;const pts=[];
isos.forEach(k=>{const c=D.C[k];if(S.cont!=='All'&&c.c!==S.cont)return;const q=quad(c,i,S.acc);if(q==null)return;cnt[q]++;n++;pts.push([k,c,q])});
pts.sort((a,b)=>(b[1].pop[i]||0)-(a[1].pop[i]||0));
const tr=el('g',{},g);
pts.forEach(([k,c,q])=>{const r=Math.max(3,Math.min(dm.sm?14:22,Math.sqrt(c.pop[i]||1)*0.9));const hl=S.hl.has(k);
const p=el('circle',{cx:x(c[S.acc][i]),cy:y(c.att[i]),r,fill:QC[q],class:'cs-pt'+(hl?' hl':'')+(S.hl.size&&!hl?' dim':''),tabindex:0,'aria-label':`${c.n}, ${S.year}`},g);
const html=`<b>${c.n}</b> · ${S.year}<br>${QN[q]}<br>CO₂: ${fmt(c[S.acc][i],2)} t · Attainment ${fmt(c.att[i],2)}<br>Thresholds met: ${c.met[i]}/4<br><small>Life exp. ${fmt(c.le[i])} · U5MR ${fmt(c.cm[i])} · Electricity ${fmt(c.el[i])}% · Employment ${fmt(c.em[i])}%</small><br><small>Click to ${hl?'remove highlight':'highlight & trace path'}</small>`;
const sh=e=>{const b=svg.getBoundingClientRect();showTip(html,(e.clientX??b.left+x(c[S.acc][i]))-b.left,(e.clientY??b.top+y(c.att[i]))-b.top)};
p.addEventListener('pointerenter',sh);p.addEventListener('pointermove',sh);p.addEventListener('pointerleave',hideTip);p.addEventListener('focus',sh);p.addEventListener('blur',hideTip);
const tg=()=>{hl?S.hl.delete(k):S.hl.add(k);hideTip();draw()};p.addEventListener('click',tg);p.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tg()}});
if(hl){let d='';for(let j=0;j<=i;j++){const e=c[S.acc][j],a=c.att[j];if(e==null||a==null)continue;d+=(d?'L':'M')+x(e).toFixed(1)+','+y(a).toFixed(1)}el('path',{d,class:'cs-trail',stroke:QC[q]},tr);txt(g,x(c[S.acc][i])+r+3,y(c.att[i])+4,c.n,{class:'cs-t cs-lab'})}});
legend(QN.map((l,q)=>[QC[q],`${l} <b>${cnt[q]}</b>`]));
read.textContent=`${S.year}: ${n} countries with data${S.cont!=='All'?' in '+S.cont:''}. ${cnt[3]} safe and just, ${cnt[2]} meet the foundation while overshooting, ${cnt[1]} have shortfall and overshoot, ${cnt[0]} shortfall within the boundary. Bubble size = population. Highlighted countries show their path since 1990.`;
}
function drawReq(){const dm=dims(),{w,h,m}=dm;svg.innerHTML='';const g=el('g',{},svg);const x=lin(Y0,Y1,m.l,w-m.r),y=lg(0.5,80,h-m.b,m.t);
axisX(g,dm,x,dm.sm?[1990,2000,2010,2022]:[1990,1995,2000,2005,2010,2015,2022],'Year');axisY(g,dm,y,[0.5,1,2,5,10,20,50],'CO₂ per person where half of countries meet the foundation (t, log)');
el('line',{x1:m.l,x2:w-m.r,y1:y(B),y2:y(B),class:'cs-bound'},g);txt(g,w-m.r-4,y(B)-6,'1.61 t boundary',{class:'cs-t cs-bl','text-anchor':'end'});
const sr={main:['#5aa9ff','Four thresholds · consumption'],health:['#5fd1b0','Health only · consumption'],prod:['#f2c14e','Four thresholds · production']};const L=[];
Object.keys(sr).forEach(k=>{if(!S.reqShow[k])return;const a=D.req[k].filter(r=>r[1]!=null&&r[1]<500);const col=sr[k][0];L.push([col,sr[k][1],1]);
let up='',lo='';a.forEach(r=>{up+=(up?'L':'M')+x(r[0])+','+y(Math.min(r[3]??r[1],80));});[...a].reverse().forEach(r=>{lo+='L'+x(r[0])+','+y(Math.max(r[2]??r[1],0.5))});
el('path',{d:up+lo+'Z',fill:col,class:'cs-band'},g);el('path',{d:a.map((r,j)=>(j?'L':'M')+x(r[0])+','+y(Math.min(r[1],80))).join(''),stroke:col,class:'cs-line'},g)});
const hv=el('line',{y1:m.t,y2:h-m.b,class:'cs-hover',visibility:'hidden'},g);
const ov=el('rect',{x:m.l,y:m.t,width:w-m.l-m.r,height:h-m.t-m.b,fill:'transparent'},g);
ov.addEventListener('pointermove',e=>{const b=svg.getBoundingClientRect(),px=(e.clientX-b.left)*(w/b.width);const yr=Math.round(Y0+(px-m.l)/(w-m.l-m.r)*(Y1-Y0));hv.setAttribute('x1',x(yr));hv.setAttribute('x2',x(yr));hv.setAttribute('visibility','visible');
let html=`<b>${yr}</b>`;Object.keys(sr).forEach(k=>{if(!S.reqShow[k])return;const r=D.req[k].find(r=>r[0]===yr);if(r)html+=`<br><i class="sw" style="background:${sr[k][0]}"></i>${sr[k][1]}: <b>${fmt(r[1])} t</b> <small>(${fmt(r[2])}–${fmt(r[3])})</small>`});showTip(html,e.clientX-b.left,e.clientY-b.top)});
ov.addEventListener('pointerleave',()=>{hideTip();hv.setAttribute('visibility','hidden')});
legend(L.concat([['#e8e8ed','Shaded band = 95% bootstrap interval',1]]));
read.textContent='The carbon requirement is a descriptive cross-country summary: the CO₂ per person at which a fitted 50% of countries meet the social foundation. It fell about 3.6% a year to 8.5 t in 2022, still 5.3 times the 1.61 t boundary. It is not what any single country needs. Hover for yearly values.';}
function drawShares(){const dm=dims(),{w,h,m}=dm;svg.innerHTML='';const g=el('g',{},svg);const data=S.pw?D.qp:D.q;const x=lin(data[0][0],data.at(-1)[0],m.l,w-m.r),y=lin(0,1,h-m.b,m.t);
axisX(g,dm,x,dm.sm?[1991,2000,2010,2022]:[1991,1995,2000,2005,2010,2015,2022],'Year');axisY(g,dm,y,[0,.25,.5,.75,1],S.pw?'Share of population in the panel':'Share of countries (balanced panel)',v=>Math.round(v*100)+'%');
const order=[0,1,2,3];let base=data.map(()=>0);
order.forEach(q=>{const top=data.map((r,j)=>base[j]+(r[q+1]||0));let d=data.map((r,j)=>(j?'L':'M')+x(r[0])+','+y(top[j])).join('');d+=[...data].reverse().map((r,jj)=>'L'+x(r[0])+','+y(base[data.length-1-jj])).join('')+'Z';el('path',{d,fill:QC[q],class:'cs-area'},g);base=top});
const hv=el('line',{y1:m.t,y2:h-m.b,class:'cs-hover',visibility:'hidden'},g);const ov=el('rect',{x:m.l,y:m.t,width:w-m.l-m.r,height:h-m.t-m.b,fill:'transparent'},g);
ov.addEventListener('pointermove',e=>{const b=svg.getBoundingClientRect(),px=(e.clientX-b.left)*(w/b.width);const yr=Math.round(data[0][0]+(px-m.l)/(w-m.l-m.r)*(data.at(-1)[0]-data[0][0]));const r=data.find(r=>r[0]===yr);if(!r)return;hv.setAttribute('x1',x(yr));hv.setAttribute('x2',x(yr));hv.setAttribute('visibility','visible');showTip(`<b>${yr}</b>`+QN.map((l,q)=>`<br><i class="sw" style="background:${QC[q]}"></i>${l}: <b>${Math.round(r[q+1]*100)}%</b>`).join(''),e.clientX-b.left,e.clientY-b.top)});
ov.addEventListener('pointerleave',()=>{hideTip();hv.setAttribute('visibility','hidden')});
legend(QN.map((l,q)=>[QC[q],l]));const f=data[0],L=data.at(-1);
read.textContent=`From ${f[0]} to ${L[0]}, the share meeting the foundation while overshooting rose from ${Math.round(f[3]*100)}% to ${Math.round(L[3]*100)}%${S.pw?' of people':' of countries'}; the safe and just share stayed at ${Math.round(L[4]*100)}%. Countries rarely changed configuration between periods.`;}
function drawDec(){const dm=dims(),{w,h,m}=dm;svg.innerHTML='';const g=el('g',{},svg);let a=D.dec.filter(d=>d.w===S.win&&d.g!=null&&d.gdp!=null);if(S.above)a=a.filter(d=>d.ab);
const x=lin(-6,12,m.l,w-m.r),y=lin(-10,14,h-m.b,m.t);
axisX(g,dm,x,[-6,-3,0,3,6,9,12],'GDP per person, trend growth (% a year)',v=>v+'%');axisY(g,dm,y,[-10,-5,0,5,10],'CO₂ per person, trend growth (% a year)',v=>v+'%');
el('line',{x1:x(-6),x2:x(12),y1:y(0),y2:y(0),class:'cs-zero'},g);el('line',{x1:x(-6),y1:y(-6),x2:x(12),y2:y(12),class:'cs-diag'},g);
if(!dm.sm){txt(g,x(11.5),y(11.5)+16,'emissions grow as fast as income',{class:'cs-t cs-bl2','text-anchor':'end'});txt(g,x(11.5),y(0)+16,'below 0: emissions falling',{class:'cs-t cs-bl2','text-anchor':'end'})}
const col=d=>d.cls==='Absolute'?'#5fd1b0':d.cls==='Relative'?'#5aa9ff':'#8e8e93';
const cl=v=>Math.max(-10,Math.min(14,v)),cx=v=>Math.max(-6,Math.min(12,v));
a.forEach(d=>{const p=el('circle',{cx:x(cx(d.gdp)),cy:y(cl(d.g)),r:dm.sm?4:5.5,fill:col(d),class:'cs-pt'+(d.ok&&d.ab?' ok':''),tabindex:0,'aria-label':d.n},g);
const html=`<b>${d.n}</b> · ${S.win.replace('--','–')}<br>${d.cls} decoupling${d.rob?' (robust)':''}<br>CO₂ growth ${fmt(d.g)}% · GDP growth ${fmt(d.gdp)}%<br>CO₂ in ${S.win.slice(-4)}: ${fmt(d.last,2)} t${d.ab?`<br>Needed to reach 1.61 t by 2050: <b>${fmt(d.req)}% a year</b><br>${d.ok?'On track':'Not on track'}`:'<br>Within the boundary'}`;
const sh=e=>{const b=svg.getBoundingClientRect();showTip(html,(e.clientX??b.left+x(d.gdp))-b.left,(e.clientY??b.top+y(d.g))-b.top)};p.addEventListener('pointerenter',sh);p.addEventListener('pointermove',sh);p.addEventListener('pointerleave',hideTip);p.addEventListener('focus',sh);p.addEventListener('blur',hideTip)});
legend([['#5fd1b0','Absolute: income up, emissions down'],['#5aa9ff','Relative: emissions grow slower than income'],['#8e8e93','No decoupling / no income growth'],['transparent','<span class="cs-ring"></span> Above boundary and on track for 2050']]);
const abs=a.filter(d=>d.cls==='Absolute').length,aa=a.filter(d=>d.cls==='Absolute'&&d.ab),ok=aa.filter(d=>d.ok).length;
const sc=D.scen.map(s=>`${s[0].replace('--','–')}: ${s[2]} of ${s[3]}`).join('; ');
read.textContent=`${S.win.replace('--','–')}: ${abs} of ${a.length} countries shown decoupled absolutely; ${aa.length} of them were above the boundary and ${ok} were cutting fast enough to reach 1.61 t by 2050.${S.win==='2011--2022'?' Scenarios reaching the boundary by 2050 — '+sc+'.':''}`;}
function drawCountry(){const dm=dims(),{w,h,sm}=dm;svg.innerHTML='';const c=D.C[S.country];
const P=[['le','Life expectancy (years)',74,1,[40,85]],['cm','Under-5 mortality (per 1,000)',25,0,[0,250]],['el','Electricity access (%)',95,1,[0,100]],['em','Employment (% of labour force)',94,1,[60,100]],['cons','CO₂ per person, consumption (t)',B,0,null],['prod','CO₂ per person, production (t)',B,0,null]];
const cols=sm?2:3,rows=Math.ceil(P.length/cols),pw=w/cols,ph=h/rows;
P.forEach(([k,lab,th,hi,dom],n)=>{const gx=(n%cols)*pw,gy=Math.floor(n/cols)*ph;const g=el('g',{transform:`translate(${gx},${gy})`},svg);const ml=34,mr=8,mt=22,mb=22;
const vals=c[k].filter(v=>v!=null);txt(g,ml-28,14,sm?lab.replace(/ \(.*\)/,'').replace('CO₂ per person, ','CO₂ '):lab,{class:'cs-t cs-pt-t'});
if(!vals.length){txt(g,pw/2,ph/2,'No data',{class:'cs-t','text-anchor':'middle'});return}
let d0=dom?dom[0]:0,d1=dom?dom[1]:Math.max(B*1.6,Math.max(...vals)*1.1);d0=Math.min(d0,Math.min(...vals));d1=Math.max(d1,Math.max(...vals));
const x=lin(Y0,Y1,ml,pw-mr),y=lin(d0,d1,ph-mb,mt);
[d0,(d0+d1)/2,d1].forEach(t=>{el('line',{x1:ml,x2:pw-mr,y1:y(t),y2:y(t),class:'cs-grid'},g);txt(g,ml-4,y(t)+4,t<10?(+t).toFixed(1):Math.round(t),{'text-anchor':'end',class:'cs-t cs-sm'})});
[Y0,2006,Y1].forEach(t=>txt(g,x(t),ph-6,t,{'text-anchor':'middle',class:'cs-t cs-sm'}));
const good=hi?(v=>v>=th):(v=>v<=th);el('line',{x1:ml,x2:pw-mr,y1:y(th),y2:y(th),class:'cs-bound'},g);txt(g,pw-mr-2,y(th)-4,(k==='cons'||k==='prod')?'boundary':'threshold',{class:'cs-t cs-bl','text-anchor':'end'});
let path='';c[k].forEach((v,j)=>{if(v==null){path+=' ';return}path+=(path&&!path.endsWith(' ')?'L':'M')+x(Y0+j)+','+y(v)});el('path',{d:path.replace(/ /g,''),class:'cs-line',stroke:'#e8e8ed'},g);
c[k].forEach((v,j)=>{if(v==null)return;const ok=good(v);const p=el('circle',{cx:x(Y0+j),cy:y(v),r:sm?2.2:2.8,fill:ok?'#5fd1b0':'#ef6f6c'},g);p.addEventListener('pointerenter',e=>{const b=svg.getBoundingClientRect();showTip(`<b>${c.n} · ${Y0+j}</b><br>${lab}: <b>${fmt(v,k==='cons'||k==='prod'?2:1)}</b><br>${ok?'Meets':'Misses'} ${k==='cons'||k==='prod'?'the 1.61 t boundary':'the threshold ('+(hi?'≥ ':'≤ ')+th+')'}`,e.clientX-b.left,e.clientY-b.top)});p.addEventListener('pointerleave',hideTip)})});
legend([['#5fd1b0','Meets threshold / within boundary'],['#ef6f6c','Misses threshold / above boundary'],['#ff9f0a','Threshold or boundary line',1]]);
const L=Y1-Y0;let lastQ=null,ly=null;for(let j=L;j>=0;j--){const q=quad(c,j,'cons');if(q!=null){lastQ=q;ly=Y0+j;break}}
read.textContent=`${c.n} (${c.c}). ${lastQ!=null?`In ${ly}, configuration: ${QN[lastQ]}.`:'Consumption-based emissions are not available, so no configuration is assigned.'} Green points meet each social threshold or stay within the climate boundary; coral points do not. Missing years are left blank, never filled.`;}
function draw(){hideTip();({space:drawSpace,req:drawReq,shares:drawShares,dec:drawDec,country:drawCountry})[S.v]()}
app.querySelectorAll('[role=tab]').forEach(b=>b.addEventListener('click',()=>{app.querySelectorAll('[role=tab]').forEach(t=>t.setAttribute('aria-selected',t===b?'true':'false'));S.v=b.dataset.v;controls();draw()}));
app.querySelector('[role=tablist]').addEventListener('keydown',e=>{const t=[...app.querySelectorAll('[role=tab]')],i=t.indexOf(document.activeElement);if(i<0)return;if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();const n=t[(i+(e.key==='ArrowRight'?1:t.length-1))%t.length];n.focus();n.click()}});
const rb=document.querySelector('#cs-rob tbody');if(rb)rb.innerHTML=D.rob.map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]===''?'n/a':(+r[2]).toFixed(1)}</td><td>${r[3]===''?'n/a':(+r[3]).toFixed(1)}%</td></tr>`).join('');
let started=false;const start=()=>{if(started||!document.getElementById('climate-study').classList.contains('open'))return;started=true;controls();draw()};
addEventListener('hashchange',()=>setTimeout(start,30));setTimeout(start,60);
let rt;addEventListener('resize',()=>{clearTimeout(rt);rt=setTimeout(()=>{if(started)draw()},150)});
document.addEventListener('keydown',e=>{if(e.key==='Escape')stop()});
})();

document.addEventListener('click',function(e){var link=e.target.closest('[data-study-jump]');if(!link)return;e.preventDefault();var page=link.closest('.study-page');var dashboard=page.querySelector('.research-explorer,.cs-app,.energy-frame,.heat-embed');if(dashboard)dashboard.scrollIntoView({behavior:'instant',block:'start'})});(function(){var frame=document.getElementById('global-embed');function load(){if(frame&&!frame.src&&document.getElementById('global-study').classList.contains('open'))frame.src=frame.dataset.liveSrc}addEventListener('hashchange',load);load()})();
