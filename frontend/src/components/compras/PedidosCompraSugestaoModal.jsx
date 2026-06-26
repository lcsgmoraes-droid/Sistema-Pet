import PedidosCompraSugestaoHeader from "./PedidosCompraSugestaoHeader";
import PedidosCompraSugestaoTable from "./PedidosCompraSugestaoTable";

export default function PedidosCompraSugestaoModal(props) {
  const { mostrarSugestao } = props;

  if (!mostrarSugestao) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white w-full h-full flex flex-col">
        <PedidosCompraSugestaoHeader {...props} />
        <PedidosCompraSugestaoTable {...props} />
      </div>
    </div>
  );
}
