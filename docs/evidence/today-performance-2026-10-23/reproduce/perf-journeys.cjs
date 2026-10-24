const {chromium}=require('/home/rocco/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const fs=require('fs'),assert=require('assert/strict');
const accounts=JSON.parse(fs.readFileSync('.qualification/browser-accounts.json','utf8'));
const out='docs/evidence/today-performance-2026-10-23/journeys';
const result={environment:'isolated localhost3020 -> localhost8020 -> disposable PostgreSQL',viewports:[{width:390,height:844},{width:1440,height:900}],observations:[],errors:[],consoleErrors:[],consoleLocations:[],apiFailures:[],resourceFailures:[]};
(async()=>{
const browser=await chromium.launch({headless:true,executablePath:'/home/rocco/.cache/ms-playwright/chromium-1208/chrome-linux/chrome',args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:390,height:844}});const page=await context.newPage();
page.on('pageerror',e=>result.errors.push(e.message));
page.on('console',m=>{if(m.type()==='error'){result.consoleErrors.push(m.text());result.consoleLocations.push({message:m.text(),url:m.location().url})}});
page.on('response',r=>{if(r.status()>=400)result.resourceFailures.push({path:new URL(r.url()).pathname,status:r.status(),type:r.request().resourceType()});if(r.url().includes('/api/')&&r.status()>=400)result.apiFailures.push({path:new URL(r.url()).pathname,status:r.status()})});
async function open(account){
 await page.goto('http://127.0.0.1:3020');
 await page.evaluate(token=>{localStorage.clear();localStorage.setItem('hypertrophy_token',token)},account.token);
 await page.goto('http://127.0.0.1:3020/today',{waitUntil:'domcontentloaded'});
 await page.getByRole('button',{name:'Skip',exact:true}).waitFor({timeout:10000}).catch(()=>{});
 if(await page.getByRole('button',{name:'Skip',exact:true}).isVisible()) await page.getByRole('button',{name:'Skip',exact:true}).click();
 await page.getByText('Cross-Body Lat Pull-Around',{exact:true}).first().click();
 await page.getByRole('region',{name:'Working set entry'}).waitFor();
}
async function setup(){
 await page.getByRole('button',{name:/^(Set up|Why\?)$/}).click();
 await page.getByLabel('Starting-load path').selectOption('known_1rm');
 await page.getByLabel('Benchmark load',{exact:true}).fill('100');
 await page.getByRole('combobox',{name:/^Benchmark unit/}).selectOption('lb');
 await page.getByLabel('Observed date',{exact:true}).fill(new Date().toISOString().slice(0,10));
 await page.getByRole('combobox',{name:/^Benchmark load basis/}).selectOption('machine_stack');
 await page.getByLabel('Equipment identity',{exact:true}).fill('synthetic-cable-A-left-full-ROM');
 await page.getByLabel('Setup details',{exact:true}).fill('Left side full ROM, single handle, pulley 8');
 await page.getByRole('combobox',{name:/^Available load format/}).selectOption('grid');
 await page.getByLabel('Minimum available load',{exact:true}).fill('5');
 await page.getByLabel('Available increment',{exact:true}).fill('2.5');
 await page.getByLabel('Maximum available load',{exact:true}).fill('100');
 await page.getByLabel(/^I confirm this benchmark/).check();
}
async function image(name){await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:`${out}/${name}.png`,fullPage:true});}
async function geometry(){return page.evaluate(()=>{const r=s=>{const b=document.querySelector(s).getBoundingClientRect();return{x:b.x,y:b.y,width:b.width,height:b.height}};return{weight:r('[aria-label="Working weight (lb)"]'),reps:r('[aria-label="Working repetitions"]'),save:r('.atlas-save'),scrollY:window.scrollY}})}
async function api(account,path){const r=await context.request.get('http://127.0.0.1:3020/api'+path,{headers:{Authorization:'Bearer '+account.token}});assert.equal(r.status(),200);return r.json()}
try{
 await open(accounts.eligible);await setup();
 let lostBody, retryBody, lost=false;
 await page.route('**/api/workout/*/initial-calibration',async route=>{
  const body=route.request().postDataJSON();
  if(!lost){lost=true;lostBody=body;const response=await route.fetch();assert.equal(response.status(),200);await route.abort('failed');}
  else{retryBody=body;await route.continue();}
 });
 await page.getByRole('button',{name:'Save benchmark and estimate',exact:true}).click();
 await page.getByText('Benchmark save not confirmed. Retry the exact benchmark.',{exact:true}).waitFor();
 await image('mobile-benchmark-uncertain');
 await page.getByRole('button',{name:'Close Starting load',exact:true}).click();
 await page.reload({waitUntil:'domcontentloaded'});
 await page.getByRole('region',{name:'Working set entry'}).waitFor();
 await page.getByRole('button',{name:/^(Set up|Why\?)$/}).click();
 await page.getByRole('button',{name:'Retry exact benchmark',exact:true}).click();
 await page.getByText('Benchmark saved. Review the current load guidance; no working set was recorded.',{exact:true}).waitFor();
 assert.deepEqual(retryBody,lostBody);await page.unroute('**/api/workout/*/initial-calibration');
 await page.getByRole('button',{name:'Close Starting load',exact:true}).click();
 await page.getByText('Suggested starting weight — estimate',{exact:true}).waitFor();
 assert.equal(await page.getByLabel('Working weight (lb)',{exact:true}).inputValue(),'65');
 await image('mobile-estimate-before-save');
 await page.setViewportSize({width:1440,height:900});await image('desktop-estimate-before-save');
 result.observations.push({scenario:'A',benchmark:'100 lb known1RM',estimate:'65 lb',lostResponse:'server committed; exact command/body retried after close+reload',workingReceipts:0});
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('button',{name:/^Warm-up ·/}).click();
 assert.equal(Number(await page.getByLabel('Warm-up 1 load (lb)',{exact:true}).inputValue()),37.5);
 await page.getByLabel('Warm-up 1 reps',{exact:true}).fill('8');
 await page.getByRole('button',{name:'Log warm-up 1',exact:true}).click();
 await page.getByRole('button',{name:'Warm-up · 1 recorded',exact:true}).waitFor();
 await image('mobile-source-warmup');
 await page.getByRole('button',{name:'Close Warm-up',exact:true}).click();
 await page.getByLabel('Working repetitions',{exact:true}).fill('11');
 await page.getByRole('button',{name:/^Effort: not recorded/}).click();
 await page.getByLabel('Actual RPE (0–10, optional)',{exact:true}).fill('7.5');
 await page.getByRole('button',{name:'Done',exact:true}).click();
 await page.evaluate(()=>window.scrollTo(0,0));
 await page.getByLabel('Working repetitions',{exact:true}).focus();
 const beforeMobile=await geometry();
 await image('mobile-actual-before-save');
 await page.getByRole('button',{name:'Save set 1',exact:true}).click();
 await page.getByRole('button',{name:'Save set 2',exact:true}).waitFor();
 await page.getByRole('timer').waitFor();
 const afterMobile=await geometry();
 assert.deepEqual(afterMobile,beforeMobile,'mobile composer and scroll remain stationary after first save');
 assert.equal(await page.getByLabel('Working weight (lb)',{exact:true}).inputValue(),'65');
 assert.equal(await page.getByText('Suggested starting weight — estimate',{exact:true}).count(),0);
 await image('mobile-first-saved-rest');
 result.observations.push({scenario:'D-mobile',before:beforeMobile,after:afterMobile,load:'65 lb retained',rest:true,initialEstimateRetired:true});
 await page.setViewportSize({width:1440,height:900});
 await page.getByLabel('Working repetitions',{exact:true}).fill('11');
 await page.getByRole('button',{name:/^Effort: not recorded/}).click();
 await page.getByLabel('Actual RPE (0–10, optional)',{exact:true}).fill('7.5');
 await page.getByRole('button',{name:'Done',exact:true}).click();
 await page.evaluate(()=>window.scrollTo(0,0));
 const beforeDesktop=await geometry();
 let lostSet, retriedSet, setInterrupted=false;
 await page.route('**/api/workout/*/log-set',async route=>{
  if(!setInterrupted){setInterrupted=true;lostSet=route.request().postDataJSON();const response=await route.fetch();assert.equal(response.status(),200);await route.abort('failed');}
  else{retriedSet=route.request().postDataJSON();await route.continue();}
 });
 await page.getByRole('button',{name:'Save set 2',exact:true}).click();
 await page.getByRole('button',{name:'Retry same set',exact:true}).waitFor();
 const uncertainDesktop=await geometry();assert.deepEqual(uncertainDesktop,beforeDesktop);
 assert(await page.getByLabel('Working weight (lb)',{exact:true}).getAttribute('readonly')!==null);
 await image('desktop-set-uncertain');
 await page.getByRole('button',{name:'Retry same set',exact:true}).click();
 await page.getByRole('button',{name:'Save set 3',exact:true}).waitFor();
 assert.deepEqual(retriedSet,lostSet);
 const afterDesktop=await geometry();assert.deepEqual(afterDesktop,beforeDesktop);
 await image('desktop-second-saved-rest');
 await page.unroute('**/api/workout/*/log-set');
 result.observations.push({scenario:'D-desktop',before:beforeDesktop,uncertain:uncertainDesktop,after:afterDesktop,exactSetCommandRetry:true,source:lostSet.exercise_occurrence_id,weightKg:lostSet.weight});
 await page.reload({waitUntil:'domcontentloaded'});
 await page.getByRole('button',{name:'Save set 3',exact:true}).waitFor();
 assert.equal(await page.getByLabel('Working weight (lb)',{exact:true}).inputValue(),'65');
 await page.getByRole('button',{name:'Recorded sets · 2',exact:true}).click();
 await page.getByRole('button',{name:'Edit set 1',exact:true}).click();
 await page.getByLabel('Corrected reps',{exact:true}).fill('12');
 await page.getByLabel('Correction reason',{exact:true}).fill('Synthetic count correction');
 let lostCorrection,retriedCorrection,correctionInterrupted=false;
 await page.route('**/api/workout/set/*/correct',async route=>{
  if(!correctionInterrupted){correctionInterrupted=true;lostCorrection={url:route.request().url(),body:route.request().postDataJSON()};const response=await route.fetch();assert.equal(response.status(),200);await route.abort('failed');}
  else{retriedCorrection={url:route.request().url(),body:route.request().postDataJSON()};await route.continue();}
 });
 await page.getByRole('button',{name:'Save correction',exact:true}).click();
 await page.getByRole('button',{name:'Retry exact correction',exact:true}).waitFor();
 assert(await page.getByRole('button',{name:'Edit set 2',exact:true}).isDisabled());
 await image('desktop-correction-uncertain');
 await page.getByRole('button',{name:'Close Recorded sets',exact:true}).click();
 await page.reload({waitUntil:'domcontentloaded'});
 await page.getByRole('button',{name:'Recorded sets · 2',exact:true}).click();
 await page.getByRole('button',{name:'Retry exact correction',exact:true}).click();
 await page.getByRole('button',{name:'Retry exact correction',exact:true}).waitFor({state:'detached'});
 assert.deepEqual(retriedCorrection,lostCorrection);
 await page.unroute('**/api/workout/set/*/correct');
 await image('desktop-corrected-records');
 await page.getByRole('button',{name:'Undo last set',exact:true}).click();
 await page.getByText('Last set undone. The original record remains in History.',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Close Recorded sets',exact:true}).click();
 await page.reload({waitUntil:'domcontentloaded'});
 await page.getByRole('button',{name:'Save set 2',exact:true}).waitFor();
 assert.equal(await page.getByLabel('Working weight (lb)',{exact:true}).inputValue(),'65');
 await image('desktop-after-undo-reload');
 result.observations.push({scenario:'correction-and-undo',lostResponse:true,otherReceiptLocked:true,closeReloadExactRetry:true,afterUndoCompleted:1,load:'65 lb retained'});
 await page.getByRole('link',{name:'History',exact:true}).click();
 await page.getByRole('heading',{name:/History/}).first().waitFor();
 await page.waitForTimeout(1200);await image('desktop-history');
 await page.setViewportSize({width:390,height:844});await image('mobile-history');
 await open(accounts.unsupported);await setup();
 await page.getByRole('button',{name:'Save benchmark and estimate',exact:true}).click();
 await page.getByText('Benchmark saved. Review the current load guidance; no working set was recorded.',{exact:true}).waitFor();
 const unsupportedText=await page.getByRole('dialog',{name:'Starting load',exact:true}).innerText();
 assert.match(unsupportedText,/source|target|ordinary|rep/i);assert.equal(await page.getByText('Suggested starting weight — estimate',{exact:true}).count(),0);
 await image('mobile-unsupported-explanation');
 await page.getByRole('button',{name:'Close Starting load',exact:true}).click();
 await page.getByLabel('Working weight (lb)',{exact:true}).fill('55');
 await page.getByLabel('Working repetitions',{exact:true}).fill('10');
 assert.equal(await page.getByRole('button',{name:'Save set 1',exact:true}).getAttribute('aria-disabled'),'false');
 await image('mobile-unsupported-manual');
 await page.setViewportSize({width:1440,height:900});await image('desktop-unsupported-manual');
 await page.getByRole('button',{name:'Set up',exact:true}).click();await image('desktop-unsupported-explanation');
 result.observations.push({scenario:'B',explanation:unsupportedText.split('Starting-load path')[0],manualLoad:'55 lb',manualReps:10,saveEnabled:true});
 await page.setViewportSize({width:390,height:844});await open(accounts.history);
 assert.equal(await page.getByLabel('Working weight (lb)',{exact:true}).inputValue(),'88.2');
 assert.equal(await page.getByText('Suggested starting weight — estimate',{exact:true}).count(),0);
 await image('mobile-history-precedence');
 await page.setViewportSize({width:1440,height:900});await image('desktop-history-precedence');
 await page.getByRole('button',{name:'Why?',exact:true}).click();await image('desktop-history-precedence-details');
 result.observations.push({scenario:'C',reportedBenchmark:'100 lb',qualifiedHistory:'40 kg displayed88.2 lb',historyWins:true});
 assert.deepEqual(result.errors,[]);assert.deepEqual(result.apiFailures,[]);assert.deepEqual(result.resourceFailures.filter(r=>!(r.status===404&&['/favicon.ico','/programs'].includes(r.path))),[]);assert.deepEqual(result.consoleLocations.filter(m=>!(m.message.includes('net::ERR_FAILED')&&m.url&&/^\/api\/workout\/(?:[^/]+\/(?:log-set|initial-calibration)|set\/[^/]+\/correct)$/.test(new URL(m.url).pathname))&&!(m.message.includes('status of 404')&&m.url&&['/favicon.ico','/programs'].includes(new URL(m.url).pathname))),[]);result.consoleQualification='Inherited favicon and Programs-prefetch 404s retained explicitly; injected response-loss ERR_FAILED expected; no API/chunk/unhandled page errors';
 result.passed=true;result.applicationRevision='912e7e928960069316e81f01a1df08001b0f2a53';
 fs.writeFileSync(out+'/browser-journeys.json',JSON.stringify(result,null,2));
 console.log('PASS: A/B/C/D, mobile+desktop, lost benchmark/set/correction responses, stationary composer, undo/reload/history');
}catch(e){result.failure=e.message;await page.screenshot({path:'.qualification/journey-failure.png',fullPage:true});console.error(e.stack);process.exitCode=1;}
finally{fs.writeFileSync('.qualification/journey-current.json',JSON.stringify(result,null,2));await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)});
