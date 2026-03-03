import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import WeekPage from "@/app/week/page";

beforeEach(() => {
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("Week page sends template_id when override selected", async () => {
  const programs = [{ id: "full_body_v1", name: "Full Body V1" }, { id: "upper_lower", name: "Upper/Lower" }];

  // @ts-ignore
  global.fetch.mockImplementation((input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(new Response(JSON.stringify(programs), { status: 200 }));
    }
    if (url.endsWith("/plan/generate-week") && init && init.method === "POST") {
      return Promise.resolve(new Response(JSON.stringify({ ok: true, received: init.body ? JSON.parse(init.body as string) : {} }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<WeekPage />);

  await waitFor(() => expect(screen.getByLabelText(/Program override/i)).toBeInTheDocument());

  const select = screen.getByLabelText(/Program override/i);
  fireEvent.change(select, { target: { value: "upper_lower" } });

  const btn = screen.getByRole("button", { name: /Generate Week/i });
  fireEvent.click(btn);

  await waitFor(() => expect(screen.getByText(/received/)).toBeInTheDocument());
});
