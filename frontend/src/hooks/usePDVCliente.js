import { usePDVClienteBusca } from "./usePDVClienteBusca";
import { usePDVClienteContexto } from "./usePDVClienteContexto";

export function usePDVCliente({ vendaAtual, setVendaAtual }) {
  const {
    copiadoClienteCampo,
    vendasEmAbertoInfo,
    saldoCampanhas,
    setSaldoCampanhas,
    carregarVendasEmAbertoCliente,
    carregarSaldoCampanhasCliente,
    limparClienteSelecionado,
    selecionarPet,
    copiarCampoCliente,
    recarregarVendasEmAbertoClienteAtual,
  } = usePDVClienteContexto({
    vendaAtual,
    setVendaAtual,
  });
  const {
    buscarCliente,
    setBuscarCliente,
    clientesSugeridos,
    buscarClientePorCodigoExato,
    selecionarCliente,
    handleClienteCriadoRapido,
  } = usePDVClienteBusca({
    setVendaAtual,
    setSaldoCampanhas,
    carregarVendasEmAbertoCliente,
    carregarSaldoCampanhasCliente,
  });

  return {
    buscarCliente,
    setBuscarCliente,
    clientesSugeridos,
    copiadoClienteCampo,
    vendasEmAbertoInfo,
    saldoCampanhas,
    setSaldoCampanhas,
    buscarClientePorCodigoExato,
    selecionarCliente,
    selecionarPet,
    copiarCampoCliente,
    limparClienteSelecionado,
    handleClienteCriadoRapido,
    recarregarVendasEmAbertoClienteAtual,
  };
}
