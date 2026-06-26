import CupomTransferenciaPrintArea from "./CupomTransferenciaPrintArea";
import HistoricoTransferenciaFilters from "./HistoricoTransferenciaFilters";
import HistoricoTransferenciaResults from "./HistoricoTransferenciaResults";
import LancamentoTransferenciaParceiro from "./LancamentoTransferenciaParceiro";
import ModalDocumentoTransferenciaParceiro from "./ModalDocumentoTransferenciaParceiro";
import TransferenciaParceiroHeader from "./TransferenciaParceiroHeader";
import useEstoqueTransferenciaParceiroController from "./useEstoqueTransferenciaParceiroController";

export default function EstoqueTransferenciaParceiroPage() {
  const {
    cupomTransferencia,
    modalDocumentoTransferenciaProps,
    headerProps,
    abaAtiva,
    lancamentoProps,
    historicoFiltersProps,
    historicoResultsProps,
  } = useEstoqueTransferenciaParceiroController();

  return (
    <div className="space-y-6 p-6">
      <CupomTransferenciaPrintArea cupomTransferencia={cupomTransferencia} />
      <ModalDocumentoTransferenciaParceiro {...modalDocumentoTransferenciaProps} />
      <TransferenciaParceiroHeader {...headerProps} />

      {abaAtiva === "lancamento" ? (
        <LancamentoTransferenciaParceiro {...lancamentoProps} />
      ) : (
        <section className="rounded-3xl border border-gray-200 bg-white shadow-sm">
          <HistoricoTransferenciaFilters {...historicoFiltersProps} />
          <HistoricoTransferenciaResults {...historicoResultsProps} />
        </section>
      )}
    </div>
  );
}
