import React from 'react';
import { Filter } from 'lucide-react';

const DashboardRacoesFiltros = ({
  filtros,
  mostrarFiltros,
  opcoesFiltros,
  onAplicarFiltros,
  onFiltroChange,
  onLimparFiltros,
  onToggleFiltroMultiplo,
  onToggleMostrarFiltros
}) => {
  const totalFiltrosAtivos =
    filtros.marca_ids.length +
    filtros.linhas.length +
    filtros.portes.length +
    filtros.fases.length +
    filtros.sabores.length +
    filtros.pesos.length;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Filter className="h-5 w-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">Filtros</h3>
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">
            Clique para selecionar/desmarcar
          </span>
        </div>
        <button
          onClick={onToggleMostrarFiltros}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          {mostrarFiltros ? 'Ocultar ▲' : 'Mostrar ▼'}
        </button>
      </div>

      {mostrarFiltros && (
        <>
          <div className="space-y-4 mb-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Marcas</label>
              <div className="flex flex-wrap gap-2">
                {opcoesFiltros.marcas.map((marca) => (
                  <button
                    key={marca.id}
                    onClick={() => onToggleFiltroMultiplo('marca_ids', marca.id)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      filtros.marca_ids.includes(marca.id)
                        ? 'bg-blue-600 text-white shadow-md'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {marca.nome}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Linha de Ração</label>
              <div className="flex flex-wrap gap-2">
                {opcoesFiltros.linhas.map((linha) => (
                  <button
                    key={linha.id}
                    onClick={() => onToggleFiltroMultiplo('linhas', linha.id)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      filtros.linhas.includes(linha.id)
                        ? 'bg-purple-600 text-white shadow-md'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {linha.nome}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Porte do Animal</label>
              <div className="flex flex-wrap gap-2">
                {opcoesFiltros.portes.map((porte) => (
                  <button
                    key={porte.id}
                    onClick={() => onToggleFiltroMultiplo('portes', porte.id)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      filtros.portes.includes(porte.id)
                        ? 'bg-green-600 text-white shadow-md'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {porte.nome}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Fase/Público</label>
              <div className="flex flex-wrap gap-2">
                {opcoesFiltros.fases.map((fase) => (
                  <button
                    key={fase.id}
                    onClick={() => onToggleFiltroMultiplo('fases', fase.id)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      filtros.fases.includes(fase.id)
                        ? 'bg-amber-600 text-white shadow-md'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {fase.nome}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Sabor/Proteína</label>
              <div className="flex flex-wrap gap-2">
                {opcoesFiltros.sabores.map((sabor) => (
                  <button
                    key={sabor}
                    onClick={() => onToggleFiltroMultiplo('sabores', sabor)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      filtros.sabores.includes(sabor)
                        ? 'bg-pink-600 text-white shadow-md'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {sabor}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Peso da Embalagem</label>
              <div className="flex flex-wrap gap-2">
                {opcoesFiltros.pesos.map((peso) => (
                  <button
                    key={peso}
                    onClick={() => onToggleFiltroMultiplo('pesos', peso)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      filtros.pesos.includes(peso)
                        ? 'bg-indigo-600 text-white shadow-md'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {peso} kg
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Margem Mínima (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={filtros.margem_min || ''}
                  onChange={(event) =>
                    onFiltroChange('margem_min', parseFloat(event.target.value) || null)
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  placeholder="Ex: 25"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Margem Máxima (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={filtros.margem_max || ''}
                  onChange={(event) =>
                    onFiltroChange('margem_max', parseFloat(event.target.value) || null)
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  placeholder="Ex: 50"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Início</label>
                <input
                  type="date"
                  value={filtros.data_inicio || ''}
                  onChange={(event) => onFiltroChange('data_inicio', event.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Fim</label>
                <input
                  type="date"
                  value={filtros.data_fim || ''}
                  onChange={(event) => onFiltroChange('data_fim', event.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-3 pt-4 border-t">
            <button
              onClick={onAplicarFiltros}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2 font-medium"
            >
              <Filter className="h-4 w-4" />
              Aplicar Filtros
            </button>

            <button
              onClick={onLimparFiltros}
              className="px-6 py-2.5 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 font-medium"
            >
              Limpar Tudo
            </button>

            {totalFiltrosAtivos > 0 && (
              <div className="flex items-center gap-2 ml-auto text-sm text-gray-600">
                <span className="font-semibold">{totalFiltrosAtivos}</span>
                filtros ativos
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default DashboardRacoesFiltros;
