import React, { useState } from 'react';
import api from '../api';
import toast from 'react-hot-toast';
import './CalculadoraRacaoNova.css';

/**
 * Calculadora de Ração - NOVA VERSÃO
 * ====================================
 * Interface simples para acessar a NOVA BASE de cálculo de ração.
 * 
 * IMPORTANTE:
 * - Esta é uma tela NOVA que coexiste com a calculadora antiga
 * - Usa o endpoint interno: POST /internal/racao/calcular
 * - NÃO substitui a calculadora antiga
 * - Serve para validação, uso interno e futura integração com IA
 */
export default function CalculadoraRacaoNova() {
    const [loading, setLoading] = useState(false);
    
    // Formulário simples
    const [form, setForm] = useState({
        especie: 'cao',
        peso_kg: '',
        fase: 'adulto',
        porte: 'medio',
        tipo_racao: 'premium',
        peso_pacote_kg: '',
        preco_pacote: ''
    });
    
    // Resultado
    const [resultado, setResultado] = useState(null);

    // Função de cálculo
    const calcular = async () => {
        // Validações básicas
        if (!form.peso_kg || parseFloat(form.peso_kg) <= 0) {
            toast.error('Informe o peso do animal (maior que 0)');
            return;
        }
        if (!form.peso_pacote_kg || parseFloat(form.peso_pacote_kg) <= 0) {
            toast.error('Informe o peso do pacote (maior que 0)');
            return;
        }
        if (!form.preco_pacote || parseFloat(form.preco_pacote) < 0) {
            toast.error('Informe o preço do pacote (não pode ser negativo)');
            return;
        }

        try {
            setLoading(true);
            
            // Chama o endpoint interno da NOVA BASE
            const response = await api.post('/internal/racao/calcular', {
                especie: form.especie,
                peso_kg: parseFloat(form.peso_kg),
                fase: form.fase,
                porte: form.porte,
                tipo_racao: form.tipo_racao,
                peso_pacote_kg: parseFloat(form.peso_pacote_kg),
                preco_pacote: parseFloat(form.preco_pacote)
            });
            
            setResultado(response.data);
            toast.success('✅ Cálculo realizado com sucesso!');
            
        } catch (error) {
            console.error('Erro ao calcular:', error);
            const errorMsg = error.response?.data?.detail?.message || 
                           error.response?.data?.detail || 
                           'Erro ao calcular consumo de ração';
            toast.error(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    const limpar = () => {
        setForm({
            especie: 'cao',
            peso_kg: '',
            fase: 'adulto',
            porte: 'medio',
            tipo_racao: 'premium',
            peso_pacote_kg: '',
            preco_pacote: ''
        });
        setResultado(null);
    };

    return (
        <div className="calculadora-racao-nova-container">
            <div className="header-nova">
                <div className="title-wrapper">
                    <h1>🥫 Calculadora de Ração (Nova)</h1>
                    <span className="badge-nova">NOVA VERSÃO</span>
                </div>
                <p>Interface simples para cálculo de consumo e custos</p>
                <div className="info-badge-nova">
                    ℹ️ Versão independente - Usa nova base de cálculo (preparada para IA)
                </div>
            </div>

            <div className="calculadora-grid-nova">
                {/* Formulário */}
                <div className="form-card-nova">
                    <h2>📝 Dados do Animal</h2>
                    
                    <div className="form-group-nova">
                        <label>Espécie *</label>
                        <select
                            value={form.especie}
                            onChange={(e) => setForm({...form, especie: e.target.value})}
                            className="form-select-nova"
                        >
                            <option value="cao">🐶 Cão</option>
                            <option value="gato">🐱 Gato</option>
                        </select>
                    </div>

                    <div className="form-group-nova">
                        <label>Peso do Animal (kg) *</label>
                        <input
                            type="number"
                            step="0.1"
                            min="0"
                            value={form.peso_kg}
                            onChange={(e) => setForm({...form, peso_kg: e.target.value})}
                            placeholder="Ex: 15.5"
                            className="form-input-nova"
                        />
                    </div>

                    <div className="form-group-nova">
                        <label>Fase de Vida *</label>
                        <select
                            value={form.fase}
                            onChange={(e) => setForm({...form, fase: e.target.value})}
                            className="form-select-nova"
                        >
                            <option value="filhote">Filhote</option>
                            <option value="adulto">Adulto</option>
                            <option value="idoso">Idoso</option>
                        </select>
                    </div>

                    <div className="form-group-nova">
                        <label>Porte *</label>
                        <select
                            value={form.porte}
                            onChange={(e) => setForm({...form, porte: e.target.value})}
                            className="form-select-nova"
                        >
                            <option value="mini">Mini (até 5kg)</option>
                            <option value="pequeno">Pequeno (5-10kg)</option>
                            <option value="medio">Médio (10-25kg)</option>
                            <option value="grande">Grande (25kg+)</option>
                        </select>
                    </div>

                    <hr className="divider-nova" />

                    <h3>🥫 Dados da Ração</h3>

                    <div className="form-group-nova">
                        <label>Tipo de Ração *</label>
                        <select
                            value={form.tipo_racao}
                            onChange={(e) => setForm({...form, tipo_racao: e.target.value})}
                            className="form-select-nova"
                        >
                            <option value="standard">Standard</option>
                            <option value="premium">Premium</option>
                            <option value="super_premium">Super Premium</option>
                        </select>
                        <small className="form-hint-nova">
                            Rações premium são mais calóricas, logo precisa menor quantidade
                        </small>
                    </div>

                    <div className="form-group-nova">
                        <label>Peso do Pacote (kg) *</label>
                        <input
                            type="number"
                            step="0.1"
                            min="0"
                            value={form.peso_pacote_kg}
                            onChange={(e) => setForm({...form, peso_pacote_kg: e.target.value})}
                            placeholder="Ex: 10.5"
                            className="form-input-nova"
                        />
                    </div>

                    <div className="form-group-nova">
                        <label>Preço do Pacote (R$) *</label>
                        <input
                            type="number"
                            step="0.01"
                            min="0"
                            value={form.preco_pacote}
                            onChange={(e) => setForm({...form, preco_pacote: e.target.value})}
                            placeholder="Ex: 180.00"
                            className="form-input-nova"
                        />
                    </div>

                    <div className="button-group-nova">
                        <button 
                            onClick={calcular} 
                            disabled={loading} 
                            className="btn-primary-nova"
                        >
                            {loading ? '⏳ Calculando...' : '📊 Calcular'}
                        </button>
                        <button 
                            onClick={limpar} 
                            disabled={loading}
                            className="btn-secondary-nova"
                        >
                            🔄 Limpar
                        </button>
                    </div>
                </div>

                {/* Resultado */}
                {resultado && (
                    <div className="result-card-nova">
                        <h2>📊 Resultado do Cálculo</h2>
                        
                        <div className="result-summary-nova">
                            <div className="summary-item-nova primary">
                                <span className="icon">🍽️</span>
                                <div>
                                    <strong>Consumo Diário</strong>
                                    <p className="value">{resultado.consumo_diario_gramas}g</p>
                                </div>
                            </div>

                            <div className="summary-item-nova">
                                <span className="icon">⏱️</span>
                                <div>
                                    <strong>Durabilidade</strong>
                                    <p className="value">{resultado.duracao_pacote_dias} dias</p>
                                    <small>({(resultado.duracao_pacote_dias / 30).toFixed(1)} meses)</small>
                                </div>
                            </div>

                            <div className="summary-item-nova">
                                <span className="icon">💰</span>
                                <div>
                                    <strong>Custo Diário</strong>
                                    <p className="value">R$ {resultado.custo_diario.toFixed(2)}</p>
                                </div>
                            </div>

                            <div className="summary-item-nova highlight">
                                <span className="icon">📅</span>
                                <div>
                                    <strong>Custo Mensal</strong>
                                    <p className="value">R$ {resultado.custo_mensal.toFixed(2)}</p>
                                </div>
                            </div>
                        </div>

                        <div className="result-observacoes-nova">
                            <h3>📝 Observações</h3>
                            <p>{resultado.observacoes}</p>
                        </div>

                        {/* Detalhes técnicos (opcional) */}
                        {resultado.contexto_ia?.dados_estruturados && (
                            <details className="result-details-nova">
                                <summary>🔍 Ver detalhes técnicos</summary>
                                <div className="details-content-nova">
                                    <p><strong>Custo por kg:</strong> R$ {resultado.contexto_ia.dados_estruturados.metricas?.custo_por_kg.toFixed(2)}</p>
                                    <p><strong>Gramas por real:</strong> {resultado.contexto_ia.dados_estruturados.metricas?.gramas_por_real.toFixed(2)}g</p>
                                    <p><strong>Consumo mensal:</strong> {resultado.contexto_ia.dados_estruturados.metricas?.consumo_mensal_kg.toFixed(2)}kg</p>
                                </div>
                            </details>
                        )}
                    </div>
                )}

                {!resultado && (
                    <div className="empty-state-nova">
                        <span className="empty-icon-nova">🥫</span>
                        <h3>Preencha os dados e clique em Calcular</h3>
                        <p>Os resultados aparecerão aqui</p>
                    </div>
                )}
            </div>
        </div>
    );
}
