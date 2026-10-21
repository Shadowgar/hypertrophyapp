import React from 'react';
import {act,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,test,expect,vi} from 'vitest';
import {AppearanceProvider,useAppearance} from '@/components/appearance-provider';
import {setAuthToken,clearAuthToken} from '@/lib/api';
const token=(sub:string)=>`a.${btoa(JSON.stringify({sub}))}.c`;
function View(){const p=useAppearance();return <p>{p.preferences.theme_family}/{p.preferences.appearance}/{p.preferences.weight_unit}</p>;}
beforeEach(()=>{vi.stubGlobal('matchMedia',vi.fn(()=>({matches:false,addEventListener:vi.fn(),removeEventListener:vi.fn()})));});
test('a late old-account response cannot change the next account or signed-out appearance',async()=>{
 let oldResolve:(value:Response)=>void=()=>{};
 vi.stubGlobal('fetch',vi.fn((_url,init)=>init.headers.get('Authorization').includes(token('first'))?new Promise<Response>(resolve=>{oldResolve=resolve;}):Promise.resolve(Response.json({theme_family:'charcoal',appearance:'system',weight_unit:'kg',revision:1}))));
 setAuthToken(token('first'));render(<AppearanceProvider><View/></AppearanceProvider>);
 act(()=>setAuthToken(token('second')));
 await screen.findByText('charcoal/system/kg');
 await act(async()=>oldResolve(Response.json({theme_family:'graphite',appearance:'light',weight_unit:'lb',revision:4})));
 expect(screen.getByText('charcoal/system/kg')).toBeInTheDocument();
 expect(document.documentElement.dataset.appearance).toBe('light');
 act(()=>clearAuthToken());await screen.findByText('classic/dark/lb');
 await waitFor(()=>expect(document.documentElement.dataset.appearance).toBe('dark'));
});
