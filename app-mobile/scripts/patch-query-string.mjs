import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

// React Navigation 6 usa query-string CJS; o decoder corrigido e ESM.
// Preservar a API do query-string sem reintroduzir o decoder vulneravel.
const mobileRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const original = "const decodeComponent = require('decode-uri-component');";
const patched =
  "const decodeComponent = require('decode-uri-component').default;";

export function adaptQueryStringSource(source, queryVersion, decoderVersion) {
  if (queryVersion !== "7.1.3" || decoderVersion !== "0.5.1") {
    throw new Error(
      "query-string ou decode-uri-component mudou; revisar a compatibilidade antes de instalar.",
    );
  }
  const originalCount = source.split(original).length - 1;
  const patchedCount = source.split(patched).length - 1;
  if (originalCount === 0 && patchedCount === 1) return source;
  if (originalCount === 1 && patchedCount === 0) {
    return source.replace(original, patched);
  }
  throw new Error(
    "query-string/index.js mudou; revisar a compatibilidade antes de instalar.",
  );
}

export function patchQueryString() {
  const packageVersion = (name) =>
    JSON.parse(
      readFileSync(
        path.join(mobileRoot, "node_modules", name, "package.json"),
        "utf8",
      ),
    ).version;
  const sourcePath = path.join(
    mobileRoot,
    "node_modules/query-string/index.js",
  );
  const source = readFileSync(sourcePath, "utf8");
  const adapted = adaptQueryStringSource(
    source,
    packageVersion("query-string"),
    packageVersion("decode-uri-component"),
  );
  if (adapted !== source) writeFileSync(sourcePath, adapted);
  console.log("Compatibilidade query-string/decode-uri-component verificada.");
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
) {
  patchQueryString();
}
