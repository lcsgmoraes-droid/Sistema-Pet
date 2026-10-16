import { ExternalLink } from "lucide-react";
import { forwardRef } from "react";
import { Link as LinkRouter } from "react-router-dom";

// Link padrão do sistema — cor, peso e ícone sempre iguais em qualquer tela; o único ajuste livre
// é o tamanho da fonte (prop `tamanho`). Serve tanto rota interna (`to`, via react-router) quanto
// URL externa (`href`). É para navegação de verdade — ação secundária dentro de um painel continua
// sendo BotaoLink.
const LinkPadrao = forwardRef(function LinkPadrao(
  { children, href, novaJanela = false, tamanho = "text-sm", to, ...rest },
  ref,
) {
  const classe = [
    tamanho,
    "inline-flex items-center gap-1 font-semibold text-blue-600 hover:text-blue-700 hover:underline",
    "dark:text-cyan-300 dark:hover:text-cyan-200",
  ].join(" ");

  const conteudo = (
    <>
      {children}
      {novaJanela ? <ExternalLink className="h-[1em] w-[1em]" aria-hidden="true" /> : null}
    </>
  );

  const propsNovaJanela = novaJanela ? { target: "_blank", rel: "noopener noreferrer" } : {};

  if (to) {
    return (
      <LinkRouter {...rest} {...propsNovaJanela} ref={ref} to={to} className={classe}>
        {conteudo}
      </LinkRouter>
    );
  }

  return (
    <a {...rest} {...propsNovaJanela} ref={ref} href={href} className={classe}>
      {conteudo}
    </a>
  );
});

export default LinkPadrao;
