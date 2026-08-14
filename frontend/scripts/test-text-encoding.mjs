import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const sourceRoot = path.join(process.cwd(), "src");
const extensions = new Set([".css", ".html", ".js", ".jsx", ".mjs", ".ts", ".tsx"]);
const allowRecoveryLiterals = new Set([
  "components/produtos/produtosUtils.js",
  "pages/categorias-financeiras/categoriasFinanceirasConstants.js",
  "pages/categorias-financeiras/categoriasFinanceirasUtils.js",
  "pages/ecommerce/ecommerceMvpUtils.js",
]);
const brokenEncoding =
  /Ã[\u0080-\u00bfƒŠŒŽšœžŸ]|ð[\u0080-\u00bfƒŠŒŽšœžŸ]|â[€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ]|�|\p{L}\?{2,}\p{L}|["'`]\?{2,}/u;

function listFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) return listFiles(absolute);
    return extensions.has(path.extname(entry.name)) ? [absolute] : [];
  });
}

const failures = [];
for (const absolute of listFiles(sourceRoot)) {
  const relative = path.relative(sourceRoot, absolute).replaceAll("\\", "/");
  if (allowRecoveryLiterals.has(relative) || relative.endsWith(".test.mjs")) continue;

  fs.readFileSync(absolute, "utf8")
    .split(/\r?\n/)
    .forEach((line, index) => {
      if (brokenEncoding.test(line)) failures.push(`${relative}:${index + 1}`);
    });
}

if (failures.length > 0) {
  throw new Error(`Textos com codificação suspeita:\n${failures.join("\n")}`);
}

console.log("Text encoding contract OK");
