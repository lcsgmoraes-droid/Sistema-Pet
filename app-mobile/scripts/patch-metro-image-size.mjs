import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// Metro 0.84 passes file paths to image-size, but image-size 2.x accepts bytes.
// Keep the patched image-size release and adapt Metro's build-time call.
const mobileRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const metroRoot = path.join(mobileRoot, "node_modules", "metro");
const assetsPath = path.join(metroRoot, "src", "Assets.js");
const imageSizePath = path.join(
  mobileRoot,
  "node_modules",
  "image-size",
  "package.json",
);

const original =
  "const dimensions = isImage ? (0, _imageSize.default)(isImageInput) : null;";
const patched =
  'const dimensions = isImage ? (0, _imageSize.default)(typeof isImageInput === "string" ? _fs.default.readFileSync(isImageInput) : isImageInput) : null;';

const metroVersion = JSON.parse(
  readFileSync(path.join(metroRoot, "package.json"), "utf8"),
).version;
const imageSizeVersion = JSON.parse(
  readFileSync(imageSizePath, "utf8"),
).version;
if (metroVersion !== "0.84.4" || imageSizeVersion !== "2.0.3") {
  throw new Error(
    "Metro ou image-size mudou; revisar a compatibilidade antes de instalar.",
  );
}

const source = readFileSync(assetsPath, "utf8");
if (source.includes(patched)) {
  console.log("Compatibilidade Metro/image-size ja aplicada.");
} else if (source.split(original).length === 2) {
  writeFileSync(assetsPath, source.replace(original, patched));
  console.log("Compatibilidade Metro/image-size aplicada.");
} else {
  throw new Error(
    "Metro Assets.js mudou; revisar a compatibilidade antes de instalar.",
  );
}
