import React from 'react';
import {fireEvent,render,screen} from '@testing-library/react';
import {beforeEach,expect,test,vi} from 'vitest';
import SettingsPage from '@/app/settings/page';
vi.mock('next/navigation',()=>({useRouter:()=>({push:vi.fn(),replace:vi.fn()})}));
const profile={email:'synthetic@example.invalid',name:'Synthetic',age:34,weight:80,split_preference:'full_body',schedule_mode:'flexible',expected_sessions_per_week:2,days_available:null,effective_days_available:null,selected_program_id:'pure_bodybuilding_phase_1_full_body',effective_program_id:'pure_bodybuilding_phase_1_full_body',training_location:'gym',equipment_profile:['dumbbell']};
beforeEach(()=>localStorage.setItem('hypertrophy_token',`header.${btoa(JSON.stringify({sub:'flex-settings'}))}.signature`));
function serve(){const writes:Array<{path:string;payload:Record<string,unknown>}>=[];vi.stubGlobal('fetch',vi.fn(async(input,init)=>{
 const path=String(input);
 if(path.endsWith('/profile/equipment')){const payload=JSON.parse(String(init.body));writes.push({path,payload});return Response.json({...profile,...payload});}
 if(path.endsWith('/profile'))return Response.json(profile);
 return Response.json({detail:'Optional capability unavailable'},{status:403});
}));return writes;}
test('ordinary Flexible equipment edits preserve null calendar days and the separate advisory expectation',async()=>{
 const writes=serve();render(<SettingsPage/>);
 await screen.findByText('2 expected sessions per week · dates optional');
 fireEvent.change(screen.getByLabelText('Training location'),{target:{value:'home'}});
 fireEvent.click(screen.getByRole('button',{name:'Save training settings'}));
 await screen.findByText('Training settings saved.');
 expect(writes).toHaveLength(1);expect(writes[0].payload).toEqual({training_location:'home',equipment_profile:['dumbbell']});
 expect(screen.getByText('2 expected sessions per week · dates optional')).toBeInTheDocument();
});
test('Flexible settings cannot expose legacy frequency or program-apply controls',async()=>{
 serve();render(<SettingsPage/>);await screen.findByText('Full Body Phase 1');
 expect(screen.queryByRole('heading',{name:'Advanced training controls'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Get Recommendation'})).not.toBeInTheDocument();
 expect(screen.getByRole('link',{name:'Manage Flexible training'})).toHaveAttribute('href','/today');
});
