import "@testing-library/jest-dom/vitest";
import React from "react";
import { beforeEach, vi } from "vitest";

// Ensure React is globally available for older compiled components expecting a global `React`.
(globalThis as any).React = React;

beforeEach(() => {
	globalThis.localStorage?.clear();
});

// jsdom has no native dialog implementation. Disclosure tests exercise open/close;
// the real-browser suite verifies modal focus, Escape and focus restoration.
HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open',''); };
HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); this.dispatchEvent(new Event('close')); };
// jsdom does not lay out or scroll. Browser qualification checks scroll restoration.
window.scrollTo = vi.fn();
