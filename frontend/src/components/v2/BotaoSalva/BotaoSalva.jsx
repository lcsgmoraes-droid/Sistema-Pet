import { Save } from "lucide-react";
import { forwardRef } from "react";
import BotaoBase from "../BotaoBase/BotaoBase";

const BotaoSalva = forwardRef(function BotaoSalva(
  { children = "Salvar", disabled, loading, onClick, tamanho = "normal", type = "submit", ...rest },
  ref,
) {
  return (
    <BotaoBase
      {...rest}
      ref={ref}
      variante="sucesso"
      icon={Save}
      disabled={disabled}
      loading={loading}
      onClick={onClick}
      tamanho={tamanho}
      type={type}
    >
      {children}
    </BotaoBase>
  );
});

export default BotaoSalva;
