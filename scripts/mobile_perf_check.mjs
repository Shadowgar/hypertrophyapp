#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const buildDir = path.join(root, "apps", "web", ".next");
const outputDir = path.join(root, "docs", "validation");
const outputJsonPath = path.join(outputDir, "mobile_perf_metrics.json");
const outputMdPath = path.join(outputDir, "mobile_perf_metrics.md");

const BUDGETS = {
  maxSharedJsKb: 170,
  maxCriticalRouteChunkKb: 35,
  maxCriticalRouteTotalKb: 200,
};

const CRITICAL_ROUTES = [
  { id: "home", candidates: ["/", "/page"] },
  { id: "today", candidates: ["/today", "/today/page"] },
  { id: "week", candidates: ["/week", "/week/page"] },
  { id: "checkin", candidates: ["/checkin", "/checkin/page"] },
  { id: "history", candidates: ["/history", "/history/page"] },
  { id: "guides", candidates: ["/guides", "/guides/page"] },
  { id: "settings", candidates: ["/settings", "/settings/page"] },
];

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

function normalizeAssetPath(assetPath) {
  if (!assetPath) {
    return assetPath;
  }
  if (assetPath.startsWith("/")) {
    return assetPath.slice(1);
  }
  return assetPath;
}

function isJsAsset(assetPath) {
  return assetPath.endsWith(".js") || assetPath.endsWith(".mjs");
}

function statAssetGzipBytes(assetPath) {
  const normalized = normalizeAssetPath(assetPath);
  const fullPath = path.join(buildDir, normalized);
  const content = fs.readFileSync(fullPath);
  return zlib.gzipSync(content, { level: 9 }).byteLength;
}

function kb(bytes) {
  return Number((bytes / 1024).toFixed(2));
}

function sumAssetBytes(assetList) {
  const unique = [...new Set(assetList.map(normalizeAssetPath))].filter(isJsAsset);
  const totalBytes = unique.reduce((acc, asset) => acc + statAssetGzipBytes(asset), 0);
  return { totalBytes, assets: unique };
}

function resolveRouteAssets(appBuildManifest, routeInfo) {
  const pages = appBuildManifest.pages || {};
  for (const candidate of routeInfo.candidates) {
    if (pages[candidate]) {
      return { routeKey: candidate, assets: pages[candidate] };
    }
  }
  return { routeKey: null, assets: [] };
}

function writeReports(metrics) {
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(outputJsonPath, `${JSON.stringify(metrics, null, 2)}\n`, "utf-8");

  const routeRows = metrics.routes.map(
    (route) => `| ${route.id} | ${route.routeKey || "missing"} | ${route.chunkJsKb} | ${route.totalWithSharedKb} |`,
  );

  const lines = [
    "# Mobile Performance Metrics",
    "",
    "This report is generated from `apps/web/.next` build manifests.",
    "",
    "## Summary",
    "",
    `- Shared JS (KB): ${metrics.sharedJsKb}`,
    `- Max critical route chunk JS (KB): ${metrics.maxCriticalRouteChunkJsKb}`,
    `- Max critical route total JS with shared (KB): ${metrics.maxCriticalRouteTotalJsKb}`,
    `- Budget status: ${metrics.passed ? "PASS" : "FAIL"}`,
    "",
    "## Budgets",
    "",
    `- Shared JS <= ${metrics.budgets.maxSharedJsKb} KB`,
    `- Critical route chunk JS <= ${metrics.budgets.maxCriticalRouteChunkKb} KB`,
    `- Critical route total JS with shared <= ${metrics.budgets.maxCriticalRouteTotalKb} KB`,
    "",
    "## Critical Routes",
    "",
    "| Route | Route Key | Chunk JS (KB) | Total JS w/ Shared (KB) |",
    "| --- | --- | ---: | ---: |",
    ...routeRows,
    "",
  ];

  if (metrics.failures.length > 0) {
    const failureRows = metrics.failures.map((failure) => `- ${failure}`);
    lines.push("## Budget Failures", "", ...failureRows, "");
  }

  fs.writeFileSync(outputMdPath, `${lines.join("\n")}\n`, "utf-8");
}

