import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { AccountRecovery } from '@/components/account-recovery';
import { setAuthToken } from '@/lib/api';
beforeEach(() => { localStorage.clear(); setAuthToken('synthetic-session'); vi.stubGlobal('fetch',vi.fn().mockResolvedValue(Response.json({remaining:0,events:[]}))); });
function ready() { return screen.findByRole('button',{name:'Generate recovery codes'}); }
function fill() { fireEvent.change(screen.getByLabelText('Current password'),{target:{value:'Synthetic-password-123'}}); fireEvent.click(screen.getByRole('checkbox')); }
test('password confirmed setup displays ten codes once, never in browser storage',async()=>{
 render(<AccountRecovery />); const button=await ready(); fill();
 const codes=Array.from({length:10},(_,i)=>`synthetic-private-code-${i}`);
 vi.mocked(fetch).mockResolvedValueOnce(Response.json({status:'generated',codes})); fireEvent.click(button);
 await screen.findByText(codes[0]);
 expect(localStorage.getItem('hypertrophy_token')).toBe('synthetic-session');
 expect(JSON.stringify(localStorage)+JSON.stringify(sessionStorage)).not.toContain(codes[0]);
 expect(screen.getByLabelText('Current password')).toHaveValue('');
 fireEvent.click(screen.getByRole('button',{name:'I saved these codes'})); expect(screen.queryByText(codes[0])).not.toBeInTheDocument();
});
test('late generation response cannot expose codes after account change',async()=>{
 render(<AccountRecovery />); const button=await ready(); fill();
 let resolve!:(r:Response)=>void; vi.mocked(fetch).mockReturnValueOnce(new Promise(r=>{resolve=r;})); fireEvent.click(button);
 act(()=>setAuthToken('another-account')); await act(async()=>resolve(Response.json({status:'generated',codes:['must-not-render']})));
 expect(screen.queryByText('must-not-render')).not.toBeInTheDocument();
});
test('security notice is authenticated and can be acknowledged',async()=>{
 vi.mocked(fetch).mockResolvedValueOnce(Response.json({remaining:9,events:[{id:'event',kind:'password_recovered',created_at:'2026-10-31T12:00:00',acknowledged_at:null}]}));
 render(<AccountRecovery />); await screen.findByText('Your password was recovered. Previous sign-ins were invalidated.');
 vi.mocked(fetch).mockResolvedValueOnce(Response.json({status:'acknowledged'})).mockResolvedValue(Response.json({remaining:9,events:[]})); fireEvent.click(screen.getByRole('button',{name:'Acknowledge security notice'}));
 await waitFor(()=>expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/auth/recovery-events/event/acknowledge'),expect.objectContaining({method:'POST'})));
});
