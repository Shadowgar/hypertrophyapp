import React from "react";
import {act,cleanup,fireEvent,render,screen,waitFor} from "@testing-library/react";
import AnalyticsPage from "@/app/analytics/page";
import {setAuthToken} from "@/lib/api";
const saved=vi.hoisted(()=>({weight_unit:"lb" as "kg"|"lb"}));
vi.mock("@/components/appearance-provider",()=>({useAppearance:()=>({preferences:saved})}));
const series={series_id:"press-cable-a",exercise_id:"press",exercise_name:"Cable Press",basis:"machine_stack",equipment_key:"Cable A",unit:"kg",points:[{week_start:"2026-10-12",max_weight:20},{week_start:"2026-10-19",max_weight:22.5}]};
const payload={window:{start_date:"2026-09-01",end_date:"2026-10-21",limit_weeks:8},load_series:[series],load_series_unknown_sets:2,checkins:[],adherence:{average_pct:0},bodyweight_trend:[],body_measurement_trends:[],strength_trends:[],pr_highlights:[],volume_heatmap:{max_volume:0,weeks:[]}};
function deferred(){let resolve!:(r:Response)=>void;const promise=new Promise<Response>(r=>resolve=r);return{promise,resolve};}
afterEach(()=>{cleanup();vi.unstubAllGlobals();saved.weight_unit="lb";});
test("analytics chart and table share unit-aware existing values while a slow timeline remains optional",async()=>{
  const timeline=deferred();vi.stubGlobal("fetch",vi.fn(async(input)=>String(input).includes("/history/analytics")?Response.json(payload):timeline.promise));
  const {rerender}=render(<AnalyticsPage/>);
  expect(await screen.findByRole("img",{name:/Weekly highest working load/})).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button",{name:"Show data table"}));
  expect(screen.getByRole("cell",{name:"44.1 lb"})).toBeInTheDocument();
  expect(screen.getByRole("cell",{name:"49.6 lb"})).toBeInTheDocument();
  saved.weight_unit="kg";rerender(<AnalyticsPage/>);
  expect(screen.getByRole("cell",{name:"20 kg"})).toBeInTheDocument();
  expect(screen.getByRole("cell",{name:"22.5 kg"})).toBeInTheDocument();
  expect(screen.queryByText(/High.Readiness/i)).not.toBeInTheDocument();
});
test("failed analytics is retryable and cannot be presented as empty evidence",async()=>{
  let fail=true;vi.stubGlobal("fetch",vi.fn(async(input)=>String(input).includes("/history/analytics")?(fail?Response.json({}, {status:503}):Response.json({...payload,load_series:[]})):Response.json({entries:[]})));
  render(<AnalyticsPage/>);fireEvent.click(await screen.findByRole("button",{name:"Retry analytics"}));
  expect(screen.queryByText("More training will tell the story")).not.toBeInTheDocument();
  fail=false;await waitFor(()=>expect(screen.getByRole("button",{name:"Retry analytics"})).toBeEnabled());fireEvent.click(screen.getByRole("button",{name:"Retry analytics"}));
  await screen.findByRole("heading",{name:"More training will tell the story"});
});
test("retired account analytics cannot replace the current selected series",async()=>{
  setAuthToken("analytics-a");const old=deferred();vi.stubGlobal("fetch",vi.fn(async(input,init)=>String(input).includes("/history/analytics")?(new Headers(init?.headers).get("Authorization")==="Bearer analytics-a"?old.promise:Response.json(payload)):Response.json({entries:[]})));
  render(<AnalyticsPage/>);act(()=>setAuthToken("analytics-b"));await screen.findByRole("img",{name:/Weekly highest working load/});
  await act(async()=>old.resolve(Response.json({...payload,load_series:[{...series,exercise_name:"Old Account Press"}]})));
  expect(screen.queryByText("Old Account Press")).not.toBeInTheDocument();
});

test("late analytics for an old range cannot overwrite the selected range",async()=>{
  const old=deferred();vi.stubGlobal("fetch",vi.fn(async(input)=>{
    const url=new URL(String(input),"http://analytics.test");
    if(!url.pathname.endsWith("/history/analytics"))return Response.json({entries:[]});
    return url.searchParams.get("limit_weeks")==="8" ? old.promise : Response.json({...payload,window:{...payload.window,limit_weeks:4}});
  }));
  render(<AnalyticsPage/>);fireEvent.change(screen.getByLabelText("Date range"),{target:{value:"4"}});
  await screen.findByRole("img",{name:/Weekly highest working load/});
  await act(async()=>old.resolve(Response.json({...payload,load_series:[{...series,exercise_name:"Old range press"}]})));
  expect(screen.queryByText("Old range press")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Date range")).toHaveValue("4");
});
