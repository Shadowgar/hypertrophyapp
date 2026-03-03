import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import SettingsPage from "@/app/settings/page";

beforeEach(() => {
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("Settings page shows selected program and saves changes", async () => {
  const profile = { selected_program_id: "full_body_v1", training_location: "gym", equipment_profile: ["dumbbell"], days_available: 5 };
  const programs = [{ id: "full_body_v1", name: "Full Body V1" }, { id: "upper_lower", name: "Upper/Lower" }];

  // @ts-ignore
  global.fetch.mockImplementation((input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/profile") && (!init || init.method === "GET")) {
      return Promise.resolve(new Response(JSON.stringify(profile), { status: 200 }));
    }
    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(new Response(JSON.stringify(programs), { status: 200 }));
    }
    if (url.endsWith("/profile") && init && init.method === "POST") {
      // echo back posted payload merged
      return Promise.resolve(new Response(JSON.stringify({ ...profile, ...(init.body ? JSON.parse(init.body as string) : {}) }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<SettingsPage />);

  await waitFor(() => {
    expect(screen.getByLabelText(/Settings program selector/i)).toBeInTheDocument();
  });

  // change program
  const select = screen.getByLabelText(/Settings program selector/i);
  fireEvent.change(select, { target: { value: "upper_lower" } });

  const save = screen.getByRole("button", { name: /Save Program/i });
  fireEvent.click(save);

  await waitFor(() => {
    expect(screen.getByText(/Saved/)).toBeInTheDocument();
  });
});
