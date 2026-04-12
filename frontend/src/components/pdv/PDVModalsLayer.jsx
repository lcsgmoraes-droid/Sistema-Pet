import { useEffect } from "react";
import AnaliseVendaDrawer from "../AnaliseVendaDrawer";
import ModalAbrirCaixa from "../ModalAbrirCaixa";
import ModalAdicionarCredito from "../ModalAdicionarCredito";
import ModalPagamento from "../ModalPagamento";
import HistoricoCliente from "./HistoricoCliente";
import ModalCadastroCliente from "./ModalCadastroCliente";
import ModalCalculadoraRacaoPDV from "./ModalCalculadoraRacaoPDV";
import ModalPendenciasEstoque from "./ModalPendenciasEstoque";
import PDVDescontoItemModal from "./PDVDescontoItemModal";
import PDVDescontoTotalModal from "./PDVDescontoTotalModal";
import PDVEnderecoModal from "./PDVEnderecoModal";
import VendasEmAberto from "./VendasEmAberto";

export default function PDVModalsLayer({
  carregandoAnalise,
  dadosAnalise,
  enderecoAtual,
  itemEditando,
  loadingCep,
  mostrarAnaliseVenda,
  mostrarCalculadoraRacao,
  mostrarHistoricoCliente,
  mostrarModalAbrirCaixa,
  mostrarModalAdicionarCredito,
  mostrarModalCliente,
  mostrarModalDescontoItem,
  mostrarModalDescontoTotal,
  mostrarModalEndereco,
  mostrarModalPagamento,
  mostrarPendenciasEstoque,
  mostrarVendasEmAberto,
  podeVerMargem,
  racaoIdFechada,
  setTipoDescontoTotal,
  setValorDescontoTotal,
  tipoDescontoTotal,
  valorDescontoTotal,
  vendaAtual,
  onAbrirCaixaSucesso,
  onAnalisarVenda,
  onAplicarDescontoTotal,
  onBuscarCep,
  onChangeEnderecoAtual,
  onChangeItemEditando,
  onClienteCriado,
  onCloseAnalise,
  onCloseCalculadoraRacao,
  onCloseHistoricoCliente,
  onCloseModalAbrirCaixa,
  onCloseModalAdicionarCredito,
  onCloseModalCliente,
  onCloseModalDescontoItem,
  onCloseModalDescontoTotal,
  onCloseModalEndereco,
  onCloseModalPagamento,
  onClosePendenciasEstoque,
  onCloseVendasEmAberto,
  onConfirmarCredito,
  onConfirmarPagamento,
  onPendenciaAdicionada,
  onRemoverItemEditando,
  onSalvarDescontoItem,
  onSalvarEndereco,
  onVendaAtualizada,
  onVendasEmAbertoSucesso,
}) {
  const clienteAtual = vendaAtual.cliente;

  useEffect(() => {
    const modalCloseStack = [
      mostrarModalPagamento && onCloseModalPagamento,
      mostrarModalDescontoTotal && onCloseModalDescontoTotal,
      mostrarModalDescontoItem && onCloseModalDescontoItem,
      mostrarModalEndereco && onCloseModalEndereco,
      mostrarModalCliente && onCloseModalCliente,
      mostrarModalAdicionarCredito && onCloseModalAdicionarCredito,
      mostrarVendasEmAberto && onCloseVendasEmAberto,
      mostrarHistoricoCliente && onCloseHistoricoCliente,
      mostrarPendenciasEstoque && onClosePendenciasEstoque,
      mostrarCalculadoraRacao && onCloseCalculadoraRacao,
      mostrarModalAbrirCaixa && onCloseModalAbrirCaixa,
      mostrarAnaliseVenda && onCloseAnalise,
    ].filter(Boolean);

    if (modalCloseStack.length === 0) {
      return undefined;
    }

    const handleEscape = (event) => {
      if (event.key !== "Escape") {
        return;
      }

      event.preventDefault();
      modalCloseStack[0]?.();
    };

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [
    mostrarModalPagamento,
    onCloseModalPagamento,
    mostrarModalDescontoTotal,
    onCloseModalDescontoTotal,
    mostrarModalDescontoItem,
    onCloseModalDescontoItem,
    mostrarModalEndereco,
    onCloseModalEndereco,
    mostrarModalCliente,
    onCloseModalCliente,
    mostrarModalAdicionarCredito,
    onCloseModalAdicionarCredito,
    mostrarVendasEmAberto,
    onCloseVendasEmAberto,
    mostrarHistoricoCliente,
    onCloseHistoricoCliente,
    mostrarPendenciasEstoque,
    onClosePendenciasEstoque,
    mostrarCalculadoraRacao,
    onCloseCalculadoraRacao,
    mostrarModalAbrirCaixa,
    onCloseModalAbrirCaixa,
    mostrarAnaliseVenda,
    onCloseAnalise,
  ]);

  return (
    <>
      {mostrarModalPagamento && (
        <ModalPagamento
          venda={vendaAtual}
          onClose={onCloseModalPagamento}
          onAnalisarVenda={onAnalisarVenda}
          onConfirmar={onConfirmarPagamento}
          onVendaAtualizada={onVendaAtualizada}
        />
      )}

      {mostrarModalAbrirCaixa && (
        <ModalAbrirCaixa
          onClose={onCloseModalAbrirCaixa}
          onSucesso={onAbrirCaixaSucesso}
        />
      )}

      {mostrarCalculadoraRacao && (
        <ModalCalculadoraRacaoPDV
          isOpen={mostrarCalculadoraRacao}
          itensCarrinho={vendaAtual.itens}
          racaoIdFechada={racaoIdFechada}
          onClose={onCloseCalculadoraRacao}
        />
      )}

      {mostrarPendenciasEstoque && clienteAtual && (
        <ModalPendenciasEstoque
          isOpen={mostrarPendenciasEstoque}
          onClose={onClosePendenciasEstoque}
          clienteId={clienteAtual.id}
          onPendenciaAdicionada={onPendenciaAdicionada}
        />
      )}

      {mostrarModalCliente && (
        <ModalCadastroCliente
          onClose={onCloseModalCliente}
          onClienteCriado={onClienteCriado}
        />
      )}

      {mostrarModalEndereco && enderecoAtual && (
        <PDVEnderecoModal
          enderecoAtual={enderecoAtual}
          loadingCep={loadingCep}
          onBuscarCep={onBuscarCep}
          onChange={onChangeEnderecoAtual}
          onClose={onCloseModalEndereco}
          onSalvar={onSalvarEndereco}
        />
      )}

      {mostrarModalDescontoItem && itemEditando && (
        <PDVDescontoItemModal
          itemEditando={itemEditando}
          onChangeItem={onChangeItemEditando}
          onClose={onCloseModalDescontoItem}
          onRemover={onRemoverItemEditando}
          onSalvar={onSalvarDescontoItem}
        />
      )}

      {mostrarModalDescontoTotal && (
        <PDVDescontoTotalModal
          itens={vendaAtual.itens}
          onAplicar={onAplicarDescontoTotal}
          onClose={onCloseModalDescontoTotal}
          setTipoDescontoTotal={setTipoDescontoTotal}
          setValorDescontoTotal={setValorDescontoTotal}
          tipoDescontoTotal={tipoDescontoTotal}
          valorDescontoTotal={valorDescontoTotal}
        />
      )}

      {mostrarVendasEmAberto && clienteAtual && (
        <VendasEmAberto
          clienteId={clienteAtual.id}
          clienteNome={clienteAtual.nome}
          onClose={onCloseVendasEmAberto}
          onSucesso={onVendasEmAbertoSucesso}
        />
      )}

      {mostrarModalAdicionarCredito && clienteAtual && (
        <ModalAdicionarCredito
          cliente={clienteAtual}
          onConfirmar={onConfirmarCredito}
          onClose={onCloseModalAdicionarCredito}
        />
      )}

      {mostrarHistoricoCliente && clienteAtual && (
        <HistoricoCliente
          clienteId={clienteAtual.id}
          clienteNome={clienteAtual.nome}
          onClose={onCloseHistoricoCliente}
        />
      )}

      {podeVerMargem && (
        <AnaliseVendaDrawer
          mostrar={mostrarAnaliseVenda}
          onFechar={onCloseAnalise}
          dados={dadosAnalise}
          carregando={carregandoAnalise}
        />
      )}
    </>
  );
}
