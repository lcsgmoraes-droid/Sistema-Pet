import { forwardRef } from "react";

// Link de navegação secundário dentro de um painel ("ver mais", "ver produtos") — não é uma ação
// de formulário (por isso não usa BotaoBase: não tem tamanho nem variante, é sempre texto simples).
const BotaoLink = forwardRef(function BotaoLink(
  { children, onClick, type = "button", ...rest },
  ref,
) {
  return (
    <button
      {...rest}
      ref={ref}
      type={type}
      onClick={onClick}
      className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline dark:text-cyan-300 dark:hover:text-cyan-200"
    >
      {children}
    </button>
  );
});

export default BotaoLink;
