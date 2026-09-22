import { useState } from "react";
import { Printer } from "lucide-react";
import toast from "react-hot-toast";
import {
  podeImprimirDocumentoFiscalVenda,
  tipoDocumentoFiscalVenda,
} from "../../utils/pdvFiscalStatus";
import { imprimirDocumentoFiscalVenda } from "../../utils/pdvFiscalPrint";
import ActionButton from "../ui/ActionButton";

export default function ImprimirDocumentoFiscalButton({
  venda,
  className = "",
  intent = "create",
  size = "md",
}) {
  const [imprimindo, setImprimindo] = useState(false);

  if (!podeImprimirDocumentoFiscalVenda(venda)) return null;

  const documento = tipoDocumentoFiscalVenda(venda);
  const handleImprimir = async () => {
    try {
      setImprimindo(true);
      await imprimirDocumentoFiscalVenda(venda);
    } catch (error) {
      toast.error(error?.message || `Não foi possível imprimir a ${documento}.`);
    } finally {
      setImprimindo(false);
    }
  };

  return (
    <ActionButton
      className={className}
      disabled={imprimindo}
      icon={Printer}
      intent={intent}
      loading={imprimindo}
      onClick={handleImprimir}
      size={size}
      title={`Imprimir o DANFE da ${documento}`}
    >
      {imprimindo ? "Preparando..." : `Imprimir ${documento}`}
    </ActionButton>
  );
}
