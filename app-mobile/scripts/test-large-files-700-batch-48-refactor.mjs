import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const files = [
  "src/screens/profile/ProfileScreen.tsx",
  "src/screens/profile/profile/ProfileContent.tsx",
  "src/screens/profile/profile/ProfileAddressSections.tsx",
  "src/screens/profile/profile/ProfilePersonalSections.tsx",
  "src/screens/profile/profile/ProfileSharedComponents.tsx",
  "src/screens/profile/profile/ProfileStyles.ts",
  "src/screens/profile/profile/ProfileUtils.ts",
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

  const nonEmptyLines = readFileSync(fullPath, "utf8")
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0).length;

  counts[file] = nonEmptyLines;
  if (nonEmptyLines >= maxLines) {
    failures.push(`${file}: ${nonEmptyLines} linhas com conteudo (limite < ${maxLines})`);
  }
}

if (failures.length) {
  console.error("Profile mobile batch 48 ainda acima do contrato de linhas");
  console.error(failures.join("\n"));
  console.error(counts);
  process.exit(1);
}

console.log("Profile mobile batch 48 abaixo de 700 linhas", counts);
