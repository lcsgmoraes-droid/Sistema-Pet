import { readdirSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { pathToFileURL } from "node:url";

const severityOrder = { info: 0, low: 1, moderate: 2, high: 3, critical: 4 };
const minimumSeverity = severityOrder.moderate;
const allowedAdvisories = new Map([
  [
    "GHSA-W3RX-R6R6-PGPR",
    "image-size e transitivo do Metro e usado apenas na construcao do bundle; nao ha versao corrigida disponivel.",
  ],
  [
    "GHSA-5P2G-FCMC-QVQQ",
    "image-size e transitivo do Metro e usado apenas na construcao do bundle; nao ha versao corrigida disponivel.",
  ],
]);
const imageSizeImportPatterns = [
  /\bfrom\s+["']image-size(?:\/[^"']*)?["']/,
  /\brequire\(\s*["']image-size(?:\/[^"']*)?["']\s*\)/,
  /\bimport\(\s*["']image-size(?:\/[^"']*)?["']\s*\)/,
];

function sourceUsesImageSize(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (sourceUsesImageSize(entryPath)) return true;
      continue;
    }
    if (!/\.(?:js|jsx|mjs|ts|tsx)$/.test(entry.name)) continue;
    const source = readFileSync(entryPath, "utf8");
    if (imageSizeImportPatterns.some((pattern) => pattern.test(source))) return true;
  }
  return false;
}

function applicationUsesImageSize() {
  const sourceDirectory = path.resolve("src");
  if (sourceUsesImageSize(sourceDirectory)) return true;

  for (const entryFile of ["App.tsx", "index.js"]) {
    const source = readFileSync(path.resolve(entryFile), "utf8");
    if (imageSizeImportPatterns.some((pattern) => pattern.test(source))) return true;
  }
  return false;
}

function runNpmAudit() {
  const options = {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 20 * 1024 * 1024,
  };
  if (process.platform === "win32") {
    return spawnSync(
      process.env.ComSpec || "cmd.exe",
      ["/d", "/s", "/c", "npm audit --json"],
      options,
    );
  }
  return spawnSync("npm", ["audit", "--json"], options);
}

function advisoryIdsByVulnerability(vulnerabilities) {
  const idsByName = new Map();
  for (const [name, vulnerability] of Object.entries(vulnerabilities)) {
    const ids = new Set();
    for (const via of vulnerability?.via || []) {
      if (typeof via === "string") continue;
      const match = String(via?.url || "").match(/GHSA-[A-Za-z0-9-]+/i);
      if (match) ids.add(match[0].toUpperCase());
    }
    idsByName.set(name, ids);
  }

  // O relatorio do npm contem ciclos entre metro, metro-config e
  // metro-transform-worker. Propagar ate estabilizar evita que a ordem dos
  // pacotes esconda o advisory raiz do image-size.
  let changed = true;
  while (changed) {
    changed = false;
    for (const [name, vulnerability] of Object.entries(vulnerabilities)) {
      const ids = idsByName.get(name);
      for (const via of vulnerability?.via || []) {
        if (typeof via !== "string") continue;
        for (const advisoryId of idsByName.get(via) || []) {
          if (ids.has(advisoryId)) continue;
          ids.add(advisoryId);
          changed = true;
        }
      }
    }
  }
  return idsByName;
}

export function evaluateAudit(report, { sourceImportsImageSize = false } = {}) {
  const vulnerabilities = report?.vulnerabilities || {};
  const advisoryIdsByName = advisoryIdsByVulnerability(vulnerabilities);
  const blocked = [];
  const ignored = [];

  for (const [name, vulnerability] of Object.entries(vulnerabilities)) {
    if ((severityOrder[vulnerability.severity] ?? 99) < minimumSeverity) continue;

    const advisoryIds = advisoryIdsByName.get(name) || new Set();
    const onlyAllowed =
      advisoryIds.size > 0 &&
      [...advisoryIds].every((advisoryId) => allowedAdvisories.has(advisoryId));

    if (onlyAllowed && !sourceImportsImageSize) {
      ignored.push({ name, advisoryIds: [...advisoryIds] });
    } else {
      blocked.push({
        name,
        severity: vulnerability.severity,
        advisoryIds: [...advisoryIds],
      });
    }
  }

  return { blocked, ignored };
}

function main() {
  const auditResult = runNpmAudit();
  if (!auditResult.stdout?.trim()) {
    process.stderr.write(
      auditResult.stderr || "npm audit nao retornou um relatorio JSON.\n",
    );
    process.exit(1);
  }

  let report;
  try {
    report = JSON.parse(auditResult.stdout);
  } catch (error) {
    process.stderr.write(
      `Nao foi possivel interpretar o relatorio do npm audit: ${error.message}\n`,
    );
    process.exit(1);
  }

  const { blocked, ignored } = evaluateAudit(report, {
    sourceImportsImageSize: applicationUsesImageSize(),
  });

  const ignoredAdvisories = new Set(
    ignored.flatMap((item) => item.advisoryIds),
  );
  for (const advisoryId of ignoredAdvisories) {
    console.warn(
      `Excecao documentada: image-size / ${advisoryId}. ${allowedAdvisories.get(advisoryId)}`,
    );
  }

  if (blocked.length > 0) {
    console.error("Auditoria de dependencias mobile bloqueada:");
    for (const item of blocked) {
      console.error(
        `- ${item.name} (${item.severity})${item.advisoryIds.length ? `: ${item.advisoryIds.join(", ")}` : ""}`,
      );
    }
    process.exit(1);
  }

  console.log(
    "Auditoria mobile aprovada; nenhuma vulnerabilidade aplicavel foi encontrada.",
  );
}

const isMain =
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isMain) main();
