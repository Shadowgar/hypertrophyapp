// Synthetic disposable services only. Never record screenshots/traces while codes
// are visible; plaintext exists only in this process/browser's transient memory.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium, webkit, devices } = require('playwright');
const base = process.env.FERRAVIS_RECOVERY_TEST_BASE;
const version = process.env.FERRAVIS_EXPECTED_VERSION;
const out = process.env.FERRAVIS_TEST_ARTIFACTS;
assert.equal(base, 'http://127.0.0.1:55441');
assert.equal(process.env.FERRAVIS_DISPOSABLE, '1');
assert.match(version || '', /^[a-f0-9]{40}$/);
assert.ok(out); fs.mkdirSync(out, { recursive: true });
let stage='preflight';
(async () => {
 for (const path of ['/version', '/api/health']) assert.equal((await (await fetch(base+path)).json()).version, version);
 const results=[];
 const engines=['chromium','chromium-mobile',...(process.env.FERRAVIS_WEBKIT==='1'?['webkit']:[])];
 for (const engine of engines) {
  stage=engine+' launch';
  const browser=await (engine==='webkit'?webkit:chromium).launch({headless:true});
  try {
   const context=await browser.newContext(engine==='webkit'?devices['iPhone 13']:engine==='chromium-mobile'?{viewport:{width:390,height:844},isMobile:true,hasTouch:true}:{viewport:{width:1440,height:900}});
   await context.route('**/*',r=>new URL(r.request().url()).origin===base?r.continue():r.abort());
   const email=`synthetic-recovery-${engine}-${Date.now()}@example.com`;
   const original='Synthetic-only-Q98!'; const updated='New-synthetic-only-Q98!';
   const registration=await context.request.post(base+'/api/auth/register',{data:{email,name:'Synthetic',password:original}});
   assert.equal(registration.status(),200);
   const token=(await registration.json()).access_token;
   const page=await context.newPage(); page.setDefaultTimeout(60000);
   const errors=[]; page.on('pageerror',error=>errors.push({name:error.name,frames:(error.stack||'').split('\n').slice(1,4)}));
   stage=engine+' settings';
   await page.goto(base+'/login');
   await page.evaluate(value=>localStorage.setItem('hypertrophy_token',value),token);
   await page.goto(base+'/settings');
   await page.getByRole('heading',{name:'Password recovery',exact:true}).waitFor();
   await page.getByText('0 unused recovery codes remain.',{exact:true}).waitFor();
   await page.getByLabel('Current password',{exact:true}).fill(original);
   await page.getByRole('checkbox',{name:/I will save the new codes privately/}).check();
   stage=engine+' generation';
   const generating=page.waitForResponse(r=>r.url().endsWith('/auth/recovery-codes')&&r.request().method()==='POST');
   await page.getByRole('button',{name:'Generate recovery codes',exact:true}).click();
   const generated=await generating; assert.equal(generated.status(),200);
   const codes=(await generated.json()).codes; assert.equal(codes.length,10);
   await page.getByRole('heading',{name:'Save these codes now',exact:true}).waitFor();
   assert.equal(await page.locator('#account-recovery li').count(),10);
   assert.equal(await page.evaluate(()=>[...Object.values(localStorage),...Object.values(sessionStorage)].some(v=>v.includes('frc_'))),false);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await page.getByRole('button',{name:'I saved these codes',exact:true}).click();
   assert.equal(await page.locator('#account-recovery li').count(),0);
   // Secret-free screenshot only after dismissal, and no browser trace/video.
   await page.screenshot({path:`${out}/${engine}-settings-hidden.png`,fullPage:true});
   stage=engine+' recovery';
   await page.goto(base+'/reset-password');
   assert.equal(await page.getByLabel('Email',{exact:true}).count(),0);
   await page.getByLabel('Recovery code',{exact:true}).fill(codes[0]);
   await page.getByLabel('New password',{exact:true}).fill(updated);
   await page.getByRole('button',{name:'Save new password',exact:true}).click();
   await page.getByRole('status').filter({hasText:'Password updated.'}).waitFor();
   const stale=await context.request.get(base+'/api/auth/recovery-codes',{headers:{Authorization:`Bearer ${token}`}});
   assert.equal(stale.status(),401);
   stage=engine+' new login';
   await page.goto(base+'/login');
   await page.getByLabel('Email',{exact:true}).fill(email);
   await page.getByLabel('Password',{exact:true}).fill(updated);
   await page.getByRole('button',{name:'Sign in',exact:true}).click();
   await page.waitForURL(url=>!url.pathname.endsWith('/login'));
   await page.goto(base+'/settings');
   await page.getByText('9 unused recovery codes remain.',{exact:true}).waitFor();
   await page.getByText('Your password was recovered. Previous sign-ins were invalidated.',{exact:true}).waitFor();
   const replay=await context.request.post(base+'/api/auth/password-reset/confirm',{data:{token:codes[0],new_password:updated}});
   assert.equal(replay.status(),400);
   stage=engine+' runtime';
   if(errors.length) fs.writeFileSync(out+'/runtime-frames.json',JSON.stringify(errors));
   assert.deepEqual(errors,[]);
   results.push({engine,viewport:engine==='webkit'?'iPhone13-emulated':engine==='chromium-mobile'?'390x844':'1440x900',generated:10,remaining:9,oldSession:401,replay:400,pageErrors:0,emailSent:false});
  } finally { await browser.close(); }
 }
 fs.writeFileSync(out+'/summary.json',JSON.stringify(results,null,2));
 console.log(JSON.stringify(results));
})().catch(()=>{console.error('Isolated recovery browser qualification failed at '+stage+' (no credential output).');process.exitCode=1;});
