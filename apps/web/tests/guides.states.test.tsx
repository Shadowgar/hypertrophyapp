import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { setAuthToken } from "@/lib/api";
const route = vi.hoisted(() => ({ params: {} as Record<string, string>, search: "" }));
vi.mock("next/navigation", () => ({ useParams: () => route.params, useSearchParams: () => new URLSearchParams(route.search) }));
import GuidesIndex from "@/app/guides/page";
import ProgramIndex from "@/app/guides/[programId]/page";
import ProgramDetail from "@/app/programs/[id]/page";
import PhaseGuide from "@/app/guides/[programId]/phase/[phaseId]/page";
import DayGuide from "@/app/guides/[programId]/day/[dayIndex]/page";
import PhaseDayGuide from "@/app/guides/[programId]/phase/[phaseId]/day/[dayIndex]/page";
import ExerciseGuide from "@/app/guides/[programId]/exercise/[exerciseId]/page";
const program = { id: "phase_one", name: "Source program one", description: "Original source description", split: "full_body", days_supported: [3], days: [{ day_index: 1, day_name: "Source session", exercise_count: 1, first_exercise_id: "press" }] };
const exercise = { program_id: "phase_one", exercise: { id: "source_slot", primary_exercise_id: "press", name: "Source exercise", notes: "Synthetic technique instructions.\nPreserve this second line.", video_youtube_url: "https://www.youtube.com/watch?v=synthetic" } };
const day = { program_id: "phase_one", day_index: 1, day_name: "Source session", exercises: [exercise.exercise] };
function response(value: unknown, status = 200) { return new Response(JSON.stringify(value), { status }); }
function deferred() { let resolve!: (value: Response) => void; const promise = new Promise<Response>((done) => { resolve = done; }); return { promise, resolve }; }
beforeEach(() => {
  localStorage.clear(); route.params = { programId: "phase_one", id: "phase_one", phaseId: "main", dayIndex: "1", exerciseId: "press" }; route.search = ""; vi.stubGlobal("fetch", vi.fn());
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
test("library loading and failure cannot masquerade as empty or Online; retry keeps focus", async () => {
  const pending = deferred(); vi.mocked(fetch).mockReturnValueOnce(pending.promise).mockResolvedValueOnce(response([program])); render(<GuidesIndex />);
  expect(screen.getByRole("status")).toHaveTextContent(/loading/i); expect(screen.queryByText(/no programs|online/i)).not.toBeInTheDocument();
  await act(async () => { pending.resolve(response({ detail: "private diagnostic" }, 503)); });
  expect(screen.getByRole("status")).toHaveTextContent(/could not load/i); expect(screen.queryByText(/no programs|private diagnostic/i)).not.toBeInTheDocument();
  const retry = screen.getByRole("button", { name: /retry/i }); retry.focus(); fireEvent.click(retry);
  expect(await screen.findByRole("link", { name: /open guide for source program one/i })).toHaveAttribute("href", "/guides/phase_one");
  expect(screen.getByRole("button", { name: /refresh/i })).toHaveFocus();
  expect(vi.mocked(fetch).mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});
test("acknowledged empty library has its own state and refresh", async () => {
  vi.mocked(fetch).mockResolvedValue(response([])); render(<GuidesIndex />);
  expect(await screen.findByText(/no program guides/i)).toBeVisible(); expect(screen.getByRole("button", { name: /refresh/i })).toBeVisible();
});
const detailRoutes = [["program", ProgramIndex, program], ["catalog detail", ProgramDetail, program], ["phase", PhaseGuide, program], ["legacy day", DayGuide, day], ["phase day", PhaseDayGuide, day], ["exercise", ExerciseGuide, exercise]] as const;
for (const [label, Page, payload] of detailRoutes) {
  test(`${label} distinguishes unavailable reads from not found and recovers on retry`, async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response({ detail: "internal source path" }, 500)).mockResolvedValueOnce(response(payload)); render(<Page />);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/could not load/i));
    expect(screen.queryByText(/not found|no exercise details|internal source path/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    await waitFor(() => expect(screen.getByRole("status")).not.toHaveTextContent(/could not load|loading/i));
    expect(screen.getByRole("navigation", { name: /breadcrumb/i })).toBeVisible();
  });
}
test("actual not-found response does not claim a transport failure", async () => {
  vi.mocked(fetch).mockResolvedValue(response({ detail: "hidden path" }, 404)); render(<ProgramDetail />);
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/not found/i)); expect(screen.queryByText(/could not load|hidden path/i)).not.toBeInTheDocument();
});
test("new route immediately retires visible detail and rejects an older late response", async () => {
  const oldRead = deferred(); const nextRead = deferred(); vi.mocked(fetch).mockResolvedValueOnce(response(program)).mockReturnValueOnce(oldRead.promise).mockReturnValueOnce(nextRead.promise);
  const view = render(<ProgramDetail />); await screen.findByRole("heading", { name: program.name });
  route.params = { id: "phase_two" }; view.rerender(<ProgramDetail />); expect(screen.queryByRole("heading", { name: program.name })).not.toBeInTheDocument();
  route.params = { id: "phase_three" }; view.rerender(<ProgramDetail />);
  await act(async () => { nextRead.resolve(response({ ...program, id: "phase_three", name: "Current program" })); }); await screen.findByRole("heading", { name: "Current program" });
  await act(async () => { oldRead.resolve(response({ ...program, id: "phase_two", name: "Retired program" })); }); expect(screen.queryByRole("heading", { name: "Retired program" })).not.toBeInTheDocument();
});
test("account changes retire in-flight guide lists and old 401 cannot clear the new token", async () => {
  localStorage.setItem("hypertrophy_token", "account-a"); const oldRead = deferred();
  vi.mocked(fetch).mockReturnValueOnce(oldRead.promise).mockResolvedValueOnce(response([{ ...program, name: "Current account catalog" }])); render(<GuidesIndex />);
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1)); await act(async () => { setAuthToken("account-b"); }); await screen.findByRole("link", { name: /current account catalog/i });
  await act(async () => { oldRead.resolve(response({ detail: "expired old account" }, 401)); }); expect(localStorage.getItem("hypertrophy_token")).toBe("account-b"); expect(screen.getByRole("link", { name: /current account catalog/i })).toBeVisible();
});
test("silent storage account change during a read rejects the prior reply and reloads", async () => {
  localStorage.setItem("hypertrophy_token", "account-a"); const oldRead = deferred(); vi.mocked(fetch).mockReturnValueOnce(oldRead.promise).mockResolvedValueOnce(response([{ ...program, name: "New catalog" }]));
  render(<GuidesIndex />); await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1)); localStorage.setItem("hypertrophy_token", "account-b");
  await act(async () => { oldRead.resolve(response([{ ...program, name: "Retired catalog" }])); }); await screen.findByRole("link", { name: /new catalog/i }); expect(screen.queryByRole("link", { name: /retired catalog/i })).not.toBeInTheDocument();
});
test("exercise reads source notes and video while technical record starts collapsed", async () => {
  route.search = "day=1&phase=main"; vi.mocked(fetch).mockResolvedValue(response(exercise)); render(<ExerciseGuide />); await screen.findByRole("heading", { name: exercise.exercise.name });
  expect(within(screen.getByRole("region", { name: "Technique & setup" })).getByText(/Synthetic technique instructions/)).toBeVisible(); expect(screen.getByRole("link", { name: /watch.*video/i })).toHaveAttribute("href", exercise.exercise.video_youtube_url);
  const disclosure = screen.getByText("Source & technical details").closest("details"); expect(disclosure).not.toHaveAttribute("open"); expect(within(disclosure!).getByText(/source_slot/)).not.toBeVisible();
  expect(screen.getByRole("link", { name: "Day 1" })).toHaveAttribute("href", "/guides/phase_one/phase/main/day/1"); expect(screen.getByRole("link", { name: /return to workout/i })).toHaveAttribute("href", "/today");
});
test("missing exercise instructions stay unknown and unsafe video URLs are not actionable", async () => {
  route.search = "day=javascript:bad&phase=other"; vi.mocked(fetch).mockResolvedValue(response({ ...exercise, exercise: { ...exercise.exercise, notes: null, video_youtube_url: "javascript:alert(1)" } })); render(<ExerciseGuide />);
  expect(await screen.findByText(/no technique instructions/i)).toBeVisible(); expect(screen.queryByRole("link", { name: /watch.*video|^day /i })).not.toBeInTheDocument(); expect(screen.queryByText(/3 sets|target RPE/i)).not.toBeInTheDocument();
});
test("empty day exposes no invented exercise and unknown phase never replays Main Phase", async () => {
  vi.mocked(fetch).mockResolvedValue(response({ ...day, exercises: [] })); const view = render(<DayGuide />); expect(await screen.findByText(/no exercises.*guide/i)).toBeVisible();
  view.unmount(); vi.mocked(fetch).mockClear(); route.params = { programId: "phase_one", phaseId: "invented" }; render(<PhaseGuide />);
  expect(screen.getByRole("status")).toHaveTextContent(/not found/i); expect(fetch).not.toHaveBeenCalled();
});
