import { forwardRef } from "react";
import BotaoBase from "../BotaoBase/BotaoBase";

const BotaoInteracao = forwardRef(function BotaoInteracao(
  { children, disabled, icon, onClick, type = "button" },
  ref,
) {
  return (
    <BotaoBase
      ref={ref}
      variante="informativo"
      icon={icon}
      disabled={disabled}
      onClick={onClick}
      type={type}
    >
      {children}
    </BotaoBase>
  );
});

export default BotaoInteracao;
