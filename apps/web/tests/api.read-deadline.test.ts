import { afterEach, expect, test, vi } from "vitest";
import { api } from "@/lib/api";
afterEach(()=>{vi.useRealTimers();vi.unstubAllGlobals();});

test.each([
  ["workout",()=>api.getTodayWorkout()],
  ["mode",()=>api.getNextTraining()],
  ["date",()=>api.getSchedulingContext("UTC")],
  ["progress",()=>api.getWorkoutProgress("synthetic")],
  ["soreness",()=>api.listSoreness("2026-11-01","2026-11-01")],
] as const)("a stalled %s GET has a bounded failure and abort signal",async(_name,read)=>{
 vi.useFakeTimers();let signal:AbortSignal|null|undefined;let failure:unknown;
 vi.stubGlobal("fetch",vi.fn((_url:RequestInfo|URL,init?:RequestInit)=>{signal=init?.signal;return new Promise(()=>{});}));
 void read().catch(error=>{failure=error;});
 await vi.advanceTimersByTimeAsync(15001);
 expect(failure).toBeInstanceOf(Error);expect(signal?.aborted).toBe(true);expect(vi.getTimerCount()).toBe(0);
});

test("the GET deadline never aborts or retries a pending mutation",async()=>{
 vi.useFakeTimers();let reply!:(r:Response)=>void;let settled=false;
 const fetch=vi.fn((_input:RequestInfo|URL,_init?:RequestInit)=>new Promise<Response>(resolve=>{reply=resolve}));vi.stubGlobal("fetch",fetch);
 const pending=api.createSoreness({entry_date:"2026-11-01",severity_by_muscle:{chest:"none"}}).then(()=>{settled=true});
 await vi.advanceTimersByTimeAsync(30000);expect(settled).toBe(false);expect(fetch).toHaveBeenCalledOnce();
 expect(fetch.mock.calls[0][1]?.signal).toBeUndefined();reply(Response.json({}));await pending;
});
