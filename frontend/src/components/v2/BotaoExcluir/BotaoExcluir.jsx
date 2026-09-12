import { Trash2 } from "lucide-react";
import { forwardRef, useState } from "react";
import BotaoBase from "../BotaoBase/BotaoBase";
import { confirmarCorePet } from "../../../services/corepetDialog";

const BotaoExcluir = forwardRef(function BotaoExcluir(
  {
    children = "Excluir",
    disabled,
    mensagemConfirmacao = "Excluir este registro? Essa ação não pode ser desfeita.",
    onClick,
    tamanho = "normal",
    ...rest
  },
  ref,
) {
  const [confirmando, setConfirmando] = useState(false);

  const aoClicar = async () => {
    setConfirmando(true);
    try {
      const confirmado = await confirmarCorePet(mensagemConfirmacao);
      if (confirmado) await onClick?.();
    } finally {
      setConfirmando(false);
    }
  };

  return (
    <BotaoBase
      {...rest}
      ref={ref}
      variante="perigo"
      icon={Trash2}
      disabled={disabled}
      loading={confirmando}
      onClick={aoClicar}
      tamanho={tamanho}
    >
      {children}
    </BotaoBase>
  );
});

export default BotaoExcluir;
