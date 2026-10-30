import React from 'react';
import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import { SavedSetup } from '@/components/saved-setup';
import type { Profile } from '@/lib/api';
test('saved Flexible setup keeps expected frequency separate and routes to its own training',()=>{
 render(<SavedSetup unit="lb" profile={{name:'Synthetic',age:34,weight:80,schedule_mode:'flexible',days_available:null,expected_sessions_per_week:2,selected_program_id:'pure_bodybuilding_phase_1_full_body',setup_status:'established'} as Profile}/>);
 expect(screen.getByText('2 expected sessions · dates optional')).toBeInTheDocument();
 expect(screen.getByRole('link',{name:'Continue Flexible training'})).toHaveAttribute('href','/today');
 expect(screen.queryByRole('link',{name:'Continue to program & dates'})).not.toBeInTheDocument();
});
