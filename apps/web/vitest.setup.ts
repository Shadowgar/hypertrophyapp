import "@testing-library/jest-dom/vitest";
import React from "react";
import { beforeEach } from "vitest";

// Ensure React is globally available for older compiled components expecting a global `React`.
(globalThis as any).React = React;

beforeEach(() => {
	globalThis.localStorage?.clear();
});
