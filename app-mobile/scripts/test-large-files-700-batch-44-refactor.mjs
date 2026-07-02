import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");

const beneficiosFiles = [
  "src/screens/benefits/BeneficiosScreen.tsx",
  "src/screens/benefits/beneficios/BeneficiosCashbackSection.tsx",
  "src/screens/benefits/beneficios/BeneficiosCouponsSection.tsx",
  "src/screens/benefits/beneficios/BeneficiosRankingSection.tsx",
  "src/screens/benefits/beneficios/BeneficiosStampAndLevelsSections.tsx",
  "src/screens/benefits/beneficios/BeneficiosStyles.ts",
  "src/screens/benefits/beneficios/BeneficiosUtils.ts",
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
  beneficiosFiles.map((relativePath) => [
    relativePath,
    nonEmptyLineCount(relativePath),
  ]),
);

const oversized = Object.entries(counts).filter(([, lines]) => lines >= 700);

if (oversized.length) {
  throw new Error(
    `Arquivos de beneficios mobile ainda acima do limite: ${JSON.stringify(
      Object.fromEntries(oversized),
      null,
      2,
    )}`,
  );
}

console.log("Beneficios mobile batch 44 abaixo de 700 linhas", counts);
