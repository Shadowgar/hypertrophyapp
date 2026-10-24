const {chromium}=require('/home/rocco/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const fs=require('fs'),assert=require('assert/strict'),crypto=require('crypto');
const accounts=JSON.parse(fs.readFileSync('.qualification/closeout/accounts.json'));
const scenario=process.env.CLOSEOUT_SCENARIO,a=accounts[scenario];
(async()=>{
const browser=await chromium.launch({headless:true,executablePath:'/home/rocco/.cache/ms-playwright/chromium-1208/chrome-linux/chrome',args:['--no-sandbox']});
try {
 const ctx=await browser.newContext({viewport:{width:390,height:844},timezoneId:'UTC',extraHTTPHeaders:{'X-Perf-Scenario':scenario}});
 await ctx.addInitScript(({token,name})=>{
  const D=Date;class FixedDate extends D {constructor(...args){super(...(args.length?args:['2026-10-23T17:00:00Z']))}static now(){return D.parse('2026-10-23T17:00:00Z')}}window.Date=FixedDate;
  localStorage.setItem('hypertrophy_token',token);localStorage.setItem('hypertrophy_soreness_skip:2026-10-23','1');
  const state=window.__closeout={fetches:[],longtasks:[],visible:null,usable:null};
  const original=window.fetch;window.fetch=async(...args)=>{const item={path:new URL(String(args[0]),location.href).pathname,start:performance.now()};state.fetches.push(item);try {const r=await original(...args);item.end=performance.now();item.status=r.status;return r}catch(e){item.error=String(e);throw e}};
  try{new PerformanceObserver(list=>list.getEntries().forEach(e=>state.longtasks.push({start:e.startTime,duration:e.duration}))).observe({type:'longtask',buffered:true})}catch{}
  function check(){
   if(state.visible===null&&[...document.querySelectorAll('button,h1,h2,h3')].some(el=>el.textContent.replace(/\s+/g,' ').includes(name)&&el.getBoundingClientRect().width>0))state.visible=performance.now();
   const r=document.querySelector('input[aria-label="Working repetitions"]'),w=document.querySelector('input[aria-label^="Working weight"]');
   const b=[...document.querySelectorAll('button')].find(el=>/^Save set \d+$/.test(el.textContent.trim()));
   if(state.usable===null&&r&&w&&b&&!r.readOnly&&!w.readOnly&&!b.disabled&&b.getAttribute('aria-disabled')!=='true'&&r.value&&w.value)state.usable=performance.now();
  }
  new MutationObserver(check).observe(document,{subtree:true,childList:true,attributes:true});document.addEventListener('input',()=>queueMicrotask(check));
 },{token:a.token,name:a.session.exercises[0].name});
 const results=[];
 for(const phase of ['cold','warm']){
  const page=await ctx.newPage(),cdp=await ctx.newCDPSession(page);await cdp.send('Performance.enable');const errors=[],failed=[],http=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('requestfailed',r=>failed.push({path:new URL(r.url()).pathname,error:r.failure()?.errorText}));page.on('response',r=>{if(r.status()>=400)http.push({path:new URL(r.url()).pathname,status:r.status()})});
  const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/workout/today'&&r.status()===200,{timeout:30000});const start=performance.now();
  await page.goto('http://127.0.0.1:3020/today',{waitUntil:'domcontentloaded',timeout:30000});const body=await(await response).json();
  assert.equal(body.date,'2026-10-23');assert.equal(body.exercises[0].id,a.session.exercises[0].id);assert.ok(body.workout_occurrence_id);
  const first=page.getByText(a.session.exercises[0].name,{exact:true}).filter({visible:true}).first();await first.waitFor();const visibleNode=performance.now()-start;await first.click();
  const r=page.getByLabel('Working repetitions',{exact:true}),w=page.getByLabel(/Working weight/);await r.fill('11');await w.fill('30');const save=page.getByRole('button',{name:/Save set \d+/,exact:true});await save.waitFor();assert.equal(await save.getAttribute('aria-disabled'),'false');assert.ok(await r.isEditable()&&await w.isEditable());const usableNode=performance.now()-start;
  await page.waitForLoadState('networkidle',{timeout:30000});
  const timing=await page.evaluate(()=>({marks:window.__closeout,navigation:performance.getEntriesByType('navigation').map(n=>({responseStart:n.responseStart,responseEnd:n.responseEnd,domContentLoaded:n.domContentLoadedEventEnd,load:n.loadEventEnd}))[0],paint:performance.getEntriesByType('paint').map(e=>({name:e.name,start:e.startTime})),resources:performance.getEntriesByType('resource').filter(e=>e.name.includes('/_next/')||e.name.includes('/api/')).map(e=>({path:new URL(e.name).pathname,start:e.startTime,responseStart:e.responseStart,end:e.responseEnd,encoded:e.encodedBodySize,transfer:e.transferSize,initiator:e.initiatorType}))}));
  const metrics=Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.filter(m=>['ScriptDuration','TaskDuration','LayoutDuration','RecalcStyleDuration'].includes(m.name)).map(m=>[m.name,m.value*1000]));
  assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);assert.deepEqual(http.filter(e=>!(e.status===404&&['/favicon.ico','/programs'].includes(e.path))),[]);
  assert.equal(timing.marks.fetches.filter(e=>e.path==='/api/workout/today').length,1);assert.ok(timing.marks.usable!==null);
  results.push({scenario,phase,visibleNode,usableNode,...timing,metrics,pageErrors:errors,requestFailures:failed,httpFailures:http});
  // Payloads stay private; public report gets equality booleans only.
  fs.writeFileSync('.qualification/closeout/payload-'+process.env.CLOSEOUT_KEY+'-'+phase+'.json',JSON.stringify(body));await page.close();
 }
 fs.writeFileSync('.qualification/closeout/result-'+process.env.CLOSEOUT_KEY+'.json',JSON.stringify(results));
}finally{await browser.close()}
})().catch(e=>{console.error(e.stack);process.exit(1)});
