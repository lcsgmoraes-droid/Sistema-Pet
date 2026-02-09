/**
 * DETALHE DE COMISSÃO - SNAPSHOT IMUTÁVEL
 * 
 * ⚠️ IMPORTANTE: Este componente exibe um snapshot financeiro imutável.
 * Todos os valores foram registrados no momento da venda e NÃO podem ser alterados.
 * 
 * Criado em: 22/01/2026
 */

import React, { useState, useEffect } from 'react';
import api from '../../api';

const ComissaoDetalhe = ({ comissaoId, onClose }) => {
  const [comissao, setComissao] = useState(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    if (comissaoId) {
      carregarDetalhe();
    }
  }, [comissaoId]);

  // Fechar com ESC
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const carregarDetalhe = async () => {
    try {
      setLoading(true);
      setErro(null);

      const response = await api.get(`/comissoes/comissao/${comissaoId}`);

      if (response.data.success) {
        setComissao(response.data.comissao);
      } else {
        setErro('Erro ao carregar detalhes da comissão');
      }
    } catch (error) {
      console.error('Erro ao carregar detalhe:', error);
      setErro(error.response?.data?.detail || 'Erro ao conectar com o servidor');
    } finally {
      setLoading(false);
    }
  };

  // Formatar data
  const formatarData = (dataISO) => {
    if (!dataISO) return '-';
    const data = new Date(dataISO);
    return data.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Formatar moeda
  const formatarMoeda = (valor) => {
    if (valor === null || valor === undefined) return 'R$ 0,00';
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };

  // Formatar percentual
  const formatarPercentual = (valor) => {
    if (valor === null || valor === undefined) return '0%';
    return `${valor.toFixed(1)}%`;
  };

  // Badge de status
  const renderizarStatus = (status) => {
    const cores = {
      'pendente': 'bg-yellow-100 text-yellow-800',
      'pago': 'bg-green-100 text-green-800',
      'estornado': 'bg-red-100 text-red-800'
    };

    const classe = cores[status] || 'bg-gray-100 text-gray-800';

    return (
      <span className={`px-3 py-1 rounded-full text-sm font-medium ${classe}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  // Campo de exibição
  const Campo = ({ label, valor, destaque = false }) => (
    <div className="mb-4">
      <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
        {label}
      </label>
      <div className={`text-sm ${destaque ? 'text-lg font-bold text-gray-900' : 'text-gray-900'}`}>
        {valor}
      </div>
    </div>
  );

  // Seção
  const Secao = ({ titulo, children, cor = 'blue' }) => {
    const cores = {
      blue: 'border-blue-500 bg-blue-50',
      green: 'border-green-500 bg-green-50',
      purple: 'border-purple-500 bg-purple-50',
      yellow: 'border-yellow-500 bg-yellow-50',
      red: 'border-red-500 bg-red-50'
    };

    return (
      <div className="mb-6">
        <div className={`border-l-4 ${cores[cor]} px-4 py-2 mb-3`}>
          <h3 className="font-semibold text-gray-800">{titulo}</h3>
        </div>
        <div className="px-4">
          {children}
        </div>
      </div>
    );
  };

  if (!comissaoId) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 w-full md:w-2/3 lg:w-1/2 bg-white shadow-xl z-50 overflow-hidden flex flex-col">
        {/* Header fixo */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-4 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold">Detalhes da Comissão</h2>
            <p className="text-sm text-blue-100">Snapshot Imutável #{comissaoId}</p>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-blue-500 rounded-full p-2 transition"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Conteúdo com scroll */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex justify-center items-center h-64">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-gray-600">Carregando detalhes...</p>
              </div>
            </div>
          )}

          {erro && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="text-red-800 font-semibold mb-2">Erro ao carregar</h3>
              <p className="text-red-600">{erro}</p>
              <button
                onClick={carregarDetalhe}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition"
              >
                Tentar Novamente
              </button>
            </div>
          )}

          {comissao && (
            <>
              {/* SEÇÃO 1: Identificação */}
              <Secao titulo="📋 Identificação" cor="blue">
                <div className="grid grid-cols-2 gap-4">
                  <Campo label="ID da Comissão" valor={`#${comissao.id}`} />
                  <Campo label="Venda" valor={comissao.numero_venda || `#${comissao.venda_id}`} />
                  <Campo label="ID do Produto" valor={`#${comissao.produto_id}`} />
                  <Campo label="ID do Funcionário" valor={`#${comissao.funcionario_id}`} />
                  <Campo label="Data da Venda" valor={formatarData(comissao.data_venda)} />
                  <Campo label="Número da Parcela" valor={comissao.parcela_numero} />
                  <Campo label="Quantidade" valor={comissao.quantidade} />
                </div>
              </Secao>

              {/* SEÇÃO 2: Valores Financeiros */}
              <Secao titulo="💰 Valores Financeiros (Snapshot)" cor="green">
                {/* CONTEXTO DA VENDA E PAGAMENTO */}
                <div className="mb-4 p-4 bg-blue-50 border border-blue-300 rounded-lg">
                  <h4 className="font-semibold text-blue-900 mb-3 flex items-center">
                    <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Contexto do Pagamento
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-white p-3 rounded border border-blue-200">
                      <span className="text-xs text-gray-600 block mb-1">Valor Total da Venda (Produtos)</span>
                      <span className="text-lg font-bold text-blue-700">{formatarMoeda(comissao.total_venda || 0)}</span>
                    </div>
                    <div className="bg-white p-3 rounded border border-green-200">
                      <span className="text-xs text-gray-600 block mb-1">Valor Pago (Parcela {comissao.parcela_numero})</span>
                      <span className="text-lg font-bold text-green-600">{formatarMoeda(comissao.pagamento?.valor_pago_referencia || 0)}</span>
                      {comissao.pagamento?.forma_pagamento && (
                        <span className="text-xs text-gray-500 block mt-1">via {comissao.pagamento.forma_pagamento}</span>
                      )}
                    </div>
                  </div>
                  {comissao.pagamento?.percentual_pago < 100 && (
                    <div className="mt-2 text-xs text-blue-700">
                      ℹ️ Comissão calculada proporcionalmente ({formatarPercentual(comissao.pagamento.percentual_pago)} do total)
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Campo
                    label="Valor de Venda"
                    valor={formatarMoeda(comissao.valores_financeiros.valor_venda)}
                  />
                  <Campo
                    label="Valor de Custo"
                    valor={formatarMoeda(comissao.valores_financeiros.valor_custo)}
                  />
                  <Campo
                    label="Base Original (Lucro)"
                    valor={formatarMoeda(comissao.valores_financeiros.valor_base_original)}
                  />
                  <Campo
                    label="Base Comissionada"
                    valor={formatarMoeda(comissao.valores_financeiros.valor_base_comissionada)}
                  />
                </div>
                
                {/* CÁLCULO DETALHADO DA BASE */}
                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h4 className="font-semibold text-blue-900 mb-3 flex items-center">
                    <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    Como chegamos na Base de Cálculo?
                  </h4>
                  <div className="space-y-2 text-sm font-mono bg-white p-4 rounded border border-blue-200">
                    {/* Valor pago como ponto de partida */}
                    <div className="flex justify-between pb-2 border-b border-gray-200">
                      <span className="text-gray-700 font-semibold">
                        Valor Pago (Parcela {comissao.parcela_numero || 1}):
                      </span>
                      <span className="font-bold text-blue-600">
                        {formatarMoeda(comissao.pagamento?.valor_pago_referencia || comissao.valores_financeiros.valor_venda)}
                      </span>
                    </div>
                    
                    {/* RECEITA: Taxa de entrega */}
                    {comissao.deducoes && comissao.deducoes.receita_taxa_entrega > 0 && (
                      <div className="flex justify-between text-green-600 pl-4">
                        <span>(+) Taxa de Entrega (Receita):</span>
                        <span className="font-medium">+ {formatarMoeda(comissao.deducoes.receita_taxa_entrega)}</span>
                      </div>
                    )}
                    
                    {/* Deduções linha por linha */}
                    {comissao.deducoes && (
                      <>
                        {comissao.deducoes.taxa_cartao > 0 && (
                          <div className="flex justify-between text-red-600 pl-4">
                            <span>
                              (-) {(() => {
                                // Montar label dinâmico da taxa de cartão
                                const forma = comissao.deducoes.forma_pagamento || 'Cartão';
                                const parcelas = comissao.deducoes.numero_parcelas || 1;
                                let taxa_percentual = comissao.deducoes.taxa_percentual;
                                
                                // Se parcelado, buscar taxa específica do JSON
                                if (parcelas > 1 && comissao.deducoes.taxas_por_parcela) {
                                  try {
                                    const taxas = JSON.parse(comissao.deducoes.taxas_por_parcela);
                                    taxa_percentual = taxas[parcelas.toString()] || taxa_percentual;
                                  } catch (e) {}
                                }
                                
                                // Montar texto
                                let texto = 'Taxa ';
                                if (forma.includes('Crédito')) {
                                  if (parcelas > 1) {
                                    texto += `Cartão Crédito ${parcelas}x`;
                                  } else {
                                    texto += 'Cartão Crédito à Vista';
                                  }
                                } else if (forma.includes('Débito')) {
                                  texto += 'Cartão Débito';
                                } else {
                                  texto += forma;
                                }
                                
                                // Adicionar percentual se disponível
                                if (taxa_percentual) {
                                  texto += ` (${taxa_percentual}%)`;
                                }
                                
                                return texto + ':';
                              })()}
                            </span>
                            <span className="font-medium">- {formatarMoeda(comissao.deducoes.taxa_cartao)}</span>
                          </div>
                        )}
                        {comissao.deducoes.imposto > 0 && (
                          <div className="flex justify-between text-red-600 pl-4">
                            <span>(-) Impostos ({comissao.deducoes.percentual_impostos ? comissao.deducoes.percentual_impostos.toFixed(1) + '%' : ''}):</span>
                            <span className="font-medium">- {formatarMoeda(comissao.deducoes.imposto)}</span>
                          </div>
                        )}
                        {comissao.deducoes.taxa_entregador > 0 && (
                          <div className="flex justify-between text-red-600 pl-4">
                            <span>(-) Taxa paga ao Entregador:</span>
                            <span className="font-medium">- {formatarMoeda(comissao.deducoes.taxa_entregador)}</span>
                          </div>
                        )}
                        {comissao.deducoes.custo_operacional > 0 && (
                          <div className="flex justify-between text-red-600 pl-4">
                            <span>(-) Custo Operacional de Entrega:</span>
                            <span className="font-medium">- {formatarMoeda(comissao.deducoes.custo_operacional)}</span>
                          </div>
                        )}
                        {comissao.deducoes.desconto > 0 && (
                          <div className="flex justify-between text-red-600 pl-4">
                            <span>(-) Desconto:</span>
                            <span className="font-medium">- {formatarMoeda(comissao.deducoes.desconto)}</span>
                          </div>
                        )}
                      </>
                    )}
                    
                    {/* Resultado */}
                    <div className="border-t-2 border-blue-400 pt-2 mt-2 flex justify-between font-bold">
                      <span className="text-blue-900">(=) Base de Cálculo:</span>
                      <span className="text-blue-900 text-lg">{formatarMoeda(comissao.calculo.valor_base_calculo)}</span>
                    </div>
                  </div>
                </div>
              </Secao>

              {/* SEÇÃO 3: Cálculo da Comissão */}
              <Secao titulo="🧮 Cálculo da Comissão" cor="purple">
                <div className="grid grid-cols-2 gap-4">
                  <Campo
                    label="Tipo de Cálculo"
                    valor={
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                        comissao.calculo.tipo_calculo === 'percentual' 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-purple-100 text-purple-800'
                      }`}>
                        {comissao.calculo.tipo_calculo.toUpperCase()}
                      </span>
                    }
                  />
                  <Campo
                    label="Percentual da Comissão"
                    valor={formatarPercentual(comissao.calculo.percentual_comissao)}
                  />
                  <Campo
                    label="Percentual Aplicado (Pago)"
                    valor={formatarPercentual(comissao.calculo.percentual_aplicado)}
                  />
                  <Campo
                    label="Valor Base de Cálculo"
                    valor={formatarMoeda(comissao.calculo.valor_base_calculo)}
                    destaque
                  />
                  <Campo
                    label="Valor da Comissão (Total)"
                    valor={formatarMoeda(comissao.calculo.valor_comissao)}
                  />
                  <Campo
                    label="Valor Efetivamente Gerado"
                    valor={formatarMoeda(comissao.calculo.valor_comissao_gerada)}
                    destaque
                  />
                </div>
                
                {/* FÓRMULA DE CÁLCULO */}
                <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                  <h4 className="font-semibold text-purple-900 mb-3">📐 Fórmula Aplicada:</h4>
                  <div className="space-y-2 text-sm font-mono">
                    <div className="bg-white p-3 rounded border border-purple-200">
                      <div className="text-gray-700 mb-2">Base de Cálculo × Percentual = Comissão</div>
                      <div className="text-purple-900 font-bold">
                        {formatarMoeda(comissao.calculo.valor_base_calculo)} × {formatarPercentual(comissao.calculo.percentual_comissao)} = {formatarMoeda(comissao.calculo.valor_comissao)}
                      </div>
                    </div>
                    {comissao.calculo.percentual_aplicado < 100 && (
                      <div className="bg-yellow-50 p-3 rounded border border-yellow-200">
                        <div className="text-gray-700 mb-2">⚠️ Venda parcial - Comissão proporcional ao valor pago:</div>
                        <div className="text-yellow-900 font-bold">
                          {formatarMoeda(comissao.calculo.valor_comissao)} × {formatarPercentual(comissao.calculo.percentual_aplicado)} = {formatarMoeda(comissao.calculo.valor_comissao_gerada)}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </Secao>

              {/* SEÇÃO 4: Pagamento */}
              <Secao titulo="💳 Controle de Pagamento" cor="yellow">
                <div className="grid grid-cols-2 gap-4">
                  <Campo
                    label="Percentual Pago da Venda"
                    valor={formatarPercentual(comissao.pagamento.percentual_pago)}
                  />
                  <Campo
                    label="Valor Pago de Referência"
                    valor={formatarMoeda(comissao.pagamento.valor_pago_referencia)}
                  />
                  <Campo
                    label="Valor Pago da Comissão"
                    valor={formatarMoeda(comissao.pagamento.valor_pago)}
                  />
                  <Campo
                    label="Saldo Restante"
                    valor={formatarMoeda(comissao.pagamento.saldo_restante)}
                  />
                  {comissao.pagamento.data_pagamento && (
                    <>
                      <Campo
                        label="Data do Pagamento"
                        valor={formatarData(comissao.pagamento.data_pagamento)}
                      />
                      <Campo
                        label="Forma de Pagamento"
                        valor={comissao.pagamento.forma_pagamento || 'Não informado'}
                      />
                    </>
                  )}
                </div>
                {comissao.pagamento.percentual_pago < 100 && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-xs text-yellow-800">
                      ⚠️ Esta comissão foi gerada proporcionalmente ao pagamento parcial da venda.
                      Apenas {formatarPercentual(comissao.pagamento.percentual_pago)} do valor total foi pago.
                    </p>
                  </div>
                )}
              </Secao>

              {/* SEÇÃO 5: Status */}
              <Secao titulo="📊 Status e Controle" cor={comissao.status.status === 'estornado' ? 'red' : 'blue'}>
                <div className="mb-4">
                  <label className="block text-xs font-medium text-gray-500 uppercase mb-2">
                    Status Atual
                  </label>
                  {renderizarStatus(comissao.status.status)}
                </div>

                {comissao.status.status === 'estornado' && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h4 className="font-semibold text-red-800 mb-2">Informações do Estorno</h4>
                    <Campo
                      label="Data do Estorno"
                      valor={formatarData(comissao.status.data_estorno)}
                    />
                    <Campo
                      label="Motivo do Estorno"
                      valor={comissao.status.motivo_estorno || 'Não informado'}
                    />
                  </div>
                )}
                
                {comissao.status.observacao_pagamento && (
                  <div className="mt-4 bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <h4 className="font-semibold text-gray-800 mb-2">Observações</h4>
                    <p className="text-sm text-gray-600">{comissao.status.observacao_pagamento}</p>
                  </div>
                )}
              </Secao>

              {/* SEÇÃO 6: Resumo Visual do Cálculo */}
              <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white shadow-lg">
                <h3 className="text-xl font-bold mb-4 flex items-center">
                  <svg className="w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  Resumo do Cálculo Completo
                </h3>
                <div className="space-y-3 font-mono text-sm">
                  <div className="flex justify-between items-center border-b border-white/20 pb-2">
                    <span className="text-blue-100">
                      Valor Pago (Parcela {comissao.parcela_numero || 1}):
                    </span>
                    <span className="font-bold text-lg">
                      {formatarMoeda(comissao.pagamento?.valor_pago_referencia || comissao.valores_financeiros.valor_venda)}
                    </span>
                  </div>
                  
                  {/* Deduções detalhadas */}
                  {comissao.deducoes && (
                    <>
                      {comissao.deducoes.taxa_cartao > 0 && (
                        <div className="flex justify-between items-center pl-4 text-red-200">
                          <span>
                            (-) {(() => {
                              // Montar label dinâmico da taxa de cartão
                              const forma = comissao.deducoes.forma_pagamento || 'Cartão';
                              const parcelas = comissao.deducoes.numero_parcelas || 1;
                              let taxa_percentual = comissao.deducoes.taxa_percentual;
                              
                              // Se parcelado, buscar taxa específica do JSON
                              if (parcelas > 1 && comissao.deducoes.taxas_por_parcela) {
                                try {
                                  const taxas = JSON.parse(comissao.deducoes.taxas_por_parcela);
                                  taxa_percentual = taxas[parcelas.toString()] || taxa_percentual;
                                } catch (e) {}
                              }
                              
                              // Montar texto
                              let texto = 'Taxa ';
                              if (forma.includes('Crédito')) {
                                if (parcelas > 1) {
                                  texto += `Cartão Crédito ${parcelas}x`;
                                } else {
                                  texto += 'Cartão Crédito à Vista';
                                }
                              } else if (forma.includes('Débito')) {
                                texto += 'Cartão Débito';
                              } else {
                                texto += forma;
                              }
                              
                              // Adicionar percentual se disponível
                              if (taxa_percentual) {
                                texto += ` (${taxa_percentual}%)`;
                              }
                              
                              return texto + ':';
                            })()}
                          </span>
                          <span className="font-medium">- {formatarMoeda(comissao.deducoes.taxa_cartao)}</span>
                        </div>
                      )}
                      {comissao.deducoes.imposto > 0 && (
                        <div className="flex justify-between items-center pl-4 text-red-200">
                          <span>(-) Impostos:</span>
                          <span className="font-medium">- {formatarMoeda(comissao.deducoes.imposto)}</span>
                        </div>
                      )}
                      {comissao.deducoes.custo_entrega > 0 && (
                        <div className="flex justify-between items-center pl-4 text-red-200">
                          <span>(-) Custo de Entrega:</span>
                          <span className="font-medium">- {formatarMoeda(comissao.deducoes.custo_entrega)}</span>
                        </div>
                      )}
                      {comissao.deducoes.desconto > 0 && (
                        <div className="flex justify-between items-center pl-4 text-red-200">
                          <span>(-) Desconto:</span>
                          <span className="font-medium">- {formatarMoeda(comissao.deducoes.desconto)}</span>
                        </div>
                      )}
                    </>
                  )}
                  
                  <div className="flex justify-between items-center border-t-2 border-white/40 pt-2">
                    <span className="text-blue-100 font-semibold">(=) Base de Cálculo:</span>
                    <span className="font-bold text-lg">{formatarMoeda(comissao.calculo.valor_base_calculo)}</span>
                  </div>
                  
                  <div className="flex justify-between items-center border-b border-white/20 pb-2">
                    <span className="text-blue-100">(×) Percentual:</span>
                    <span className="font-bold text-lg">{formatarPercentual(comissao.calculo.percentual_comissao)}</span>
                  </div>
                  
                  <div className="flex justify-between items-center bg-white/10 rounded-lg p-3 border-2 border-yellow-300">
                    <span className="text-xl font-bold">Comissão Gerada:</span>
                    <span className="font-bold text-3xl text-yellow-300">{formatarMoeda(comissao.calculo.valor_comissao_gerada)}</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Rodapé fixo */}
        {comissao && (
          <div className="bg-blue-50 border-t border-blue-200 px-6 py-4">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-sm font-semibold text-blue-800 mb-1">
                  Snapshot Financeiro Imutável
                </p>
                <p className="text-xs text-blue-700">
                  Este é um snapshot financeiro imutável. Os valores refletem exatamente o momento da venda 
                  e não podem ser alterados. Qualquer discrepância deve ser tratada através de ajustes 
                  ou estornos, nunca por edição direta.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default ComissaoDetalhe;
