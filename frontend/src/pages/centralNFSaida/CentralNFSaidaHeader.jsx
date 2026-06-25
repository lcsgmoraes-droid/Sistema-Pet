import { FileOutput } from "lucide-react";

export default function CentralNFSaidaHeader() {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
        <FileOutput className="w-8 h-8 text-purple-600" />
        NF de Saída
      </h1>
      <p className="text-gray-600 mt-1">
        Notas fiscais emitidas pelo PDV/Bling. Use o painel SEFAZ abaixo para consultar ou
        configurar sincronização.
      </p>
    </div>
  );
}