function main() {
  const buildManifestPath = path.join(buildDir, "build-manifest.json");
  const appBuildManifestPath = path.join(buildDir, "app-build-manifest.json");

  if (!fs.existsSync(buildManifestPath) || !fs.existsSync(appBuildManifestPath)) {
    console.error("Next build manifests are missing. Run `npm run build` in apps/web first.");
    process.exit(1);
  }

  const buildManifest = readJson(buildManifestPath);
  const appBuildManifest = readJson(appBuildManifestPath);

  const sharedAssets = [
    ...(buildManifest.rootMainFiles || []),
    ...(buildManifest.pages?.["/_app"] || []),
  ];
  const shared = sumAssetBytes(sharedAssets);
  const sharedAssetSet = new Set(shared.assets);

  const routes = CRITICAL_ROUTES.map((routeInfo) => {
    const resolved = resolveRouteAssets(appBuildManifest, routeInfo);
    const routeExclusiveAssets = resolved.assets
      .map(normalizeAssetPath)
      .filter(isJsAsset)
      .filter((asset) => !sharedAssetSet.has(asset));
    const chunk = sumAssetBytes(routeExclusiveAssets);
    return {
      id: routeInfo.id,
      routeKey: resolved.routeKey,
      chunkJsBytes: chunk.totalBytes,
      chunkJsKb: kb(chunk.totalBytes),
      totalWithSharedBytes: chunk.totalBytes + shared.totalBytes,
      totalWithSharedKb: kb(chunk.totalBytes + shared.totalBytes),
    };
  });

  const maxCriticalRouteChunkJsBytes = routes.reduce((max, route) => Math.max(max, route.chunkJsBytes), 0);
  const maxCriticalRouteTotalJsBytes = routes.reduce((max, route) => Math.max(max, route.totalWithSharedBytes), 0);

  const failures = [];
  if (kb(shared.totalBytes) > BUDGETS.maxSharedJsKb) {
    failures.push(
      `Shared JS ${kb(shared.totalBytes)} KB exceeds budget ${BUDGETS.maxSharedJsKb} KB`,
    );
  }
  if (kb(maxCriticalRouteChunkJsBytes) > BUDGETS.maxCriticalRouteChunkKb) {
    failures.push(
      `Critical route chunk JS ${kb(maxCriticalRouteChunkJsBytes)} KB exceeds budget ${BUDGETS.maxCriticalRouteChunkKb} KB`,
    );
  }
  if (kb(maxCriticalRouteTotalJsBytes) > BUDGETS.maxCriticalRouteTotalKb) {
    failures.push(
      `Critical route total JS ${kb(maxCriticalRouteTotalJsBytes)} KB exceeds budget ${BUDGETS.maxCriticalRouteTotalKb} KB`,
    );
  }

  const metrics = {
    budgets: BUDGETS,
    sharedJsBytes: shared.totalBytes,
    sharedJsKb: kb(shared.totalBytes),
    maxCriticalRouteChunkJsBytes,
    maxCriticalRouteChunkJsKb: kb(maxCriticalRouteChunkJsBytes),
    maxCriticalRouteTotalJsBytes,
    maxCriticalRouteTotalJsKb: kb(maxCriticalRouteTotalJsBytes),
    routes,
    failures,
    passed: failures.length === 0,
  };

  writeReports(metrics);

  console.log("Mobile performance metrics written:");
  console.log(`- ${path.relative(root, outputJsonPath)}`);
  console.log(`- ${path.relative(root, outputMdPath)}`);
  console.log(`Shared JS: ${metrics.sharedJsKb} KB`);
  console.log(`Max critical route chunk JS: ${metrics.maxCriticalRouteChunkJsKb} KB`);
  console.log(`Max critical route total JS: ${metrics.maxCriticalRouteTotalJsKb} KB`);

  if (!metrics.passed) {
    console.error("Budget check failed.");
    process.exit(1);
  }
}

main();
