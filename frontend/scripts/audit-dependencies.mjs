import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const severityOrder = { info: 0, low: 1, moderate: 2, high: 3, critical: 4 };
const minimumSeverity = severityOrder.moderate;
const allowedAdvisories = new Map([
  ["GHSA-QWWW-VCR4-C8H2", "O frontend é uma SPA Vite e não usa o modo RSC/Server Actions afetado."],
]);
const buildOnlyBracesAdvisory = "GHSA-VFJ7-8CJW-P6XM";
const buildOnlyBracesPackages = new Set([
  "braces",
  "chokidar",
  "fast-glob",
  "micromatch",
  "tailwindcss",
]);
const packageManifest = JSON.parse(readFileSync("package.json", "utf8"));
const packageLock = JSON.parse(readFileSync("package-lock.json", "utf8"));
const rscApiPatterns = [
  /\bcreateRequestHandler\b/,
  /\bServerRouter\b/,
  /\bgetRSCStream\b/,
  /\bunstable_[A-Za-z0-9_]*RSC[A-Za-z0-9_]*\b/,
  /\breact-server-dom\b/,
];

function sourceUsesRsc(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (sourceUsesRsc(entryPath)) return true;
      continue;
    }
    if (!/\.(?:js|jsx|mjs|ts|tsx)$/.test(entry.name)) continue;
    const source = readFileSync(entryPath, "utf8");
    if (rscApiPatterns.some((pattern) => pattern.test(source))) return true;
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

const auditResult = runNpmAudit();
if (!auditResult.stdout?.trim()) {
  process.stderr.write(auditResult.stderr || "npm audit não retornou um relatório JSON.\n");
  process.exit(1);
}

let report;
try {
  report = JSON.parse(auditResult.stdout);
} catch (error) {
  process.stderr.write(`Não foi possível interpretar o relatório do npm audit: ${error.message}\n`);
  process.exit(1);
}

const vulnerabilities = report.vulnerabilities || {};
const advisoryCache = new Map();

function advisoryIdsFor(vulnerabilityName, visited = new Set()) {
  if (advisoryCache.has(vulnerabilityName)) {
    return advisoryCache.get(vulnerabilityName);
  }
  if (visited.has(vulnerabilityName)) return new Set();
  visited.add(vulnerabilityName);

  const ids = new Set();
  const vulnerability = vulnerabilities[vulnerabilityName];
  for (const via of vulnerability?.via || []) {
    if (typeof via === "string") {
      for (const advisoryId of advisoryIdsFor(via, visited)) ids.add(advisoryId);
      continue;
    }
    const match = String(via?.url || "").match(/GHSA-[A-Za-z0-9-]+/i);
    if (match) ids.add(match[0].toUpperCase());
  }
  advisoryCache.set(vulnerabilityName, ids);
  return ids;
}

const usesRsc = sourceUsesRsc(path.resolve("src"));
const blocked = [];
const ignored = [];

function isBuildOnlyBracesExposure(name, vulnerability, advisoryIds) {
  // A falha exige um padrao de glob controlado pelo atacante. Nesta arvore,
  // braces chega apenas pelo Tailwind 3 usado no build de arquivos do repositorio.
  // Se algum pacote afetado passar a ser dependencia de runtime, a excecao cai.
  if (
    advisoryIds.size !== 1 ||
    !advisoryIds.has(buildOnlyBracesAdvisory) ||
    !buildOnlyBracesPackages.has(name) ||
    !packageManifest.devDependencies?.tailwindcss ||
    packageManifest.dependencies?.tailwindcss
  ) {
    return false;
  }
  return (
    Array.isArray(vulnerability.nodes) &&
    vulnerability.nodes.length > 0 &&
    vulnerability.nodes.every((node) => packageLock.packages?.[node]?.dev === true)
  );
}

for (const [name, vulnerability] of Object.entries(vulnerabilities)) {
  if ((severityOrder[vulnerability.severity] ?? 99) < minimumSeverity) continue;

  const advisoryIds = advisoryIdsFor(name);
  const onlyAllowed =
    advisoryIds.size > 0 &&
    [...advisoryIds].every((advisoryId) => allowedAdvisories.has(advisoryId));

  const rscException = onlyAllowed && !usesRsc;
  const buildOnlyException = isBuildOnlyBracesExposure(name, vulnerability, advisoryIds);

  if (rscException || buildOnlyException) {
    ignored.push({
      name,
      advisoryIds: [...advisoryIds],
      reason: buildOnlyException
        ? "Atinge apenas dependências de desenvolvimento do Tailwind usadas no build com padrões controlados pelo repositório."
        : allowedAdvisories.get([...advisoryIds][0]),
    });
  } else {
    blocked.push({ name, severity: vulnerability.severity, advisoryIds: [...advisoryIds] });
  }
}

for (const item of ignored) {
  for (const advisoryId of item.advisoryIds) {
    console.warn(`Exceção documentada: ${item.name} / ${advisoryId}. ${item.reason}`);
  }
}

if (blocked.length > 0) {
  console.error("Auditoria de dependências bloqueada:");
  for (const item of blocked) {
    console.error(
      `- ${item.name} (${item.severity})${item.advisoryIds.length ? `: ${item.advisoryIds.join(", ")}` : ""}`,
    );
  }
  process.exit(1);
}

console.log(
  "Auditoria de dependências aprovada; nenhuma vulnerabilidade aplicável foi encontrada.",
);
