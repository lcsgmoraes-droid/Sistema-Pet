import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");

const funcionarioPdvFiles = [
  "src/screens/funcionario/FuncionarioPdvScreen.tsx",
  "src/screens/funcionario/pdv/FuncionarioPdvContent.tsx",
  "src/screens/funcionario/pdv/FuncionarioPdvProductImage.tsx",
  "src/screens/funcionario/pdv/FuncionarioPdvScanner.tsx",
  "src/screens/funcionario/pdv/FuncionarioPdvStyles.ts",
  "src/screens/funcionario/pdv/FuncionarioPdvUtils.ts",
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
  funcionarioPdvFiles.map((relativePath) => [
    relativePath,
    nonEmptyLineCount(relativePath),
  ]),
);

const oversized = Object.entries(counts).filter(([, lines]) => lines >= 700);

if (oversized.length) {
  throw new Error(
    `Arquivos do PDV funcionario ainda acima do limite: ${JSON.stringify(
      Object.fromEntries(oversized),
      null,
      2,
    )}`,
  );
}

console.log("PDV funcionario mobile batch 42 abaixo de 700 linhas", counts);
