import CampanhasGestorHeader from "./CampanhasGestorHeader";
import CampanhasGestorCampanhaLista from "./CampanhasGestorCampanhaLista";
import CampanhasGestorClienteResumo from "./CampanhasGestorClienteResumo";
import CampanhasGestorCarimbosSection from "./CampanhasGestorCarimbosSection";
import CampanhasGestorCashbackSection from "./CampanhasGestorCashbackSection";
import CampanhasGestorCuponsSection from "./CampanhasGestorCuponsSection";
import CampanhasGestorRankingSection from "./CampanhasGestorRankingSection";

export default function CampanhasGestorTab({
  gestorModo,
  setGestorModo,
  gestorSearch,
  setGestorSearch,
  buscarClientesGestor,
  setGestorSugestoes,
  gestorBuscando,
  gestorSugestoes,
  selecionarClienteGestor,
  gestorCampanhaTipo,
  setGestorCampanhaTipo,
  carregarClientesPorCampanha,
  gestorCampanhaCarregando,
  gestorCampanhaLista,
  abrirClienteNoGestor,
  gestorCarregando,
  gestorCliente,
  gestorSaldo,
  gestorCarimbos,
  gestorSecao,
  setGestorSecao,
  gestorIncluirEstornados,
  setGestorIncluirEstornados,
  gestorCarimboNota,
  setGestorCarimboNota,
  gestorLancandoCarimbo,
  lancarCarimboGestor,
  gestorRemovendo,
  estornarCarimboGestor,
  formatBRL,
  RANK_LABELS,
  gestorCashbackTipo,
  setGestorCashbackTipo,
  gestorCashbackValor,
  setGestorCashbackValor,
  gestorCashbackDesc,
  setGestorCashbackDesc,
  gestorLancandoCashback,
  ajustarCashbackGestor,
  gestorCupons,
  CUPOM_STATUS,
  anularCupomGestor,
  gestorAnulando,
}) {
  return (
    <div className="space-y-4">
      <CampanhasGestorHeader
        gestorModo={gestorModo}
        setGestorModo={setGestorModo}
        gestorSearch={gestorSearch}
        setGestorSearch={setGestorSearch}
        buscarClientesGestor={buscarClientesGestor}
        setGestorSugestoes={setGestorSugestoes}
        gestorBuscando={gestorBuscando}
        gestorSugestoes={gestorSugestoes}
        selecionarClienteGestor={selecionarClienteGestor}
        gestorCampanhaTipo={gestorCampanhaTipo}
        setGestorCampanhaTipo={setGestorCampanhaTipo}
        carregarClientesPorCampanha={carregarClientesPorCampanha}
        gestorCampanhaCarregando={gestorCampanhaCarregando}
      />

      <CampanhasGestorCampanhaLista
        gestorModo={gestorModo}
        gestorCampanhaCarregando={gestorCampanhaCarregando}
        gestorCampanhaLista={gestorCampanhaLista}
        abrirClienteNoGestor={abrirClienteNoGestor}
      />

      {gestorModo === "cliente" && gestorCarregando && (
        <div className="text-center py-12 text-gray-400">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3" />
          <p className="text-sm">Carregando dados do cliente...</p>
        </div>
      )}

      {gestorModo === "cliente" &&
        gestorCliente &&
        gestorSaldo &&
        !gestorCarregando && (
          <>
            <CampanhasGestorClienteResumo
              gestorCliente={gestorCliente}
              gestorSaldo={gestorSaldo}
              rankLabels={RANK_LABELS}
            />

            <CampanhasGestorCarimbosSection
              gestorSaldo={gestorSaldo}
              gestorSecao={gestorSecao}
              setGestorSecao={setGestorSecao}
              gestorCarimboNota={gestorCarimboNota}
              setGestorCarimboNota={setGestorCarimboNota}
              gestorLancandoCarimbo={gestorLancandoCarimbo}
              lancarCarimboGestor={lancarCarimboGestor}
              gestorCarimbos={gestorCarimbos}
              gestorIncluirEstornados={gestorIncluirEstornados}
              setGestorIncluirEstornados={setGestorIncluirEstornados}
              gestorRemovendo={gestorRemovendo}
              estornarCarimboGestor={estornarCarimboGestor}
            />

            <CampanhasGestorCashbackSection
              gestorSaldo={gestorSaldo}
              gestorSecao={gestorSecao}
              setGestorSecao={setGestorSecao}
              formatBRL={formatBRL}
              gestorCashbackTipo={gestorCashbackTipo}
              setGestorCashbackTipo={setGestorCashbackTipo}
              gestorCashbackValor={gestorCashbackValor}
              setGestorCashbackValor={setGestorCashbackValor}
              gestorCashbackDesc={gestorCashbackDesc}
              setGestorCashbackDesc={setGestorCashbackDesc}
              gestorLancandoCashback={gestorLancandoCashback}
              ajustarCashbackGestor={ajustarCashbackGestor}
            />

            <CampanhasGestorCuponsSection
              gestorSecao={gestorSecao}
              setGestorSecao={setGestorSecao}
              gestorCupons={gestorCupons}
              cupomStatus={CUPOM_STATUS}
              formatBRL={formatBRL}
              anularCupomGestor={anularCupomGestor}
              gestorAnulando={gestorAnulando}
            />

            <CampanhasGestorRankingSection
              gestorSaldo={gestorSaldo}
              gestorSecao={gestorSecao}
              setGestorSecao={setGestorSecao}
              rankLabels={RANK_LABELS}
              formatBRL={formatBRL}
            />
          </>
        )}
    </div>
  );
}
