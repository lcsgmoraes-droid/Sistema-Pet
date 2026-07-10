export default function CampanhasRankingLoteCard({ setResultadoLote, setModalLote }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-cyan-200 bg-cyan-50 p-4">
      <div>
        <p className="font-semibold text-cyan-900">Mensagem por ranking</p>
        <p className="text-sm text-cyan-700">
          Envie e-mail e notificacao no app para todos os clientes de um nivel.
        </p>
      </div>
      <button
        onClick={() => {
          setResultadoLote(null);
          setModalLote(true);
        }}
        className="rounded-lg bg-cyan-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-cyan-800"
      >
        Enviar para nivel
      </button>
    </div>
  );
}
