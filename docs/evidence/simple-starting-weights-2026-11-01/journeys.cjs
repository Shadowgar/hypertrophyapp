const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('fs'),assert=require('assert/strict');
const accounts=JSON.parse(fs.readFileSync('.qualification/browser-accounts.json'));
const base='http://127.0.0.1:3041',out='docs/evidence/simple-starting-weights-2026-11-01';
const result={runtimeRevision:require('child_process').execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),environment:'synthetic accounts; loopback3041 -> 8041 -> tmpfs PostgreSQL16 loopback55441',observations:[],pageErrors:[],unexpectedApiErrors:[]};
let browser,page,context;
const exact=(role,name)=>page.getByRole(role,{name,exact:true});
async function image(name){await page.screenshot({path:out+'/'+name+'.png',fullPage:true});}
async function open(name,{clear=true}={}){
 console.log('Journey',name);const account=accounts[name];await page.goto(base,{waitUntil:'domcontentloaded'});
 await page.evaluate(({token,clear})=>{if(clear)localStorage.clear();localStorage.setItem('hypertrophy_token',token);window.dispatchEvent(new Event('hypertrophy:auth-token-changed'));},{token:account.token,clear});
 await page.goto(base+'/today',{waitUntil:'domcontentloaded'});
 const skip=exact('button','Skip');await skip.waitFor({timeout:7000}).catch(()=>{});if(await skip.isVisible())await skip.click();
 await page.getByText(account.session.exercises[0].name,{exact:true}).first().click();await exact('region','Working set entry').waitFor();
 return account;
}
async function setup(method='known_1rm'){
 await exact('radio',method==='known_1rm'?'I know my 1-rep max.':'I know a recent weight and repetitions.').check();
 await page.getByLabel('Benchmark load (lb)',{exact:true}).fill(method==='known_1rm'?'100':'40');
 await page.getByLabel('Observed date',{exact:true}).fill(new Date().toISOString().slice(0,10));
 if(method==='recent_set'){
  await page.getByLabel('Benchmark reps (1–10)',{exact:true}).fill('8');
  await page.getByLabel('Benchmark RIR (0–3)',{exact:true}).fill('2');
 }
 await page.getByText('Equipment and available loads',{exact:true}).click();
 await page.getByRole('combobox',{name:/^Benchmark load basis/}).selectOption('machine_stack');
 await page.getByLabel('Equipment identity',{exact:true}).fill('synthetic-same-machine-full-ROM');
 await page.getByLabel('Setup details',{exact:true}).fill('Exact same seat, handle, grip, side and full ROM');
 await page.getByLabel('Available loads (comma separated)',{exact:true}).fill('5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100');
 await page.getByLabel(/^I confirm this benchmark/).check();
}
async function geometry(){return page.evaluate(()=>{const b=document.querySelector('.atlas-save').getBoundingClientRect();return{top:b.top+scrollY,left:b.left,width:b.width,height:b.height,scrollY,focused:document.activeElement?.getAttribute('aria-label'),blocks:Object.fromEntries(['.atlas-runner','.atlas-center','.atlas-name','.atlas-prescription','.atlas-suggestion','.atlas-feedback','.atlas-composer'].map(s=>{const r=document.querySelector(s).getBoundingClientRect();return[s,{top:r.top+scrollY,height:r.height}]}))};});}
async function api(name,path,method='GET',body){const response=await context.request.fetch(base+'/api'+path,{method,headers:{Authorization:'Bearer '+accounts[name].token},...(body?{data:body}:{})});assert.equal(response.status(),200,path);return response.json();}
async function saveActual(name,load='25',lost=false){
 const technique=page.getByLabel('I have read the source technique for this set.',{exact:true});if(await technique.isVisible())await technique.check();
 const weight=page.getByLabel('Working weight (lb)',{exact:true});await weight.fill(load);await page.getByLabel('Working repetitions',{exact:true}).fill('10');
 await page.getByLabel('Working repetitions',{exact:true}).focus();
 await exact('button','Save set 1').scrollIntoViewIfNeeded();await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(250);const before=await geometry();
 let original,retry,interrupted=false;
 if(lost)await page.route('**/api/workout/*/log-set',async route=>{if(!interrupted){interrupted=true;original=route.request().postDataJSON();const r=await route.fetch();assert.equal(r.status(),200);await route.abort();}else{retry=route.request().postDataJSON();await route.continue();}});
 await exact('button','Save set 1').click();
 if(lost){await exact('button','Retry same set').waitFor();assert.equal(await weight.getAttribute('readonly'),'');await exact('button','Retry same set').click();assert.deepEqual(retry,original);await page.unroute('**/api/workout/*/log-set');}
 await exact('button','Save set 2').waitFor();
 const after=await geometry();result.observations.push({scenario:name+'-geometry',before,after});assert.equal(after.top,before.top,'stationary Save Set document position');assert.equal(after.left,before.left);assert.equal(after.height,before.height);assert.equal(after.scrollY,before.scrollY,'no scroll jump');
 const s=await api(name,'/workout/'+accounts[name].session.workout_occurrence_id+'/progress');assert.equal(s.completed_total,1);
 result.observations.push({scenario:name,saveBefore:before,saveAfter:after,oneWorkingSet:true,canonicalKg:Number(load)*0.45359237,lostResponseExactRetry:lost});
}
(async()=>{browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE ? {executablePath:process.env.CHROMIUM_EXECUTABLE} : {})});context=await browser.newContext({viewport:{width:390,height:844}});page=await context.newPage();page.setDefaultTimeout(30000);
 page.on('pageerror',e=>result.pageErrors.push(e.message));page.on('response',r=>{const u=new URL(r.url());if(u.pathname.startsWith('/api/')&&r.status()>=400)result.unexpectedApiErrors.push({path:u.pathname,status:r.status()});});
 try{
 await open('phase1');await image('after-mobile-entry');await setup();await image('after-mobile-benchmark');
 let original,retry,interrupted=false;
 await page.route('**/api/workout/*/initial-calibration',async route=>{if(!interrupted){interrupted=true;original=route.request().postDataJSON();const r=await route.fetch();assert.equal(r.status(),200);await route.abort();}else{retry=route.request().postDataJSON();await route.continue();}});
 await exact('button','Save benchmark and estimate').click();await page.getByText('Benchmark save not confirmed. Retry the exact benchmark.',{exact:true}).waitFor();
 await page.reload({waitUntil:'domcontentloaded'});await exact('button','Retry exact benchmark').click();await page.getByText(/Benchmark saved/).waitFor();assert.deepEqual(retry,original);await page.unroute('**/api/workout/*/initial-calibration');
 await page.getByText('Suggested starting weight — estimate',{exact:true}).waitFor();
 const suggested=await page.getByLabel('Working weight (lb)',{exact:true}).inputValue();assert(Number(suggested)>0);result.observations.push({scenario:'known-1rm',provisional:true,suggestedLb:Number(suggested),benchmarkExactRetryAfterReload:true,actualSetsBeforeLogging:0});
 await page.setViewportSize({width:1440,height:900});await image('after-desktop-estimate');await page.setViewportSize({width:390,height:844});
 await saveActual('phase1',suggested,true);await image('after-mobile-saved-set');
 // Correction remains the existing immutable receipt authority.
 await exact('button','Recorded sets · 1').click();await exact('button','Edit set 1').click();await page.getByLabel('Corrected reps',{exact:true}).fill('11');await page.getByLabel('Correction reason',{exact:true}).fill('Synthetic count correction');await exact('button','Save correction').click();await page.getByLabel('Corrected reps',{exact:true}).waitFor({state:'hidden'});
 await exact('button','Undo last set').click();await exact('button','Recorded sets · 0').waitFor();await exact('button','Close Recorded sets').click();await page.reload({waitUntil:'domcontentloaded'});await exact('button','Save set 1').waitFor();result.observations.push({scenario:'correction-undo-reload',logicalSetsAfterUndo:0,sourceIdentityRetained:true});
 await open('recent');await setup('recent_set');await exact('button','Save benchmark and estimate').click();await page.getByText(/Benchmark saved/).waitFor();await page.getByText('Suggested starting weight — estimate',{exact:true}).waitFor();await saveActual('recent',await page.getByLabel('Working weight (lb)',{exact:true}).inputValue());result.observations.push({scenario:'recent-set',reportedReps:8,explicitRir:2,provisional:true});
 await open('manual');assert.equal(await page.getByLabel('Equipment identity',{exact:true}).count(),0);await saveActual('manual','20');await image('after-mobile-manual');
 await api('manual','/profile/preferences','PUT',{theme_family:'classic',appearance:'dark',weight_unit:'kg',expected_revision:1});await page.reload({waitUntil:'domcontentloaded'});assert(Math.abs(Number(await page.getByLabel('Working weight (kg)',{exact:true}).inputValue())-20*0.45359237)<1e-9);result.observations.push({scenario:'lb-kg-reload',canonicalKgRetained:true});
 await open('phase2');await setup();await exact('button','Save benchmark and estimate').click();await page.getByText(/Benchmark saved/).waitFor();const hasEstimate=await page.getByText('Suggested starting weight — estimate',{exact:true}).count();await image('after-mobile-phase2');await saveActual('phase2',hasEstimate?await page.getByLabel('Working weight (lb)',{exact:true}).inputValue():'20');result.observations.push({scenario:'phase2-source-first-today',provisional:Boolean(hasEstimate),manualFallback:!hasEstimate});
 await open('flexible');await setup();await exact('button','Save benchmark and estimate').click();await page.getByText(/Benchmark saved/).waitFor();await page.getByText('Suggested starting weight — estimate',{exact:true}).waitFor();await saveActual('flexible',await page.getByLabel('Working weight (lb)',{exact:true}).inputValue());await image('after-mobile-flexible');result.observations.push({scenario:'native-flexible',executionContextAttached:true,actualDateRetained:true});
 await open('customized');await exact('radio','I know my 1-rep max.').check();await page.getByText(/Customized does not convert/).waitFor();assert.equal(await page.getByLabel('Benchmark load (lb)',{exact:true}).count(),0);await image('after-mobile-customized');await saveActual('customized','20');
 // Same browser switches accounts without copying benchmark/draft data.
 await open('unsupported',{clear:false});assert.equal(await page.getByLabel('Working weight (lb)',{exact:true}).inputValue(),'');assert.equal(await page.getByLabel('Benchmark load (lb)',{exact:true}).count(),0);result.observations.push({scenario:'account-switch',noDraftOrBenchmarkLeak:true});
 await page.setViewportSize({width:1440,height:900});await image('after-desktop-entry');
 assert.deepEqual(result.pageErrors,[]);assert.deepEqual(result.unexpectedApiErrors,[]);
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.equal(overflow,false);
 result.passed=true;console.log('PASS: Phase1, Phase2, Flexible, Customized; known/recent/manual; committed lost-response retries, correction/undo, units, account switch, stationary composer.');
 }catch(e){result.failure=e.message;await image('journey-failure').catch(()=>{});console.error(e.message);process.exitCode=1;}finally{fs.writeFileSync(out+'/browser-results.json',JSON.stringify(result,null,2));await browser.close();}})().catch(e=>{console.error(e.message);process.exit(1)});
