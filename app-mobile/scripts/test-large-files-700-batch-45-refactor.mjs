import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");

const funcionarioContagemFiles = [
  "src/screens/funcionario/FuncionarioContagemScreen.tsx",
  "src/screens/funcionario/contagem/FuncionarioContagemContent.tsx",
  "src/screens/funcionario/contagem/FuncionarioContagemItemComponents.tsx",
  "src/screens/funcionario/contagem/FuncionarioContagemScanner.tsx",
  "src/screens/funcionario/contagem/FuncionarioContagemStyles.ts",
  "src/screens/funcionario/contagem/FuncionarioContagemUtils.ts",
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
  funcionarioContagemFiles.map((relativePath) => [
    relativePath,
    nonEmptyLineCount(relativePath),
  ]),
);

const oversized = Object.entries(counts).filter(([, lines]) => lines >= 700);

if (oversized.length) {
  throw new Error(
    `Arquivos da contagem funcionario ainda acima do limite: ${JSON.stringify(
      Object.fromEntries(oversized),
      null,
      2,
    )}`,
  );
}

console.log("Contagem funcionario mobile batch 45 abaixo de 700 linhas", counts);
