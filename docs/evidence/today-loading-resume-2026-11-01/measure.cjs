const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('fs'),assert=require('assert/strict');
const accounts=JSON.parse(fs.readFileSync('.qualification/browser-accounts.json'));
const base='http://127.0.0.1:3043',label=process.env.PERF_LABEL||'baseline';
(async()=>{const b=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{})});const results=[];
try{for(const [mode,delay] of [['phase1','none'],['phase2','none'],['flexible','none'],['customized','none'],['phase1','progress'],['phase1','health']]){
 const context=await b.newContext({viewport:{width:390,height:844},extraHTTPHeaders:{'X-Perf-Scenario':`${label}-${mode}-${delay}`}});
 const routeErrors=[];const p=await context.newPage();p.setDefaultTimeout(15000);const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{window.__reads=[];const original=window.fetch;window.fetch=async(...args)=>{const u=new URL(typeof args[0]==='string'?args[0]:args[0].url,location.href),start=performance.now();try{const r=await original(...args);if(u.pathname.startsWith('/api/'))window.__reads.push({path:u.pathname,start,end:performance.now(),status:r.status});return r;}catch(e){if(u.pathname.startsWith('/api/'))window.__reads.push({path:u.pathname,start,end:performance.now(),status:0});throw e;}};});
 if(delay!=='none')await p.route('**/api/**',async route=>{try{const path=new URL(route.request().url()).pathname;if((delay==='progress'&&path.endsWith('/progress'))||(delay==='health'&&path.endsWith('/health'))){const r=await route.fetch();await new Promise(done=>setTimeout(done,1500));return route.fulfill({response:r});}return route.continue();}catch{routeErrors.push('intercepted read failed');}});
 await p.goto(base,{waitUntil:'domcontentloaded'});
 for(let rep=0;rep<3;rep++){
  await p.evaluate(token=>{localStorage.clear();localStorage.setItem('hypertrophy_token',token)},accounts[mode].token);
  const start=performance.now();await p.goto(base+'/today',{waitUntil:'domcontentloaded'});
  const name=accounts[mode].session.exercises[0].name;
  const row=p.getByRole('button',{name:new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'))}).first();await row.waitFor();const visible=performance.now()-start;
  const skip=p.getByRole('button',{name:'Skip',exact:true});await skip.waitFor();const soreness=performance.now()-start;await skip.click();await row.click();
  await p.getByLabel('Working weight (lb)',{exact:true}).fill('20');await p.getByLabel('Working repetitions',{exact:true}).fill('8');
  const technique=p.getByLabel('I have read the source technique for this set.',{exact:true});if(await technique.isVisible())await technique.check();
  const save=p.getByRole('button',{name:'Save set 1',exact:true});assert.equal(await save.getAttribute('aria-disabled'),'false');const usable=performance.now()-start;
  await p.waitForLoadState('networkidle');const reads=await p.evaluate(()=>window.__reads);results.push({mode,delay,rep,visible_ms:visible,soreness_ms:soreness,usable_ms:usable,reads:reads.map(r=>({...r,path:r.path.replace(/\/workout\/[^/]+\//,'/workout/<occurrence>/')}))});
  fs.writeFileSync('.qualification/'+label+'-measurements.json',JSON.stringify(results,null,2));console.log(label,mode,delay,rep,Math.round(soreness),Math.round(usable));
 }
 await p.unrouteAll({behavior:'wait'});assert.deepEqual(routeErrors,[]);assert.deepEqual(errors,[]);await context.close();
}}finally{fs.writeFileSync('.qualification/'+label+'-measurements.json',JSON.stringify(results,null,2));await b.close();}})().catch(e=>{console.error('Measurement failed:',e.name);process.exitCode=1});
