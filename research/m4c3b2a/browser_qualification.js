// Invoke with a Playwright page and credentials from the explicit disposable demo.
// Tokens are never hardcoded in this committed artifact or obtained over HTTP.
async (page,credentials) => {
  const origin='http://127.0.0.1:8767',results={};
  const check=(value,message)=>{if(!value)throw new Error(message);};
  async function begin(){await page.goto(origin+'/customized/lifecycle');await page.locator('#credential').fill(credentials.alice);await page.getByRole('button',{name:'Preview candidate',exact:true}).click();await page.locator('#notice').filter({hasText:'review_required'}).waitFor();}
  async function prepare(){await page.getByRole('button',{name:'Review consent terms',exact:true}).click();await page.locator('#consent').waitFor({state:'visible'});}
  await page.setViewportSize({width:1440,height:1000});await begin();
  check((await page.locator('.work-difference').count())===12,'Missing specific set differences');
  check((await page.locator('.range-conflict').count())===6,'Missing unapproved range assumptions');
  const comparison=await page.locator('#workload-comparison').innerText();
  check(comparison.includes('33 weekly working sets')&&comparison.includes('45 weekly working sets'),'Workload summary mismatch');
  check(comparison.includes('70.5')&&comparison.includes('59'),'Duration comparison absent');
  await prepare();check((await page.locator('#consent input[type=checkbox]').count())===1,'Routine consent requires more than one checkbox');
  await page.locator('#agree').check();await page.getByRole('button',{name:'Accept inactive candidate',exact:true}).click();
  await page.locator('#notice').filter({hasText:'accepted_candidate'}).waitFor();
  await page.getByRole('button',{name:'Show activation blockers',exact:true}).click();await page.locator('#notice').filter({hasText:'activation_blocked'}).waitFor();
  results.desktop=await page.locator('#notice').innerText();
  check(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)),'Desktop overflow');
  await page.setViewportSize({width:390,height:844});
  await page.locator('#candidate').selectOption('longer-current');await page.locator('#cap').fill('90');
  await page.getByRole('button',{name:'Save new revision',exact:true}).click();await page.locator('#notice').filter({hasText:'plan version 2'}).waitFor();
  check((await page.locator('.work-difference').count())===12,'Reverse comparison lost individual differences');
  check((await page.locator('.range-conflict').count())===6,'Alternative unapproved assumptions hidden');
  await page.getByRole('button',{name:'Decline candidate',exact:true}).click();await page.locator('#notice').filter({hasText:'declined'}).waitFor();
  results.mobile=await page.locator('#notice').innerText();
  check(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)),'Mobile overflow');
  await begin();await page.getByText('Explicit profile and selected local dates',{exact:true}).click();
  await page.locator('#profile').fill('{invalid');await page.getByRole('button',{name:'Save new revision',exact:true}).click();
  check(await page.locator('#prepare').isDisabled(),'Dirty failed revision enabled old consent');results.dirtyBlocked=true;
  for(const stage of ['create','render','challenge','accept']){
    await page.goto(origin+'/customized/lifecycle');await page.locator('#credential').fill(credentials.alice);
    if(['challenge','accept'].includes(stage)){await page.getByRole('button',{name:'Preview candidate',exact:true}).click();await page.locator('#notice').filter({hasText:'review_required'}).waitFor();}
    if(stage==='accept'){await prepare();await page.locator('#agree').check();}
    let release,seen;const gate=new Promise(r=>release=r),captured=new Promise(r=>seen=r);
    const pattern=stage==='create'?'**/customized/proposals':'**/customized/proposals/*/'+stage;
    await page.route(pattern,async route=>{const response=await route.fetch();seen();await gate;await route.fulfill({response});});
    await page.getByRole('button',{name:stage==='challenge'?'Review consent terms':stage==='accept'?'Accept inactive candidate':'Preview candidate',exact:true}).click();
    await captured;await page.locator('#credential').fill(credentials.bob);release();
    await page.waitForResponse(r=>stage==='create'?r.url()===origin+'/customized/proposals':r.url().endsWith('/'+stage));await page.waitForTimeout(100);
    check((await page.locator('#preview').innerText())==='','Prior-account '+stage+' response restored data');
    check(await page.locator('#consent').isHidden(),'Prior-account consent restored');
    await page.unroute(pattern);results['discarded_'+stage]=true;
  }
  return results;
}
