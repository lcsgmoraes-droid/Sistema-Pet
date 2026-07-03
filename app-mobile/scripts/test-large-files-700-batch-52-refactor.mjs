import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const files = [
  "src/screens/orders/OrdersScreen.tsx",
  "src/screens/orders/orders/OrdersContent.tsx",
  "src/screens/orders/orders/OrderCard.tsx",
  "src/screens/orders/orders/OrdersStyles.ts",
  "src/screens/orders/orders/OrdersUtils.ts",
];

const maxLines = 700;
const root = process.cwd();
const counts = {};
const failures = [];

for (const file of files) {
  const fullPath = join(root, file);
  if (!existsSync(fullPath)) {
    failures.push(`${file}: arquivo esperado nao existe`);
    continue;
  }

  const source = readFileSync(fullPath, "utf8");
  const nonEmptyLines = source
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0).length;

  counts[file] = nonEmptyLines;
  if (nonEmptyLines >= maxLines) {
    failures.push(
      `${file}: ${nonEmptyLines} linhas com conteudo (limite < ${maxLines})`,
    );
  }

  const invalidControl = [...source].find((char) => {
    const code = char.codePointAt(0);
    return (code < 32 && ![9, 10, 13].includes(code)) || code === 0xfffd;
  });
  if (invalidControl) {
    const code = invalidControl.codePointAt(0).toString(16).toUpperCase();
    failures.push(
      `${file}: contem caractere de controle/replacement U+${code}`,
    );
  }

  const suspiciousQuestion = source
    .split(/\r?\n/)
    .find((line) => /['"`][^'"`]*[A-Za-z]\?[A-Za-z][^'"`]*['"`]/.test(line));
  if (suspiciousQuestion) {
    failures.push(
      `${file}: possivel acento substituido por ? em "${suspiciousQuestion.trim()}"`,
    );
  }

  const suspiciousMojibake = source.match(
    /(\u00c3.|\u00c2.|\u00e2\u0080.|\u00e2\u0082.|\u00f0|\ufffd)/u,
  );
  if (suspiciousMojibake) {
    const line = source
      .slice(0, suspiciousMojibake.index)
      .split(/\r?\n/).length;
    failures.push(`${file}: possivel mojibake na linha ${line}`);
  }
}

const utilsPath = join(root, "src/screens/orders/orders/OrdersUtils.ts");
if (existsSync(utilsPath)) {
  const utilsSource = readFileSync(utilsPath, "utf8");
  for (const expectedExport of [
    "export function getPedidoStatusKey",
    "export function getPedidoItens",
    "export function getPedidoRenderKey",
    "export function getPedidoTitulo",
    "export function getEntregaStatusConfig",
    "export function hasOpenFulfillmentOrder",
  ]) {
    if (!utilsSource.includes(expectedExport)) {
      failures.push(`OrdersUtils.ts: export esperado ausente: ${expectedExport}`);
    }
  }
}

if (failures.length) {
  console.error("Pedidos mobile batch 52 ainda fora do contrato");
  console.error(failures.join("\n"));
  console.error(counts);
  process.exit(1);
}

console.log("Pedidos mobile batch 52 abaixo de 700 linhas", counts);
