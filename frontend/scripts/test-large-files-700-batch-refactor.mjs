import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function exists(relativePath) {
  return fs.existsSync(path.join(root, relativePath));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function lineCount(relativePath) {
  return read(relativePath).split(/\r?\n/).length;
}

const targetFiles = [
  "src/pages/ecommerce/EcommerceAccountPage.jsx",
  "src/pages/BlingFlowMonitor.jsx",
  "src/pages/CentralAjuda.jsx",
];

const extractedFiles = [
  "src/pages/ecommerce/EcommerceAccountProfileForm.jsx",
  "src/pages/ecommerce/EcommerceAccountAuthCards.jsx",
  "src/pages/blingFlowMonitor/blingFlowMonitorUtils.js",
  "src/pages/blingFlowMonitor/BlingFlowMonitorCards.jsx",
  "src/pages/centralAjuda/centralAjudaKnowledge.js",
];

for (const relativePath of extractedFiles) {
  assert(exists(relativePath), `Missing extracted large-file refactor module: ${relativePath}`);
}

for (const relativePath of targetFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 700, `${relativePath} has ${lines} lines; expected <= 700`);
}

for (const relativePath of extractedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 700, `${relativePath} has ${lines} lines; expected <= 700`);
}

const ecommerceAccount = read("src/pages/ecommerce/EcommerceAccountPage.jsx");
assert(
  ecommerceAccount.includes("./EcommerceAccountProfileForm"),
  "EcommerceAccountPage.jsx should delegate the customer profile form",
);
assert(
  ecommerceAccount.includes("./EcommerceAccountAuthCards"),
  "EcommerceAccountPage.jsx should delegate login/register/password cards",
);

const blingMonitor = read("src/pages/BlingFlowMonitor.jsx");
assert(
  blingMonitor.includes("./blingFlowMonitor/blingFlowMonitorUtils"),
  "BlingFlowMonitor.jsx should delegate event formatting helpers",
);
assert(
  blingMonitor.includes("./blingFlowMonitor/BlingFlowMonitorCards"),
  "BlingFlowMonitor.jsx should delegate incident and event cards",
);

const centralAjuda = read("src/pages/CentralAjuda.jsx");
assert(
  centralAjuda.includes("./centralAjuda/centralAjudaKnowledge"),
  "CentralAjuda.jsx should delegate the static knowledge base",
);

console.log("Large files 700 batch refactor contract OK");
