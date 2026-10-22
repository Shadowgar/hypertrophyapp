import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { useAtlasSet } from "@/components/use-atlas-set";
beforeEach(() => localStorage.clear());
const props = {
  scope: "synthetic-account/occurrence",
  exerciseId: "cross-body",
  completed: 0,
  total: 3,
  unit: "lb" as const,
  prefillKg: 20,
  repRange: [12, 12] as [number, number],
  receipts: [],
};
test("unknown save freezes exact attempt, retries it, and retains weight for next set", async () => {
  const submit = vi
    .fn()
    .mockRejectedValueOnce(new Error("reply lost"))
    .mockResolvedValue(undefined);
  const { result } = renderHook(() => useAtlasSet({ ...props, submit }));
  act(() => {
    result.current.edit("weight", "40");
    result.current.edit("reps", "12");
    result.current.edit("rpe", "8");
  });
  await act(() => result.current.save());
  expect(result.current.phase).toBe("uncertain");
  act(() => result.current.edit("weight", "90"));
  expect(result.current.draft.weight).toBe("40");
  await act(() => result.current.save());
  expect(submit.mock.calls[0]).toEqual(submit.mock.calls[1]);
  expect(submit.mock.calls[0][1]).toMatchObject({
    canonicalWeight: 40 * 0.45359237,
    rpe: 8,
    actual_rir: null,
  });
  expect(result.current.draft.reps).toBe("");
  expect(result.current.draft.weight).toBe("40");
  expect(result.current.phase).toBe("saved");
});
test("interruption restores immutable pending values and original unit", async () => {
  const submit = vi.fn().mockRejectedValue(new Error("offline"));
  const first = renderHook(() => useAtlasSet({ ...props, submit }));
  act(() => first.result.current.edit("weight", "45"));
  await act(() => first.result.current.save());
  first.unmount();
  const next = renderHook(() => useAtlasSet({ ...props, unit: "kg", submit }));
  expect(next.result.current.draft.unit).toBe("lb");
  expect(next.result.current.draft.weight).toBe("45");
  expect(next.result.current.phase).toBe("uncertain");
});
test("zero reps and both effort scales cannot be submitted", async () => {
  const submit = vi.fn();
  const { result } = renderHook(() => useAtlasSet({ ...props, submit }));
  act(() => result.current.edit("reps", ""));
  await act(() => result.current.save());
  expect(submit).not.toHaveBeenCalled();
  act(() => {
    result.current.edit("reps", "12");
    result.current.edit("rpe", "8");
    result.current.edit("rir", "2");
  });
  await act(() => result.current.save());
  expect(submit).not.toHaveBeenCalled();
});
test("an unattempted draft converts when account units change", () => {
  const submit = vi.fn();
  const { result, rerender } = renderHook(
    ({ unit }: { unit: "kg" | "lb" }) =>
      useAtlasSet({ ...props, unit, submit }),
    { initialProps: { unit: "lb" } },
  );
  act(() => result.current.edit("weight", "40"));
  rerender({ unit: "kg" });
  expect(result.current.draft.unit).toBe("kg");
  expect(Number(result.current.draft.weight)).toBeCloseTo(18.1436948);
});
test("a matching confirmed receipt acknowledges the restored command before undo and reuse", async () => {
  const { pendingCommandKey, retainLogPayload, pendingLogPayload } =
    await import("@/lib/workout-identity");
  const submit = vi.fn().mockRejectedValue(new Error("reply lost"));
  const first = renderHook(() => useAtlasSet({ ...props, submit }));
  await act(() => first.result.current.save());
  const attempt = first.result.current.draft.attempt!;
  const key = pendingCommandKey(props.scope, props.exerciseId, "work:1");
  retainLogPayload(key, { command_id: attempt.command, weight: 20 });
  first.unmount();
  const next = renderHook(() =>
    useAtlasSet({
      ...props,
      completed: 1,
      receipts: [{ set_index: 1, command_id: attempt.command } as any],
      submit,
    }),
  );
  expect(next.result.current.locked).toBe(false);
  expect(next.result.current.draft.reps).toBe("");
  expect(pendingLogPayload(key)).toBeNull();
});

test("confirmed undo removes the stale saved message", async () => {
  const submit = vi.fn().mockResolvedValue(undefined);
  const { result, rerender } = renderHook(
    ({ completed }) => useAtlasSet({ ...props, completed, submit }),
    { initialProps: { completed: 0 } },
  );
  await act(() => result.current.save());
  rerender({ completed: 1 });
  expect(result.current.message).toContain("Set 1 saved");
  rerender({ completed: 0 });
  expect(result.current.message).not.toContain("saved");
  expect(result.current.confirmed).toBe(0);
});

test("a definitive logical-set conflict retires the rejected attempt and requires refreshed receipts", async () => {
  const { ApiError } = await import("@/lib/api");
  const { pendingCommandKey, retainLogPayload, pendingLogPayload } =
    await import("@/lib/workout-identity");
  const key = pendingCommandKey(props.scope, props.exerciseId, "work:1");
  const submit = vi.fn(async () => {
    retainLogPayload(key, { weight: 20 });
    throw new ApiError(
      "Logical working set already logged; undo before starting a new attempt",
      409,
    );
  });
  const { result } = renderHook(() => useAtlasSet({ ...props, submit }));
  await act(() => result.current.save());
  expect(result.current.phase).toBe("conflict");
  expect(result.current.locked).toBe(true);
  expect(pendingLogPayload(key)).toBeNull();
  await act(() => result.current.save());
  expect(submit).toHaveBeenCalledTimes(1);
});

test("late authoritative receipts reconcile an uncertain draft and clear per-set observations", async () => {
  const { pendingCommandKey, retainLogPayload, pendingLogPayload } =
    await import("@/lib/workout-identity");
  const submit = vi.fn().mockRejectedValue(new Error("reply lost"));
  const { result, rerender } = renderHook(
    ({ receipts }: { receipts: any[] }) =>
      useAtlasSet({ ...props, receipts, submit }),
    { initialProps: { receipts: [] as any[] } },
  );
  act(() => {
    result.current.edit("quality", "poor");
    result.current.edit("pain", "yes");
  });
  await act(() => result.current.save());
  const attempt = result.current.draft.attempt!;
  const key = pendingCommandKey(props.scope, props.exerciseId, "work:1");
  retainLogPayload(key, { command_id: attempt.command });
  rerender({ receipts: [{ set_index: 1, command_id: attempt.command }] });
  await waitFor(() => expect(result.current.locked).toBe(false));
  expect(result.current.draft).toMatchObject({
    reps: "",
    rpe: "",
    rir: "",
    quality: "unknown",
    pain: "unknown",
  });
  expect(result.current.phase).toBe("saved");
  expect(pendingLogPayload(key)).toBeNull();
});
