import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");

const foodCalculatorFiles = [
  "src/screens/pets/FoodCalculatorScreen.tsx",
  "src/screens/pets/food-calculator/FoodCalculatorContent.tsx",
  "src/screens/pets/food-calculator/FoodCalculatorResultCards.tsx",
  "src/screens/pets/food-calculator/FoodCalculatorSelectors.tsx",
  "src/screens/pets/food-calculator/FoodCalculatorStyles.ts",
  "src/screens/pets/food-calculator/FoodCalculatorUtils.ts",
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
  foodCalculatorFiles.map((relativePath) => [
    relativePath,
    nonEmptyLineCount(relativePath),
  ]),
);

const oversized = Object.entries(counts).filter(([, lines]) => lines >= 700);

if (oversized.length) {
  throw new Error(
    `Arquivos da calculadora de racao mobile ainda acima do limite: ${JSON.stringify(
      Object.fromEntries(oversized),
      null,
      2,
    )}`,
  );
}

console.log("Calculadora de racao mobile batch 47 abaixo de 700 linhas", counts);
