import { Save } from "lucide-react";
import { forwardRef } from "react";
import BotaoBase from "../BotaoBase/BotaoBase";

const BotaoSalva = forwardRef(function BotaoSalva(
  { children = "Salvar", disabled, loading, onClick, type = "submit" },
  ref,
) {
  return (
    <BotaoBase
      ref={ref}
      variante="sucesso"
      icon={Save}
      disabled={disabled}
      loading={loading}
      onClick={onClick}
      type={type}
    >
      {children}
    </BotaoBase>
  );
});

export default BotaoSalva;
