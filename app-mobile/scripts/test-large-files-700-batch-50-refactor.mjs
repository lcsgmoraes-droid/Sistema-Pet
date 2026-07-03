import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const files = [
  "src/screens/veterinario/VetAgendaScreen.tsx",
  "src/screens/veterinario/vet-agenda/VetAgendaContent.tsx",
  "src/screens/veterinario/vet-agenda/VetAgendaAppointmentModal.tsx",
  "src/screens/veterinario/vet-agenda/VetAgendaStyles.ts",
  "src/screens/veterinario/vet-agenda/VetAgendaUtils.ts",
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

const utilsPath = join(
  root,
  "src/screens/veterinario/vet-agenda/VetAgendaUtils.ts",
);
if (existsSync(utilsPath)) {
  const utilsSource = readFileSync(utilsPath, "utf8");
  for (const expectedExport of [
    "export function periodoAgenda",
    "export function gerarCalendarioDias",
    "export function formInicialAgendamento",
    "export function formatarDataIsoParaBr",
  ]) {
    if (!utilsSource.includes(expectedExport)) {
      failures.push(
        `VetAgendaUtils.ts: export esperado ausente: ${expectedExport}`,
      );
    }
  }
}

if (failures.length) {
  console.error("Agenda veterinaria mobile batch 50 ainda fora do contrato");
  console.error(failures.join("\n"));
  console.error(counts);
  process.exit(1);
}

console.log("Agenda veterinaria mobile batch 50 abaixo de 700 linhas", counts);
