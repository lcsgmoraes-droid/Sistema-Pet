import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");

const detalheEntregaFiles = [
  "src/screens/entregador/DetalheEntregaScreen.tsx",
  "src/screens/entregador/detalhe/DetalheEntregaContent.tsx",
  "src/screens/entregador/detalhe/DetalheEntregaModals.tsx",
  "src/screens/entregador/detalhe/DetalheEntregaStopCard.tsx",
  "src/screens/entregador/detalhe/DetalheEntregaStyles.ts",
  "src/screens/entregador/detalhe/DetalheEntregaUtils.ts",
];

function nonEmptyLineCount(relativePath) {
  const fullPath = resolve(repoRoot, relativePath);
  if (!existsSync(fullPath)) {
    throw new Error(`Arquivo esperado nao encontrado: ${relativePath}`);
  }

  return readFileSync(fullPath, "utf8")
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0).length;
}

const counts = Object.fromEntries(
  detalheEntregaFiles.map((relativePath) => [
    relativePath,
    nonEmptyLineCount(relativePath),
  ]),
);

const oversized = Object.entries(counts).filter(([, lines]) => lines >= 700);

if (oversized.length) {
  throw new Error(
    `Arquivos de detalhe de entrega ainda acima do limite: ${JSON.stringify(
      Object.fromEntries(oversized),
      null,
      2,
    )}`,
  );
}

console.log("Detalhe entrega mobile batch 43 abaixo de 700 linhas", counts);
