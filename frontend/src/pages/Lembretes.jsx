import React, { useState, useEffect } from 'react';
import api from '../api';
import { FiTrash2, FiCheckCircle, FiRefreshCw, FiBell } from 'react-icons/fi';
import toast from 'react-hot-toast';
import '../styles/Lembretes.css';

export default function Lembretes() {
    const [lembretes, setLembretes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [filter, setFilter] = useState('pendente'); // pendente, notificado, completado, todos

    useEffect(() => {
        carregarLembretes();
        // Atualizar a cada 1 minuto
        const interval = setInterval(carregarLembretes, 60000);
        return () => clearInterval(interval);
    }, []);

    const carregarLembretes = async () => {
        setLoading(true);
        try {
            const response = await api.get('/lembretes/pendentes');
            setLembretes(response.data.lembretes || []);
        } catch (error) {
            console.error('Erro ao carregar lembretes:', error);
            toast.error('Erro ao carregar lembretes');
        } finally {
            setLoading(false);
        }
    };

    const completarLembrete = async (lembrete_id) => {
        try {
            await api.post(`/lembretes/${lembrete_id}/completar`, {});
            toast.success('Lembrete marcado como completado');
            carregarLembretes();
        } catch (error) {
            toast.error('Erro ao completar lembrete');
        }
    };

    const renovarLembrete = async (lembrete_id) => {
        try {
            await api.post(`/lembretes/${lembrete_id}/renovar`, {});
            toast.success('Lembrete renovado com sucesso');
            carregarLembretes();
        } catch (error) {
            toast.error('Erro ao renovar lembrete');
        }
    };

    const cancelarLembrete = async (lembrete_id) => {
        if (window.confirm('Tem certeza que deseja cancelar este lembrete?')) {
            try {
                await api.delete(`/lembretes/${lembrete_id}`);
                toast.success('Lembrete cancelado');
                carregarLembretes();
            } catch (error) {
                toast.error('Erro ao cancelar lembrete');
            }
        }
    };

    const proximosEmBreve = lembretes.filter(l => l.dias_restantes <= 7);
    const vencidos = lembretes.filter(l => l.dias_restantes < 0);

    return (
        <div className="lembretes-container">
            <div className="lembretes-header">
                <h1>📌 Lembretes de Recorrência</h1>
                <div className="stats-grid">
                    <div className="stat-card">
                        <span className="stat-number">{lembretes.length}</span>
                        <span className="stat-label">Total de Lembretes</span>
                    </div>
                    <div className="stat-card warning">
                        <span className="stat-number">{proximosEmBreve.length}</span>
                        <span className="stat-label">Próximos em 7 dias</span>
                    </div>
                    <div className="stat-card danger">
                        <span className="stat-number">{vencidos.length}</span>
                        <span className="stat-label">Vencidos</span>
                    </div>
                </div>
            </div>

            {loading && <div className="loading">Carregando lembretes...</div>}

            {lembretes.length === 0 ? (
                <div className="empty-state">
                    <FiBell size={48} />
                    <h2>Nenhum lembrete pendente</h2>
                    <p>Lembretes serão criados automaticamente para produtos recorrentes.</p>
                </div>
            ) : (
                <div className="lembretes-list">
                    {vencidos.length > 0 && (
                        <div className="section">
                            <h3 className="section-title danger">⚠️ Vencidos</h3>
                            {vencidos.map(l => (
                                <LembretCard 
                                    key={l.id}
                                    lembrete={l}
                                    onCompletar={completarLembrete}
                                    onRenovar={renovarLembrete}
                                    onCancelar={cancelarLembrete}
                                />
                            ))}
                        </div>
                    )}

                    {proximosEmBreve.length > 0 && (
                        <div className="section">
                            <h3 className="section-title warning">🔔 Próximos em até 7 dias</h3>
                            {proximosEmBreve.map(l => (
                                <LembretCard 
                                    key={l.id}
                                    lembrete={l}
                                    onCompletar={completarLembrete}
                                    onRenovar={renovarLembrete}
                                    onCancelar={cancelarLembrete}
                                />
                            ))}
                        </div>
                    )}

                    {lembretes.filter(l => l.dias_restantes > 7).length > 0 && (
                        <div className="section">
                            <h3 className="section-title">📅 Próximos (mais de 7 dias)</h3>
                            {lembretes.filter(l => l.dias_restantes > 7).map(l => (
                                <LembretCard 
                                    key={l.id}
                                    lembrete={l}
                                    onCompletar={completarLembrete}
                                    onRenovar={renovarLembrete}
                                    onCancelar={cancelarLembrete}
                                />
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function LembretCard({ lembrete, onCompletar, onRenovar, onCancelar }) {
    const diasRestantes = lembrete.dias_restantes;
    const dataProxima = new Date(lembrete.data_proxima_dose);
    const statusClass = diasRestantes < 0 ? 'vencido' : diasRestantes <= 7 ? 'proximo' : 'futuro';
    
    // Progresso de doses
    const temDoseTotal = lembrete.dose_total && lembrete.dose_total > 0;
    const progressoPercentual = temDoseTotal ? (lembrete.dose_atual / lembrete.dose_total) * 100 : 0;

    return (
        <div className={`lembrete-card ${statusClass}`}>
            <div className="card-content">
                <div className="card-header">
                    <h4>{lembrete.produto_nome}</h4>
                    <div className="badges">
                        {temDoseTotal && (
                            <span className="dose-badge">
                                Dose {lembrete.dose_atual}/{lembrete.dose_total}
                            </span>
                        )}
                        <span className={`status-badge ${statusClass}`}>
                            {diasRestantes < 0 ? 'VENCIDO' : `${Math.abs(diasRestantes)}d`}
                        </span>
                    </div>
                </div>

                {temDoseTotal && (
                    <div className="progress-bar-container">
                        <div className="progress-bar" style={{ width: `${progressoPercentual}%` }}></div>
                    </div>
                )}

                <div className="card-details">
                    <div className="detail-row">
                        <span className="label">Pet:</span>
                        <span className="value">{lembrete.pet_nome}</span>
                    </div>
                    <div className="detail-row">
                        <span className="label">Data:</span>
                        <span className="value">
                            {dataProxima.toLocaleDateString('pt-BR')}
                        </span>
                    </div>
                    <div className="detail-row">
                        <span className="label">Quantidade:</span>
                        <span className="value">{lembrete.quantidade}</span>
                    </div>
                    {lembrete.preco_estimado && (
                        <div className="detail-row">
                            <span className="label">Preço Est.:</span>
                            <span className="value">
                                R$ {lembrete.preco_estimado.toFixed(2)}
                            </span>
                        </div>
                    )}
                </div>
            </div>

            <div className="card-actions">
                <button
                    className="btn btn-success"
                    onClick={() => onCompletar(lembrete.id)}
                    title="Marcar como completado"
                >
                    <FiCheckCircle /> Comprado
                </button>
                <button
                    className="btn btn-primary"
                    onClick={() => onRenovar(lembrete.id)}
                    title="Renovar lembrete"
                >
                    <FiRefreshCw /> Renovar
                </button>
                <button
                    className="btn btn-danger"
                    onClick={() => onCancelar(lembrete.id)}
                    title="Cancelar lembrete"
                >
                    <FiTrash2 />
                </button>
            </div>
        </div>
    );
}
