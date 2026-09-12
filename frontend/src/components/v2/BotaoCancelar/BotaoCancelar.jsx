import { X } from "lucide-react";
import { forwardRef } from "react";
import BotaoBase from "../BotaoBase/BotaoBase";

const BotaoCancelar = forwardRef(function BotaoCancelar(
  { children = "Cancelar", disabled, onClick, tamanho = "normal", type = "button", ...rest },
  ref,
) {
  return (
    <BotaoBase
      {...rest}
      ref={ref}
      variante="atencao"
      icon={X}
      disabled={disabled}
      onClick={onClick}
      tamanho={tamanho}
      type={type}
    >
      {children}
    </BotaoBase>
  );
});

export default BotaoCancelar;
