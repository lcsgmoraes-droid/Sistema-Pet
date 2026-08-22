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

const sources = Object.fromEntries(
  detalheEntregaFiles.map((relativePath) => [
    relativePath,
    readFileSync(resolve(repoRoot, relativePath), "utf8"),
  ]),
);

const mojibake = Object.entries(sources).flatMap(([relativePath, source]) => {
  const match = source.match(
    /(\u00c3[\u0080-\u00bfƒŠŒŽšœžŸ]|\u00f0[\u0080-\u00bfƒŠŒŽšœžŸ]|\u00e2[€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ]|\ufffd)/u,
  );
  if (!match) return [];

  const line = source.slice(0, match.index).split(/\r?\n/).length;
  return [`${relativePath}:${line}`];
});

const expectedText = {
  "src/screens/entregador/detalhe/DetalheEntregaContent.tsx": [
    "Rota não encontrada.",
    "▶ Iniciar Rota",
    "✅ Finalizar Rota",
  ],
  "src/screens/entregador/detalhe/DetalheEntregaStopCard.tsx": [
    "☰",
    "📝",
    "📍 Navegar",
    "📞 Ligar",
    "💳",
    "📄 Detalhes",
    "✅ Entregue",
    "❌ Não entregue",
  ],
  "src/screens/entregador/detalhe/DetalheEntregaModals.tsx": [
    "Salvar posição",
    "Pré-integração Stone/Operadora",
    "Débito",
    "Crédito",
    "🧾 Detalhes da Venda",
    "Endereço:",
    '{" • "}',
  ],
  "src/screens/entregador/detalhe/DetalheEntregaUtils.ts": [
    "Não foi possível abrir o mapa.",
    "Não foi possível ligar.",
    "Entregue ✓",
    "Não entregue ✗",
  ],
};

const missingText = Object.entries(expectedText).flatMap(
  ([relativePath, snippets]) =>
    snippets
      .filter((snippet) => !sources[relativePath].includes(snippet))
      .map((snippet) => `${relativePath}: texto esperado ausente: ${snippet}`),
);

if (oversized.length || mojibake.length || missingText.length) {
  throw new Error(
    [
      oversized.length
        ? `Arquivos de detalhe de entrega ainda acima do limite: ${JSON.stringify(
            Object.fromEntries(oversized),
            null,
            2,
          )}`
        : null,
      mojibake.length
        ? `Textos com codificação suspeita:\n${mojibake.join("\n")}`
        : null,
      missingText.length
        ? `Textos/ícones esperados ausentes:\n${missingText.join("\n")}`
        : null,
    ]
      .filter(Boolean)
      .join("\n\n"),
  );
}

console.log("Detalhe entrega mobile batch 43 abaixo de 700 linhas", counts);
