import "@testing-library/jest-dom/vitest";
import React from "react";

// Ensure React is globally available for older compiled components expecting a global `React`.
(globalThis as any).React = React;
