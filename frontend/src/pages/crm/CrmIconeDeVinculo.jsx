import { UserRoundCheck, UserRoundX } from "lucide-react";

// Ícone antes do nome do tutor (card e ficha): visto verde = ligado a um cadastro; X azul =
// sem cadastro. Tem dica ao passar o mouse e texto para leitores de tela (não depende só da cor).
export default function CrmIconeDeVinculo({ semCadastro, nome, tamanho = "h-4 w-4" }) {
  const texto = semCadastro
    ? "Sem cadastro: ainda não está ligado a nenhuma pessoa"
    : `Ligado ao cadastro de ${nome}`;
  const Icone = semCadastro ? UserRoundX : UserRoundCheck;
  const cor = semCadastro
    ? "text-blue-700 dark:text-blue-300"
    : "text-emerald-700 dark:text-emerald-300";
  return (
    <span
      title={texto}
      role="img"
      aria-label={texto}
      className={`mr-1.5 inline-block align-text-bottom ${cor}`}
    >
      <Icone className={tamanho} aria-hidden="true" />
    </span>
  );
}
