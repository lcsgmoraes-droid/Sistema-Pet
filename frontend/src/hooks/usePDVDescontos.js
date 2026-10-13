import { usePDVCupom } from "./usePDVCupom";
import { usePDVDescontoItens } from "./usePDVDescontoItens";
import { usePDVDescontoTotal } from "./usePDVDescontoTotal";
import { confirmarCorePet } from "../services/corepetDialog";
import { converterDescontosLegados } from "../utils/pdvDescontosUtils";

export function usePDVDescontos({ vendaAtual, setVendaAtual }) {
  const prepararDescontos = async () => {
    if (vendaAtual.desconto_venda_valor != null) return vendaAtual;
    const confirmado = await confirmarCorePet({
      titulo: "Separar os descontos anteriores?",
      mensagem:
        "Esta venda usa o formato antigo de descontos. Ao alterar desconto geral ou cupom, os valores serão separados; confira os descontos de cada produto antes de salvar.",
      confirmarTexto: "Separar e continuar",
      variante: "warning",
    });
    if (!confirmado) return null;
    const convertida = converterDescontosLegados(vendaAtual);
    setVendaAtual(convertida);
    return convertida;
  };
  const {
    mostrarModalDescontoItem,
    setMostrarModalDescontoItem,
    itemEditando,
    setItemEditando,
    recalcularTotais,
    abrirModalDescontoItem,
    salvarDescontoItem,
    removerItemEditando,
  } = usePDVDescontoItens({
    vendaAtual,
    setVendaAtual,
  });

  const {
    mostrarModalDescontoTotal,
    setMostrarModalDescontoTotal,
    tipoDescontoTotal,
    setTipoDescontoTotal,
    valorDescontoTotal,
    setValorDescontoTotal,
    abrirModalDescontoTotal,
    aplicarDescontoTotal,
    removerDescontoTotal,
  } = usePDVDescontoTotal({
    vendaAtual,
    recalcularTotais,
    prepararDescontos,
  });

  const {
    codigoCupom,
    cupomAplicado,
    loadingCupom,
    erroCupom,
    aplicarCupom,
    removerCupom,
    handleCodigoCupomChange,
    handleCodigoCupomKeyDown,
  } = usePDVCupom({
    vendaAtual,
    recalcularTotais,
    prepararDescontos,
  });

  return {
    mostrarModalDescontoItem,
    setMostrarModalDescontoItem,
    itemEditando,
    setItemEditando,
    mostrarModalDescontoTotal,
    setMostrarModalDescontoTotal,
    tipoDescontoTotal,
    setTipoDescontoTotal,
    valorDescontoTotal,
    setValorDescontoTotal,
    codigoCupom,
    cupomAplicado,
    loadingCupom,
    erroCupom,
    recalcularTotais,
    abrirModalDescontoItem,
    salvarDescontoItem,
    removerItemEditando,
    abrirModalDescontoTotal,
    aplicarDescontoTotal,
    removerDescontoTotal,
    aplicarCupom,
    removerCupom,
    handleCodigoCupomChange,
    handleCodigoCupomKeyDown,
  };
}
