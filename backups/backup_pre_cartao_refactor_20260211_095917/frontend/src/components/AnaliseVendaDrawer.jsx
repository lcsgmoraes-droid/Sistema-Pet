import React, { useEffect } from 'react'
import { FiX, FiDollarSign, FiTrendingDown, FiBarChart2, FiAlertCircle, FiCheckCircle, FiInfo } from 'react-icons/fi'

const AnaliseVendaDrawer = ({ mostrar, onFechar, dados, carregando }) => {
  // Fechar com tecla ESC
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape' && mostrar) {
        onFechar()
      }
    }
    
    if (mostrar) {
      window.addEventListener('keydown', handleEsc)
      return () => window.removeEventListener('keydown', handleEsc)
    }
  }, [mostrar, onFechar])

  if (!mostrar) return null

  // Função para formatar moeda
  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor || 0)
  }

  // Cor do indicador de margem
  const getCorMargem = (cor) => {
    switch (cor) {
      case 'verde':
        return 'bg-green-100 border-green-500 text-green-800'
      case 'amarelo':
        return 'bg-yellow-100 border-yellow-500 text-yellow-800'
      case 'vermelho':
        return 'bg-red-100 border-red-500 text-red-800'
      default:
        return 'bg-gray-100 border-gray-500 text-gray-800'
    }
  }

  // Ícone do alerta
  const getIconeAlerta = (tipo) => {
    switch (tipo) {
      case 'success':
        return <FiCheckCircle className="text-green-500" />
      case 'error':
        return <FiAlertCircle className="text-red-500" />
      case 'warning':
        return <FiAlertCircle className="text-yellow-500" />
      case 'info':
        return <FiInfo className="text-blue-500" />
      default:
        return <FiInfo className="text-gray-500" />
    }
  }

  return (
    <>
      {/* Overlay escuro */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onFechar}
      />
      
      {/* Drawer lateral */}
      <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-50 flex flex-col animate-slide-in-right">
        
        {/* Cabeçalho */}
        <div className="p-4 border-b bg-gradient-to-r from-blue-600 to-blue-700 text-white flex justify-between items-center">
          <div className="flex items-center gap-2">
            <FiBarChart2 className="w-5 h-5" />
            <h3 className="text-lg font-bold">Análise da Venda</h3>
          </div>
          <button 
            onClick={onFechar}
            className="hover:bg-white hover:bg-opacity-20 p-1 rounded transition-colors"
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>
        
        {/* Conteúdo */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          
          {carregando ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : dados ? (
            <>
              {/* Composição Financeira */}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div className="flex items-center gap-2 mb-3">
                  <FiDollarSign className="text-blue-600" />
                  <h4 className="font-bold text-gray-700">Composição Financeira</h4>
                </div>
                
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Valor Total dos Produtos</span>
                    <span className="font-semibold">{formatarMoeda(dados.composicao.total_produtos)}</span>
                  </div>
                  
                  {dados.composicao.desconto > 0 && (
                    <div className="flex justify-between text-red-600">
                      <span>(-) Descontos Aplicados</span>
                      <span className="font-semibold">
                        {formatarMoeda(dados.composicao.desconto)}
                        <span className="text-xs ml-1">
                          ({((dados.composicao.desconto / dados.composicao.total_produtos) * 100).toFixed(1)}%)
                        </span>
                      </span>
                    </div>
                  )}
                  
                  {dados.composicao.taxa_entrega > 0 && (
                    <div className="flex justify-between text-red-600">
                      <span>(-) Taxa de Entrega</span>
                      <span className="font-semibold">{formatarMoeda(dados.composicao.taxa_entrega)}</span>
                    </div>
                  )}
                  
                  <div className="border-t-2 border-blue-600 pt-2 mt-2">
                    <div className="flex justify-between font-bold text-blue-700">
                      <span>Subtotal</span>
                      <span>{formatarMoeda(dados.composicao.subtotal)}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Deduções */}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div className="flex items-center gap-2 mb-3">
                  <FiTrendingDown className="text-orange-600" />
                  <h4 className="font-bold text-gray-700">Deduções</h4>
                </div>
                
                <div className="space-y-2 text-sm">
                  {dados.deducoes.comissao.valor > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">
                        Comissão do Vendedor ({dados.deducoes.comissao.percentual}%)
                      </span>
                      <span className="font-semibold text-red-600">
                        {formatarMoeda(dados.deducoes.comissao.valor)}
                      </span>
                    </div>
                  )}
                  
                  {/* Taxas Percentuais por Forma de Pagamento */}
                  {dados.detalhamento_taxas && dados.detalhamento_taxas.length > 0 && (
                    <>
                      {dados.detalhamento_taxas.map((taxa, idx) => (
                        <React.Fragment key={idx}>
                          {taxa.taxa_percentual > 0 && (
                            <div className="flex justify-between">
                              <div className="flex flex-col">
                                <span className="text-gray-600">
                                  Taxa {taxa.forma} ({taxa.taxa_percentual}%)
                                </span>
                                <span className="text-xs text-gray-500">
                                  {formatarMoeda(taxa.valor_pagamento)}
                                </span>
                              </div>
                              <span className="font-semibold text-red-600">
                                {formatarMoeda(taxa.valor_taxa_percentual)}
                              </span>
                            </div>
                          )}
                          {taxa.taxa_fixa > 0 && (
                            <div className="flex justify-between">
                              <div className="flex flex-col">
                                <span className="text-gray-600">
                                  Taxa Fixa {taxa.forma}
                                </span>
                                <span className="text-xs text-gray-500">
                                  R$ {taxa.taxa_fixa.toFixed(2)}
                                </span>
                              </div>
                              <span className="font-semibold text-red-600">
                                {formatarMoeda(taxa.valor_taxa_fixa)}
                              </span>
                            </div>
                          )}
                        </React.Fragment>
                      ))}
                    </>
                  )}
                  
                  {/* Fallback para taxas sem detalhamento */}
                  {(!dados.detalhamento_taxas || dados.detalhamento_taxas.length === 0) && dados.deducoes.taxa_percentual > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Taxa Percentual</span>
                      <span className="font-semibold text-red-600">
                        {formatarMoeda(dados.deducoes.taxa_percentual)}
                      </span>
                    </div>
                  )}
                  
                  {(!dados.detalhamento_taxas || dados.detalhamento_taxas.length === 0) && dados.deducoes.taxa_fixa > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Taxa Fixa</span>
                      <span className="font-semibold text-red-600">
                        {formatarMoeda(dados.deducoes.taxa_fixa)}
                      </span>
                    </div>
                  )}
                  
                  {dados.deducoes.impostos.valor > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">
                        Impostos Estimados ({dados.deducoes.impostos.percentual}%)
                      </span>
                      <span className="font-semibold text-red-600">
                        {formatarMoeda(dados.deducoes.impostos.valor)}
                      </span>
                    </div>
                  )}
                  
                  <div className="flex justify-between">
                    <span className="text-gray-600">Custo dos Produtos</span>
                    <span className="font-semibold text-red-600">
                      {formatarMoeda(dados.deducoes.custos)}
                    </span>
                  </div>
                  
                  <div className="border-t pt-2 mt-2">
                    <div className="flex justify-between font-semibold text-gray-700">
                      <span>Total de Deduções</span>
                      <span className="text-red-600">{formatarMoeda(dados.deducoes.total_deducoes)}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Resultado Final */}
              <div className={`rounded-lg p-4 border-2 ${getCorMargem(dados.resultado.cor_indicador)}`}>
                <div className="flex items-center gap-2 mb-3">
                  <FiBarChart2 className="w-5 h-5" />
                  <h4 className="font-bold">Resultado Final</h4>
                </div>
                
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-lg font-bold">Lucro Líquido Estimado</span>
                    <span className="text-2xl font-bold">
                      {formatarMoeda(dados.resultado.lucro_liquido)}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="font-semibold">Margem Líquida</span>
                    <span className="text-xl font-bold">
                      {dados.resultado.margem_liquida.toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Alertas e Sugestões */}
              {dados.alertas && dados.alertas.length > 0 && (
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <div className="flex items-center gap-2 mb-3">
                    <FiAlertCircle className="text-purple-600" />
                    <h4 className="font-bold text-gray-700">Alertas e Sugestões</h4>
                  </div>
                  
                  <div className="space-y-2">
                    {dados.alertas.map((alerta, index) => (
                      <div 
                        key={index}
                        className={`flex items-start gap-2 p-2 rounded text-sm ${
                          alerta.tipo === 'success' ? 'bg-green-50' :
                          alerta.tipo === 'error' ? 'bg-red-50' :
                          alerta.tipo === 'warning' ? 'bg-yellow-50' :
                          'bg-blue-50'
                        }`}
                      >
                        <span className="flex-shrink-0 mt-0.5">{getIconeAlerta(alerta.tipo)}</span>
                        <span className="flex-1">
                          <span className="mr-1">{alerta.icone}</span>
                          {alerta.mensagem}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Detalhamento de Comissões */}
              {dados.detalhamento_comissoes && dados.detalhamento_comissoes.length > 0 && (
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <h4 className="font-bold text-gray-700 mb-3">Detalhamento de Comissões</h4>
                  
                  <div className="space-y-2 text-sm">
                    {dados.detalhamento_comissoes.map((item, index) => (
                      <div key={index} className="flex justify-between items-center">
                        <div className="flex-1">
                          <div className="font-medium text-gray-700">{item.produto}</div>
                          <div className="text-xs text-gray-500">{item.percentual}% de comissão</div>
                        </div>
                        <span className="font-semibold text-blue-600">
                          {formatarMoeda(item.valor)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <FiAlertCircle className="w-12 h-12 mx-auto mb-2" />
                <p>Erro ao carregar análise</p>
              </div>
            </div>
          )}
        </div>
        
        {/* Rodapé */}
        <div className="p-4 border-t bg-gray-50">
          <button 
            onClick={onFechar}
            className="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <span>Fechar</span>
            <span className="text-xs text-gray-300">(ESC)</span>
          </button>
        </div>
      </div>
      
      <style jsx>{`
        @keyframes slide-in-right {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
        
        .animate-slide-in-right {
          animation: slide-in-right 0.3s ease-out;
        }
      `}</style>
    </>
  )
}

export default AnaliseVendaDrawer
