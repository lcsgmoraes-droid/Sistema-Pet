import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const files = [
  "src/screens/shop/CatalogScreen.tsx",
  "src/screens/shop/catalog/CatalogContent.tsx",
  "src/screens/shop/catalog/CatalogFilterModal.tsx",
  "src/screens/shop/catalog/CatalogProductCard.tsx",
  "src/screens/shop/catalog/CatalogStyles.ts",
  "src/screens/shop/catalog/CatalogUtils.ts",
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
}

const utilsSource = readFileSync(
  join(root, "src/screens/shop/catalog/CatalogUtils.ts"),
  "utf8",
);
if (
  !/\.replace\(\s*\/\[\\u0300-\\u036f\]\/g,\s*["']{2}\s*\)/.test(utilsSource)
) {
  failures.push(
    "CatalogUtils.ts: normalizacao de acentos perdeu o range Unicode esperado",
  );
}

if (
  !utilsSource.includes(
    "const termosCao = /\\b(cao|caes|canin|cachorro|dog|puppy)\\b/;",
  )
) {
  failures.push(
    "CatalogUtils.ts: regex de especie cao perdeu os limites de palavra",
  );
}

if (
  !utilsSource.includes(
    "const termosGato = /\\b(gato|gatos|felin|cat|kitten)\\b/;",
  )
) {
  failures.push(
    "CatalogUtils.ts: regex de especie gato perdeu os limites de palavra",
  );
}

if (failures.length) {
  console.error("Catalogo mobile batch 49 ainda acima do contrato de linhas");
  console.error(failures.join("\n"));
  console.error(counts);
  process.exit(1);
}

console.log("Catalogo mobile batch 49 abaixo de 700 linhas", counts);
