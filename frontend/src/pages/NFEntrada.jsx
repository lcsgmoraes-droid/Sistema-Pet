import { FileInput } from 'lucide-react';
import SEFAZImportacao from './SEFAZImportacao';

export default function NFEntrada() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <FileInput className="w-8 h-8 text-indigo-600" />
          NF de Entrada
        </h1>
        <p className="text-gray-600 mt-1">
          Consulte notas fiscais de entrada (compras de fornecedores) diretamente na SEFAZ pela chave de acesso.
        </p>
      </div>
      <SEFAZImportacao />
    </div>
  );
}
