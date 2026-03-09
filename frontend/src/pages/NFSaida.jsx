import { FileOutput } from 'lucide-react';
import SEFAZImportacao from './SEFAZImportacao';

export default function NFSaida() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <FileOutput className="w-8 h-8 text-purple-600" />
          NF de Saída
        </h1>
        <p className="text-gray-600 mt-1">
          Consulte notas fiscais de saída emitidas por terceiros diretamente na SEFAZ pela chave de acesso.
        </p>
      </div>
      <SEFAZImportacao />
    </div>
  );
}
