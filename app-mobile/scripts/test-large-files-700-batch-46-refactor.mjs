import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");

const petDetailFiles = [
  "src/screens/pets/PetDetailScreen.tsx",
  "src/screens/pets/detail/PetDetailContent.tsx",
  "src/screens/pets/detail/PetDetailSharedComponents.tsx",
  "src/screens/pets/detail/PetDetailStyles.ts",
  "src/screens/pets/detail/PetDetailUtils.ts",
  "src/screens/pets/detail/PetDetailVaccineBooklet.tsx",
  "src/screens/pets/detail/PetDetailVaccineModal.tsx",
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
  petDetailFiles.map((relativePath) => [
    relativePath,
    nonEmptyLineCount(relativePath),
  ]),
);

const oversized = Object.entries(counts).filter(([, lines]) => lines >= 700);

if (oversized.length) {
  throw new Error(
    `Arquivos de detalhe do pet mobile ainda acima do limite: ${JSON.stringify(
      Object.fromEntries(oversized),
      null,
      2,
    )}`,
  );
}

console.log("Detalhe do pet mobile batch 46 abaixo de 700 linhas", counts);
