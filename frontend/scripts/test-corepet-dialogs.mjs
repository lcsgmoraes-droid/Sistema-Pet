import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

const srcRoot = path.resolve(import.meta.dirname, "../src");
const supportedExtensions = new Set([".js", ".jsx", ".ts", ".tsx"]);
const nativeDialogNames = new Set(["confirm", "prompt"]);
const corePetDialogNames = new Set(["confirmarCorePet", "perguntarCorePet"]);
const errors = [];
let corePetDialogCalls = 0;

function listSourceFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolutePath = path.join(directory, entry.name);
    if (entry.isDirectory()) return listSourceFiles(absolutePath);
    return supportedExtensions.has(path.extname(entry.name)) ? [absolutePath] : [];
  });
}

function getScriptKind(filePath) {
  if (filePath.endsWith(".tsx")) return ts.ScriptKind.TSX;
  if (filePath.endsWith(".ts")) return ts.ScriptKind.TS;
  if (filePath.endsWith(".jsx")) return ts.ScriptKind.JSX;
  return ts.ScriptKind.JS;
}

function getCalledName(expression) {
  if (ts.isIdentifier(expression)) return expression.text;
  if (ts.isPropertyAccessExpression(expression)) return expression.name.text;
  return null;
}

listSourceFiles(srcRoot).forEach((filePath) => {
  const source = fs.readFileSync(filePath, "utf8");
  const sourceFile = ts.createSourceFile(
    filePath,
    source,
    ts.ScriptTarget.Latest,
    true,
    getScriptKind(filePath),
  );

  function report(node, message) {
    const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile));
    errors.push(`${path.relative(srcRoot, filePath)}:${line + 1} ${message}`);
  }

  function visit(node) {
    if (ts.isCallExpression(node)) {
      const calledName = getCalledName(node.expression);
      const objectName = ts.isPropertyAccessExpression(node.expression)
        ? node.expression.expression.getText(sourceFile)
        : null;

      if (
        nativeDialogNames.has(calledName) &&
        (!objectName || objectName === "window" || objectName === "globalThis")
      ) {
        report(node, `usa dialogo nativo ${calledName}`);
      }

      if (corePetDialogNames.has(calledName)) {
        corePetDialogCalls += 1;
        if (!ts.isAwaitExpression(node.parent)) {
          report(node, `${calledName} precisa ser aguardado com await`);
        }
      }
    }

    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
});

assert.equal(errors.length, 0, errors.join("\n"));
assert.ok(corePetDialogCalls > 0, "nenhum dialogo visual do CorePet foi encontrado");

console.log(`OK: ${corePetDialogCalls} dialogos CorePet validados, sem confirm/prompt nativo.`);
