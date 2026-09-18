import { forwardRef } from "react";
import BotaoBase from "../BotaoBase/BotaoBase";

const BotaoInteracao = forwardRef(function BotaoInteracao(
  { children, disabled, icon, loading, onClick, tamanho = "normal", type = "button", ...rest },
  ref,
) {
  return (
    <BotaoBase
      {...rest}
      ref={ref}
      variante="informativo"
      icon={icon}
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

export default BotaoInteracao;
