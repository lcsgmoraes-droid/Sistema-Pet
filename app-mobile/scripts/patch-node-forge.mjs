import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

// Backport de https://github.com/digitalbazaar/forge/pull/1152 (ceba344).
// Remover quando node-forge publicar a correção de CVE-2026-85393.
const mobileRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const packagePath = path.join(
  mobileRoot,
  "node_modules/node-forge/package.json",
);
const rsaPath = path.join(mobileRoot, "node_modules/node-forge/lib/rsa.js");
const lockPath = path.join(mobileRoot, "package-lock.json");
const originalHash =
  "fd4740238145ec26470eb3f06a627c72039538ce1307dbdce40521f94dfd0a50";

const originalBlock = [
  "          // validate DigestInfo structure and element count",
  "          var capture = {};",
  "          var errors = [];",
  "          if(!asn1.validate(obj, digestInfoValidator, capture, errors) ||",
  "            obj.value.length !== 2) {",
].join("\n");

const patchedBlock = [
  "          // validate DigestInfo structure and element counts (outer DigestInfo",
  "          // and nested DigestAlgorithm). asn1.validate ignores extra children,",
  "          // so length must be checked explicitly at each nesting level to",
  "          // prevent low-exponent PKCS#1 v1.5 signature forgery (CVE-2026-85393).",
  "          var capture = {};",
  "          var errors = [];",
  "          if(!asn1.validate(obj, digestInfoValidator, capture, errors) ||",
  "            obj.value.length !== 2 ||",
  "            obj.value[0].value.length !==",
  "              (('parameters' in capture) ? 2 : 1)) {",
].join("\n");

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function expectedDependencyTree() {
  const lock = JSON.parse(readFileSync(lockPath, "utf8"));
  const copies = Object.keys(lock.packages || {}).filter((name) =>
    /(?:^|\/)node_modules\/node-forge$/.test(name),
  );
  const installed = JSON.parse(readFileSync(packagePath, "utf8"));
  return (
    copies.length === 1 &&
    copies[0] === "node_modules/node-forge" &&
    lock.packages[copies[0]].version === "1.4.0" &&
    installed.version === "1.4.0" &&
    installed.main === "lib/index.js"
  );
}

export function isNodeForgePatched() {
  try {
    if (!expectedDependencyTree()) return false;
    const source = readFileSync(rsaPath, "utf8");
    if (source.split(patchedBlock).length !== 2) return false;
    return sha256(source.replace(patchedBlock, originalBlock)) === originalHash;
  } catch {
    return false;
  }
}

export function patchNodeForge() {
  if (isNodeForgePatched()) return;
  if (!expectedDependencyTree()) {
    throw new Error("node-forge mudou; revisar o backport antes de instalar.");
  }
  const source = readFileSync(rsaPath, "utf8");
  if (
    sha256(source) !== originalHash ||
    source.split(originalBlock).length !== 2
  ) {
    throw new Error("rsa.js não corresponde ao node-forge 1.4.0 esperado.");
  }
  writeFileSync(rsaPath, source.replace(originalBlock, patchedBlock));
  if (!isNodeForgePatched()) {
    throw new Error("Não foi possível verificar o backport de node-forge.");
  }
  console.log(
    "Backport CVE-2026-85393 aplicado e verificado em node-forge 1.4.0.",
  );
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
) {
  patchNodeForge();
}
