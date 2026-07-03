import PedidosCompraSugestaoHeader from "./PedidosCompraSugestaoHeader";
import PedidosCompraSugestaoTable from "./PedidosCompraSugestaoTable";

export default function PedidosCompraSugestaoModal(props) {
  const { mostrarSugestao } = props;

  if (!mostrarSugestao) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45">
      <div className="flex h-full w-full flex-col bg-white">
        <PedidosCompraSugestaoHeader {...props} />
        <PedidosCompraSugestaoTable {...props} />
      </div>
    </div>
  );
}
