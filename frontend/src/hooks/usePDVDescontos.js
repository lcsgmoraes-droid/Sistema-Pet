import { usePDVCupom } from "./usePDVCupom";
import { usePDVDescontoItens } from "./usePDVDescontoItens";
import { usePDVDescontoTotal } from "./usePDVDescontoTotal";

export function usePDVDescontos({ vendaAtual, setVendaAtual }) {
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
    aplicarDescontoTotal,
    removerDescontoTotal,
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
