import { X } from "lucide-react";
import { forwardRef } from "react";
import BotaoBase from "../BotaoBase/BotaoBase";

const BotaoCancelar = forwardRef(function BotaoCancelar(
  { children = "Cancelar", disabled, onClick, type = "button" },
  ref,
) {
  return (
    <BotaoBase
      ref={ref}
      variante="neutroSuave"
      icon={X}
      disabled={disabled}
      onClick={onClick}
      type={type}
    >
      {children}
    </BotaoBase>
  );
});

export default BotaoCancelar;
