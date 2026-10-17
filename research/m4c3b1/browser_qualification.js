// Invoke this async function with a Playwright page against the explicit loopback
// synthetic demo. It creates only disposable candidates; no real app is used.
async (page) => {
  const origin='http://127.0.0.1:8766';
  const results={};
  const check=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(origin+'/customized/lifecycle');
  await page.locator('#credential').fill('synthetic-alice-test-only');
  await page.getByRole('button',{name:'Preview candidate',exact:true}).click();
  await page.locator('#notice').filter({hasText:'review_required'}).waitFor();
  check(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)),'Desktop overflow');
  await page.getByRole('button',{name:'Review consent terms',exact:true}).click();
  await page.locator('#consent').waitFor({state:'visible'});
  const acknowledgements=await page.locator('#acknowledgements input').count();
  check(acknowledgements===20,'Exact twelve work changes and six dose gaps absent');
  for(const box of await page.locator('#acknowledgements input').all())await box.check();
  await page.locator('#agree').check();
  await page.getByRole('button',{name:'Accept inactive candidate',exact:true}).click();
  await page.locator('#notice').filter({hasText:'accepted_candidate'}).waitFor();
  await page.getByRole('button',{name:'Show activation blockers',exact:true}).click();
  await page.locator('#notice').filter({hasText:'activation_blocked'}).waitFor();
  results.acceptance=await page.locator('#notice').innerText();
  await page.getByRole('button',{name:'Withdraw acceptance',exact:true}).click();
  await page.locator('#notice').filter({hasText:'withdrawn'}).waitFor();
  check(await page.locator('#withdraw').isDisabled(),'Withdraw was re-enabled without consent');
  await page.setViewportSize({width:390,height:844});
  await page.locator('#candidate').selectOption('longer-current');
  await page.locator('#cap').fill('90');
  await page.getByRole('button',{name:'Save new revision',exact:true}).click();
  await page.locator('#notice').filter({hasText:'plan version 2'}).waitFor();
  results.revision=await page.locator('#notice').innerText();
  await page.getByRole('button',{name:'Decline candidate',exact:true}).click();
  await page.locator('#notice').filter({hasText:'declined'}).waitFor();
  check(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)),'Mobile overflow');
  results.decline=await page.locator('#notice').innerText();
  await page.reload();
  await page.locator('#credential').fill('synthetic-alice-test-only');
  await page.getByRole('button',{name:'Preview candidate',exact:true}).click();
  await page.locator('#notice').filter({hasText:'review_required'}).waitFor();
  await page.getByText('Explicit profile and selected local dates',{exact:true}).click();
  await page.locator('#profile').fill('{invalid json');
  await page.getByRole('button',{name:'Save new revision',exact:true}).click();
  check(await page.locator('#prepare').isDisabled(),'Failed dirty revision re-enabled old candidate consent');
  results.dirty_revision_stays_blocked=true;
  // Hold each real response while switching account. Old responses must not
  // restore data, consent challenges or proposal controls into the new account.
  for(const stage of ['create','render','challenge','accept']) {
    await page.reload();
    await page.locator('#credential').fill('synthetic-alice-test-only');
    if(['challenge','accept'].includes(stage)) {
      await page.getByRole('button',{name:'Preview candidate',exact:true}).click();
      await page.locator('#notice').filter({hasText:'review_required'}).waitFor();
    }
    if(stage==='accept') {
      await page.getByRole('button',{name:'Review consent terms',exact:true}).click();
      await page.locator('#consent').waitFor({state:'visible'});
      for(const box of await page.locator('#acknowledgements input').all())await box.check();
      await page.locator('#agree').check();
    }
    let release,seen;
    const gate=new Promise(r=>release=r),captured=new Promise(r=>seen=r);
    const pattern=stage==='create'?'**/customized/proposals':'**/customized/proposals/*/'+stage;
    await page.route(pattern,async route=>{const response=await route.fetch();seen();await gate;await route.fulfill({response});});
    const button=stage==='challenge'?'Review consent terms':stage==='accept'?'Accept inactive candidate':'Preview candidate';
    await page.getByRole('button',{name:button,exact:true}).click();
    await captured;
    await page.locator('#credential').fill('synthetic-bob-test-only');
    release();
    await page.waitForResponse(r=>stage==='create'?r.url()===origin+'/customized/proposals':r.url().endsWith('/'+stage));
    await page.waitForTimeout(100);
    check((await page.locator('#preview').innerText())==='','Old '+stage+' preview restored after account switch');
    check(await page.locator('#consent').isHidden(),'Old '+stage+' consent restored');
    check(await page.locator('#revise').isDisabled(),'Old '+stage+' controls restored');
    await page.unroute(pattern);
    results['discarded_'+stage]=true;
  }
  return results;
}
