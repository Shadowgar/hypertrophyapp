// Repeatable PR133 UI regression. All API traffic is synthetic and intercepted;
// the caller supplies Playwright and a dedicated loopback Next.js dev server.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {chromium} = require('playwright');
const base = new URL(process.env.WORKOUTAPP_TEST_BASE || 'http://127.0.0.1:18136');
assert.equal(base.hostname, '127.0.0.1');
assert.equal(base.port, '18136', 'Dedicated disposable browser port only');
const token = `header.${Buffer.from(JSON.stringify({sub:'synthetic-pr133-review'})).toString('base64url')}.signature`;
const program = 'pure_bodybuilding_phase_1_full_body';
const reservation = 'synthetic-next-week-reservation';
const session = {session_id:'native-a',title:'Native source A',exercises:[{id:'press',name:'Source Press',sets:3}]};
const finishedSets = {known:true,required:3,completed:3,complete:true,missing:[]};
const ready = {mode:'flexible',state:'active',action:'finish',sequence_id:'seq-review',revision:4,
  occurrence_id:'occ-review',local_day:'2026-11-02',timezone:'America/New_York',digest:'reviewed-finish',
  execution_context:null,session,coverage:finishedSets};

(async()=>{
  const browser=await chromium.launch({headless:true});
  const results=[];
  try {
    for (const viewport of [{width:1440,height:900},{width:390,height:844}]) {
      for (const scenario of ['next-week-switch','paused-finish']) {
        const context=await browser.newContext({viewport,timezoneId:'America/New_York'});
        try {
          await context.addInitScript(value=>localStorage.setItem('hypertrophy_token',value),token);
          const writes=[],errors=[];
          let advanced=false;
          await context.route('**/*',async route=>{
            const url=new URL(route.request().url());
            if(url.origin!==base.origin)return route.abort();
            if(!url.pathname.startsWith('/api/'))return route.continue();
            const path=url.pathname.slice(4),method=route.request().method();
            const body=route.request().postDataJSON();
            if(method==='POST')writes.push({path,body});
            // A paused occurrence has no runnable Today context. Preserve this
            // real API boundary instead of returning a malformed workout.
            if(path==='/workout/today')return route.fulfill({status:409,json:{detail:'Resume the paused occurrence before logging performance'}});
            let data={};
            if(path==='/profile/preferences')data={theme_family:'classic',appearance:'dark',weight_unit:'lb',revision:0};
            if(path==='/profile')data={selected_program_id:program,scheduling_timezone:'America/New_York',schedule_mode:scenario==='next-week-switch'?'calendar':'flexible',expected_sessions_per_week:null};
            if(path==='/plan/scheduling-context')data={timezone:'America/New_York',week_start:url.searchParams.get('week_offset')==='1'?'2026-11-02':'2026-10-26',plan:url.searchParams.get('week_offset')==='1'?{plan_id:reservation,program_template_id:program,sessions:[]}:null};
            if(path==='/training/next')data=scenario==='next-week-switch'?{mode:'calendar',action:'none'}:advanced?{...ready,action:'start',source_position:1}:ready;
            if(path==='/training/enroll/preview'){
              assert.equal(body.switch_plan_id,reservation);
              data={digest:'reviewed-switch',program_id:program,session_count:50,total_working_sets:900,first_session:session,legacy_plan_id:reservation,available:true,blockers:[]};
            }
            if(path==='/training/enroll'){
              assert.equal(body.switch_plan_id,reservation);assert.equal(body.confirmed,true);
              data={mode:'flexible',sequence_id:'new-sequence',action:'start'};
            }
            if(path==='/training/seq-review/finish'){
              assert.equal(body.expected_digest,ready.digest);assert.equal(body.confirmed,true);
              advanced=true;data={...ready,action:'start',source_position:1};
            }
            await route.fulfill({json:data});
          });
          const page=await context.newPage();page.setDefaultTimeout(60000);
          page.on('pageerror',error=>errors.push(error.message));
          await page.goto(new URL(scenario==='next-week-switch'?'/training/setup':'/',base).href,{waitUntil:'domcontentloaded'});
          if(scenario==='next-week-switch'){
            await page.getByRole('button',{name:'Preview Switch to Flexible',exact:true}).waitFor();
            assert.equal(await page.getByText(reservation,{exact:true}).count(),1);
            assert.equal(writes.length,0);
            await page.getByRole('button',{name:'Preview Switch to Flexible',exact:true}).click();
            const confirm=page.getByRole('button',{name:'Confirm Flexible enrollment',exact:true});
            await confirm.waitFor();assert.equal(await confirm.isDisabled(),true);
            await page.getByRole('checkbox',{name:/I confirm/}).check();
            await confirm.click();await page.waitForURL('**/today');
            assert.deepEqual(writes.map(item=>item.path),['/training/enroll/preview','/training/enroll']);
          }else{
            const finish=page.getByRole('button',{name:'Finish workout',exact:true});await finish.waitFor();
            assert.equal(await page.getByRole('button',{name:'Resume workout',exact:true}).count(),0);
            assert.equal(await page.getByRole('button',{name:'Pause workout',exact:true}).count(),0);
            assert.equal(writes.length,0);await finish.click();
            await page.getByRole('button',{name:'Confirm finish',exact:true}).click();
            await page.getByText('Finish recorded. The next source workout is available.',{exact:true}).waitFor();
            assert.deepEqual(writes.map(item=>item.path),['/training/seq-review/finish']);
          }
          assert.deepEqual(errors,[]);
          const width=await page.evaluate(()=>({body:document.documentElement.scrollWidth,viewport:innerWidth}));
          assert.ok(width.body<=width.viewport,'Horizontal overflow');
          results.push({scenario,viewport,writes:writes.map(item=>item.path),pageErrors:errors});
        } finally {await context.close();}
      }
    }
    if(process.env.WORKOUTAPP_TEST_ARTIFACTS)fs.writeFileSync(process.env.WORKOUTAPP_TEST_ARTIFACTS,JSON.stringify(results,null,2));
    console.log(JSON.stringify(results,null,2));
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
