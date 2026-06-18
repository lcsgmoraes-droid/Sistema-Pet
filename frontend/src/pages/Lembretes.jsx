import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  FiAlertTriangle,
  FiBell,
  FiCheckCircle,
  FiRefreshCw,
  FiPackage,
  FiTrash2,
} from "react-icons/fi";
import { useNavigate } from "react-router-dom";
import api from "../api";
import CustomerIdentity from "../components/ui/CustomerIdentity";
import PetIdentity from "../components/ui/PetIdentity";
import { useModulos } from "../contexts/ModulosContext";
import "../styles/Lembretes.css";

export default function Lembretes() {
  const { moduloAtivo } = useModulos();
  const [lembretes, setLembretes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [alertasCampanhas, setAlertasCampanhas] = useState(null);
  const [dresPendentes, setDresPendentes] = useState(0);
  const [autocadastrosBling, setAutocadastrosBling] = useState({ total: 0, items: [] });
  const [validadePendencias, setValidadePendencias] = useState([]);
  const [validadeConfig, setValidadeConfig] = useState({
    carregado: false,
    ativa: null,
    dias: 15,
  });
  const [processandoValidade, setProcessandoValidade] = useState(false);
  const navigate = useNavigate();
  const campanhasAtivo = moduloAtivo("campanhas");
  const financeiroErpAtivo = moduloAtivo("financeiro_erp");
  const blingAtivo = moduloAtivo("bling");

  useEffect(() => {
    carregarLembretes();
    if (campanhasAtivo) carregarAlertasCampanhas();
    else setAlertasCampanhas(null);
    if (financeiroErpAtivo) carregarDresPendentes();
    else setDresPendentes(0);
    if (blingAtivo) carregarAutocadastrosBling();
    else setAutocadastrosBling({ total: 0, items: [] });
    carregarValidadePendencias({ processar: true });
    // Atualizar a cada 1 minuto
    const interval = setInterval(() => {
      carregarLembretes();
      if (blingAtivo) carregarAutocadastrosBling();
      carregarValidadePendencias();
    }, 60000);
    return () => clearInterval(interval);
  }, [campanhasAtivo, financeiroErpAtivo, blingAtivo]);

  const carregarAutocadastrosBling = async () => {
    try {
      const res = await api.get("/integracoes/bling/nf/autocadastros-recentes", {
        params: { horas: 24, limite: 20 },
      });
      setAutocadastrosBling({
        total: Number(res.data?.total || 0),
        items: Array.isArray(res.data?.items) ? res.data.items : [],
      });
    } catch {
      setAutocadastrosBling({ total: 0, items: [] });
    }
  };

  const carregarAlertasCampanhas = async () => {
    try {
      const res = await api.get("/campanhas/dashboard");
      setAlertasCampanhas(res.data);
    } catch {
      // silencioso — alertas são informativos, não críticos
    }
  };

  const carregarDresPendentes = async () => {
    try {
      const res = await api.get("/dre/classificar/pendentes");
      setDresPendentes(res.data?.total_pendentes || 0);
    } catch {
      // silencioso
    }
  };

  const carregarValidadePendencias = async ({ processar = false, mostrarToast = false } = {}) => {
    let configAtual = { carregado: false, ativa: null, dias: 15 };

    try {
      const configRes = await api.get("/empresa/config-estoque");
      configAtual = {
        carregado: true,
        ativa: Boolean(configRes.data?.protecao_validade_ativa),
        dias: Number(configRes.data?.dias_alerta_validade || 15),
      };
      setValidadeConfig(configAtual);
    } catch {
      setValidadeConfig((prev) => ({
        ...prev,
        carregado: false,
        ativa: null,
      }));
    }

    if (processar && configAtual.ativa === true) {
      setProcessandoValidade(true);
      try {
        const processRes = await api.post("/estoque/validade/processar");
        const processados = Number(processRes.data?.processados || 0);
        if (mostrarToast) {
          toast.success(
            processados > 0
              ? `${processados} lote(s) removido(s) do estoque vendavel`
              : "Nenhum lote novo em risco encontrado",
          );
        }
      } catch (error) {
        console.error("Erro ao processar validade:", error);
        if (mostrarToast) toast.error("Nao foi possivel verificar validade agora");
      } finally {
        setProcessandoValidade(false);
      }
    } else if (processar && mostrarToast && configAtual.ativa === false) {
      toast("Ative a protecao por validade nas configuracoes de estoque.");
    }

    try {
      const res = await api.get("/estoque/validade/pendencias");
      setValidadePendencias(Array.isArray(res.data?.items) ? res.data.items : []);
    } catch {
      setValidadePendencias([]);
    }
  };

  const carregarLembretes = async () => {
    setLoading(true);
    try {
      const response = await api.get("/lembretes/pendentes");
      setLembretes(response.data.lembretes || []);
    } catch (error) {
      console.error("Erro ao carregar lembretes:", error);
      toast.error("Erro ao carregar lembretes");
    } finally {
      setLoading(false);
    }
  };

  const completarLembrete = async (lembrete_id) => {
    try {
      await api.post(`/lembretes/${lembrete_id}/completar`, {});
      toast.success("Lembrete marcado como completado");
      carregarLembretes();
    } catch {
      toast.error("Erro ao completar lembrete");
    }
  };

  const renovarLembrete = async (lembrete_id) => {
    try {
      await api.post(`/lembretes/${lembrete_id}/renovar`, {});
      toast.success("Lembrete renovado com sucesso");
      carregarLembretes();
    } catch {
      toast.error("Erro ao renovar lembrete");
    }
  };

  const cancelarLembrete = async (lembrete_id) => {
    if (window.confirm("Tem certeza que deseja cancelar este lembrete?")) {
      try {
        await api.delete(`/lembretes/${lembrete_id}`);
        toast.success("Lembrete cancelado");
        carregarLembretes();
      } catch {
        toast.error("Erro ao cancelar lembrete");
      }
    }
  };

  const resolverValidade = async (item, acao) => {
    const endpoints = {
      descartar: "descartar",
      trocar: "trocar-fornecedor",
      retornar: "retornar-vendavel",
    };
    const mensagens = {
      descartar: "Registrar este lote como descartado e prejuizo?",
      trocar: "Registrar este lote como trocado com o fornecedor?",
      retornar: "Retornar este lote para o estoque vendavel?",
    };

    if (!endpoints[acao]) return;
    if (!window.confirm(mensagens[acao])) return;

    try {
      await api.post(`/estoque/validade/${item.id}/${endpoints[acao]}`, {
        observacao: null,
      });
      toast.success("Pendencia de validade atualizada");
      carregarValidadePendencias();
    } catch (error) {
      console.error("Erro ao resolver pendencia de validade:", error);
      toast.error("Erro ao atualizar pendencia de validade");
    }
  };

  const proximosEmBreve = lembretes.filter((l) => l.dias_restantes <= 7);
  const vencidos = lembretes.filter((l) => l.dias_restantes < 0);
  const semPendencias = lembretes.length === 0 && validadePendencias.length === 0;
  const validadeInativa = validadeConfig.carregado && validadeConfig.ativa === false;
  const validadeAtivaSemPendencias =
    validadeConfig.ativa === true && validadePendencias.length === 0;

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

      {/* ── Alertas de Campanhas ── */}
      {alertasCampanhas && (
        <div
          style={{
            marginBottom: "20px",
            borderRadius: "12px",
            border: "1px solid #e5e7eb",
            overflow: "hidden",
            background: "#fff",
          }}
        >
          <div
            style={{
              background: "#fef3c7",
              padding: "12px 20px",
              borderBottom: "1px solid #fde68a",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <span style={{ fontSize: "16px" }}>🔔</span>
            <span style={{ fontWeight: "600", color: "#92400e", fontSize: "14px" }}>
              Alertas de Campanhas
            </span>
          </div>
          <div
            style={{
              padding: "12px 20px",
              display: "flex",
              flexWrap: "wrap",
              gap: "12px",
            }}
          >
            {/* Aniversários amanhã */}
            {alertasCampanhas.proximos_eventos?.total_aniversarios_amanha > 0 && (
              <div
                style={{
                  background: "#fdf2f8",
                  border: "1px solid #f9a8d4",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "180px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#9d174d",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.proximos_eventos.total_aniversarios_amanha}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 6px",
                  }}
                >
                  🎂 Aniversário(s) amanhã
                </p>
                <div>
                  {alertasCampanhas.proximos_eventos.aniversarios_amanha.slice(0, 3).map((a, i) => (
                    <p
                      key={i}
                      style={{
                        fontSize: "12px",
                        color: "#374151",
                        margin: "1px 0",
                      }}
                    >
                      {a.tipo === "pet" ? "🐕" : "👤"} {a.nome}
                    </p>
                  ))}
                  {alertasCampanhas.proximos_eventos.total_aniversarios_amanha > 3 && (
                    <p
                      style={{
                        fontSize: "11px",
                        color: "#9ca3af",
                        margin: "2px 0 0",
                      }}
                    >
                      +{alertasCampanhas.proximos_eventos.total_aniversarios_amanha - 3} mais
                    </p>
                  )}
                </div>
              </div>
            )}
            {/* Aniversários de hoje */}
            {alertasCampanhas.total_aniversarios > 0 && (
              <div
                style={{
                  background: "#fff7ed",
                  border: "1px solid #fed7aa",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "180px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#c2410c",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.total_aniversarios}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 6px",
                  }}
                >
                  🎉 Aniversário(s) hoje
                </p>
                <div>
                  {alertasCampanhas.aniversarios_hoje.slice(0, 3).map((a, i) => (
                    <p
                      key={i}
                      style={{
                        fontSize: "12px",
                        color: "#374151",
                        margin: "1px 0",
                      }}
                    >
                      {a.tipo === "pet" ? "🐕" : "👤"} {a.nome}
                    </p>
                  ))}
                </div>
              </div>
            )}
            {/* Clientes inativos */}
            {alertasCampanhas.alertas?.inativos_30d > 0 && (
              <div
                style={{
                  background: "#fff7ed",
                  border: "1px solid #fdba74",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "160px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#c2410c",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.alertas.inativos_30d}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 0",
                  }}
                >
                  😴 Inativos há +30 dias
                </p>
              </div>
            )}
            {/* Novos inativos hoje */}
            {alertasCampanhas.alertas?.novos_inativos_hoje > 0 && (
              <div
                style={{
                  background: "#fef2f2",
                  border: "1px solid #fca5a5",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "160px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#b91c1c",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.alertas.novos_inativos_hoje}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 0",
                  }}
                >
                  🚨 Atingiram 30 dias de inatividade hoje
                </p>
              </div>
            )}
            {/* Sorteios pendentes */}
            {alertasCampanhas.alertas?.total_sorteios_pendentes > 0 && (
              <div
                style={{
                  background: "#fefce8",
                  border: "1px solid #fde047",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "160px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#a16207",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.alertas.total_sorteios_pendentes}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 0",
                  }}
                >
                  🎲 Sorteio(s) pendente(s)
                </p>
              </div>
            )}
            {/* Sorteios esta semana */}
            {alertasCampanhas.proximos_eventos?.sorteios_esta_semana?.length > 0 && (
              <div
                style={{
                  background: "#fffbeb",
                  border: "1px solid #fcd34d",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "180px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#92400e",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.proximos_eventos.sorteios_esta_semana.length}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 6px",
                  }}
                >
                  🎯 Sorteio(s) esta semana
                </p>
                <div>
                  {alertasCampanhas.proximos_eventos.sorteios_esta_semana
                    .slice(0, 3)
                    .map((s, i) => (
                      <p
                        key={i}
                        style={{
                          fontSize: "12px",
                          color: "#374151",
                          margin: "1px 0",
                        }}
                      >
                        {s.name}
                        {s.draw_date
                          ? ` • ${new Date(s.draw_date).toLocaleDateString("pt-BR")}`
                          : ""}
                      </p>
                    ))}
                </div>
              </div>
            )}
            {/* Brindes pendentes de retirada */}
            {alertasCampanhas.alertas?.total_brindes_pendentes > 0 && (
              <div
                style={{
                  background: "#fff7ed",
                  border: "1px solid #fdba74",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "180px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color: "#c2410c",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.alertas.total_brindes_pendentes}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 6px",
                  }}
                >
                  🎁 Brinde(s) pendente(s) de retirada
                </p>
                <div>
                  {alertasCampanhas.alertas.brindes_pendentes.slice(0, 2).map((b, i) => (
                    <p
                      key={i}
                      style={{
                        fontSize: "12px",
                        color: "#374151",
                        margin: "1px 0",
                      }}
                    >
                      <CustomerIdentity
                        code={b.customer_id}
                        fallback="Cliente nao informado"
                        layout="inline"
                        name={b.nome_cliente}
                        nameClassName="font-medium text-slate-700"
                        record={b}
                      />
                      {b.retirar_ate
                        ? ` • até ${new Date(b.retirar_ate).toLocaleDateString("pt-BR")}`
                        : ""}
                    </p>
                  ))}
                  {alertasCampanhas.alertas.total_brindes_pendentes > 2 && (
                    <p
                      style={{
                        fontSize: "11px",
                        color: "#9ca3af",
                        margin: "2px 0 0",
                      }}
                    >
                      +{alertasCampanhas.alertas.total_brindes_pendentes - 2} mais
                    </p>
                  )}
                </div>
              </div>
            )}
            {/* Fim do mês - sempre visível */}
            {alertasCampanhas.proximos_eventos?.dias_ate_fim_mes != null && (
              <div
                style={{
                  background:
                    alertasCampanhas.proximos_eventos.dias_ate_fim_mes <= 3 ? "#fefce8" : "#f0fdf4",
                  border:
                    alertasCampanhas.proximos_eventos.dias_ate_fim_mes <= 3
                      ? "1px solid #fde047"
                      : "1px solid #86efac",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  minWidth: "160px",
                }}
              >
                <p
                  style={{
                    fontWeight: "700",
                    color:
                      alertasCampanhas.proximos_eventos.dias_ate_fim_mes <= 3
                        ? "#a16207"
                        : "#15803d",
                    fontSize: "22px",
                    margin: 0,
                  }}
                >
                  {alertasCampanhas.proximos_eventos.dias_ate_fim_mes}
                </p>
                <p
                  style={{
                    color: "#6b7280",
                    fontSize: "12px",
                    margin: "2px 0 0",
                  }}
                >
                  🌟{" "}
                  {alertasCampanhas.proximos_eventos.dias_ate_fim_mes === 0
                    ? "Último dia — calcule o destaque!"
                    : `dia(s) p/ Destaque Mensal`}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Aviso 24h: autocadastros criados via NF Bling ── */}
      {autocadastrosBling.total > 0 && (
        <div
          style={{
            marginBottom: "20px",
            borderRadius: "12px",
            border: "1px solid #86efac",
            overflow: "hidden",
            background: "#fff",
          }}
        >
          <div
            style={{
              background: "#dcfce7",
              padding: "12px 20px",
              borderBottom: "1px solid #86efac",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "10px",
              flexWrap: "wrap",
            }}
          >
            <span style={{ fontWeight: "700", color: "#166534", fontSize: "14px" }}>
              ✅ Auto cadastro Bling (últimas 24h)
            </span>
            <span style={{ fontWeight: "700", color: "#166534", fontSize: "14px" }}>
              {autocadastrosBling.total}
            </span>
          </div>
          <div style={{ padding: "12px 20px" }}>
            <p style={{ margin: "0 0 8px", color: "#065f46", fontSize: "13px" }}>
              O sistema já identificou SKU sem cadastro, criou o produto e seguiu com a baixa
              automaticamente. Este aviso some sozinho após 1 dia.
            </p>
            <div style={{ display: "grid", gap: "6px" }}>
              {autocadastrosBling.items.slice(0, 8).map((item) => (
                <button
                  key={item.produto_id}
                  type="button"
                  style={{
                    width: "100%",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    background: "#f0fdf4",
                    border: "1px solid #bbf7d0",
                    borderRadius: "8px",
                    padding: "8px 10px",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                  onClick={() =>
                    navigate(`/produtos?busca=${encodeURIComponent(item.codigo || "")}`)
                  }
                >
                  <span style={{ fontSize: "13px", color: "#14532d" }}>
                    {item.codigo} - {item.nome}
                  </span>
                  <span style={{ fontSize: "12px", color: "#166534" }}>
                    {item.created_at ? new Date(item.created_at).toLocaleString("pt-BR") : "agora"}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Alerta DRE: lançamentos sem classificação ── */}
      {dresPendentes > 0 && (
        <div
          style={{
            marginBottom: "20px",
            borderRadius: "12px",
            border: "1px solid #c4b5fd",
            overflow: "hidden",
            background: "#fff",
          }}
        >
          <div
            style={{
              background: "#ede9fe",
              padding: "12px 20px",
              borderBottom: "1px solid #c4b5fd",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <span style={{ fontSize: "16px" }}>🏷️</span>
            <span style={{ fontWeight: "600", color: "#5b21b6", fontSize: "14px" }}>
              DRE — Lançamentos pendentes de classificação
            </span>
          </div>
          <div
            style={{
              padding: "14px 20px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "16px",
              flexWrap: "wrap",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <p
                style={{
                  fontWeight: "700",
                  color: "#7c3aed",
                  fontSize: "28px",
                  margin: 0,
                  lineHeight: 1,
                }}
              >
                {dresPendentes}
              </p>
              <p style={{ color: "#4b5563", fontSize: "13px", margin: 0 }}>
                lançamento{dresPendentes !== 1 ? "s" : ""} sem categoria DRE.
                <br />O DRE pode estar incompleto ou incorreto.
              </p>
            </div>
            <button
              onClick={() => navigate("/financeiro/dre")}
              style={{
                background: "linear-gradient(to right, #7c3aed, #4f46e5)",
                color: "#fff",
                border: "none",
                borderRadius: "8px",
                padding: "8px 18px",
                fontWeight: "600",
                fontSize: "13px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                whiteSpace: "nowrap",
              }}
            >
              🏷️ Ir para o DRE e Classificar
            </button>
          </div>
        </div>
      )}

      {validadeInativa && (
        <div
          style={{
            marginBottom: "20px",
            borderRadius: "12px",
            border: "1px solid #fed7aa",
            background: "#fff7ed",
            padding: "14px 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "14px",
            flexWrap: "wrap",
          }}
        >
          <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
            <FiAlertTriangle style={{ color: "#c2410c", marginTop: "3px" }} />
            <div>
              <p style={{ margin: "0 0 4px", fontWeight: 700, color: "#9a3412" }}>
                Protecao por validade desativada
              </p>
              <p style={{ margin: 0, color: "#7c2d12", fontSize: "13px" }}>
                Ative a protecao para retirar automaticamente os lotes que vencem em ate{" "}
                {validadeConfig.dias || 15} dia(s) e gerar pendencias aqui.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => navigate("/configuracoes/estoque")}
          >
            Abrir configuracoes
          </button>
        </div>
      )}

      {validadeAtivaSemPendencias && (
        <div
          style={{
            marginBottom: "20px",
            borderRadius: "12px",
            border: "1px solid #bfdbfe",
            background: "#eff6ff",
            padding: "14px 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "14px",
            flexWrap: "wrap",
          }}
        >
          <div>
            <p style={{ margin: "0 0 4px", fontWeight: 700, color: "#1d4ed8" }}>
              Protecao por validade ativa
            </p>
            <p style={{ margin: 0, color: "#1e40af", fontSize: "13px" }}>
              A busca automatica considera lotes que vencem em ate {validadeConfig.dias || 15}{" "}
              dia(s).
            </p>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            disabled={processandoValidade}
            onClick={() => carregarValidadePendencias({ processar: true, mostrarToast: true })}
          >
            <FiRefreshCw /> {processandoValidade ? "Verificando..." : "Verificar validade agora"}
          </button>
        </div>
      )}

      {validadePendencias.length > 0 && (
        <div
          style={{
            marginBottom: "20px",
            borderRadius: "12px",
            border: "1px solid #fbbf24",
            overflow: "hidden",
            background: "#fff",
          }}
        >
          <div
            style={{
              background: "#fffbeb",
              padding: "12px 20px",
              borderBottom: "1px solid #fbbf24",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "10px",
            }}
          >
            <span style={{ fontWeight: "700", color: "#92400e", fontSize: "14px" }}>
              Produtos removidos por validade
            </span>
            <span style={{ fontWeight: "700", color: "#92400e", fontSize: "14px" }}>
              {validadePendencias.length}
            </span>
            <button
              type="button"
              className="btn btn-primary"
              disabled={processandoValidade}
              onClick={() => carregarValidadePendencias({ processar: true, mostrarToast: true })}
            >
              <FiRefreshCw /> {processandoValidade ? "Verificando..." : "Verificar validade agora"}
            </button>
          </div>
          <div style={{ padding: "14px 20px", display: "grid", gap: "10px" }}>
            {validadePendencias.map((item) => (
              <div
                key={item.id}
                style={{
                  border: "1px solid #fde68a",
                  borderRadius: "10px",
                  background: "#fffbeb",
                  padding: "12px",
                  display: "grid",
                  gap: "10px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "12px",
                    flexWrap: "wrap",
                  }}
                >
                  <div>
                    <p style={{ margin: "0 0 4px", color: "#78350f", fontWeight: 700 }}>
                      {item.produto_nome || "Produto sem nome"}
                    </p>
                    <p style={{ margin: 0, color: "#92400e", fontSize: "13px" }}>
                      Lote {item.lote_nome || item.lote_id} - vence em{" "}
                      {formatarDataValidade(item.data_validade)}
                    </p>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <p style={{ margin: "0 0 4px", color: "#78350f", fontWeight: 700 }}>
                      {Number(item.quantidade_bloqueada || 0).toLocaleString("pt-BR")} un.
                    </p>
                    <p style={{ margin: 0, color: "#92400e", fontSize: "13px" }}>
                      Custo estimado: {formatarMoeda(item.custo_total_estimado)}
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={() => resolverValidade(item, "descartar")}
                    className="btn btn-danger"
                  >
                    <FiTrash2 /> Descartado
                  </button>
                  <button
                    type="button"
                    onClick={() => resolverValidade(item, "trocar")}
                    className="btn btn-primary"
                  >
                    <FiPackage /> Trocado
                  </button>
                  <button
                    type="button"
                    onClick={() => resolverValidade(item, "retornar")}
                    className="btn btn-success"
                  >
                    <FiRefreshCw /> Retornar ao estoque
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && <div className="loading">Carregando lembretes...</div>}

      {semPendencias ? (
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
              {vencidos.map((l) => (
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
              {proximosEmBreve.map((l) => (
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

          {lembretes.filter((l) => l.dias_restantes > 7).length > 0 && (
            <div className="section">
              <h3 className="section-title">📅 Próximos (mais de 7 dias)</h3>
              {lembretes
                .filter((l) => l.dias_restantes > 7)
                .map((l) => (
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

function formatarDataValidade(data) {
  if (!data) return "sem data";
  return new Date(data).toLocaleDateString("pt-BR");
}

function formatarMoeda(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function LembretCard({ lembrete, onCompletar, onRenovar, onCancelar }) {
  const diasRestantes = lembrete.dias_restantes;
  const dataProxima = new Date(lembrete.data_proxima_dose);
  const statusClass = diasRestantes < 0 ? "vencido" : diasRestantes <= 7 ? "proximo" : "futuro";

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
              {diasRestantes < 0 ? "VENCIDO" : `${Math.abs(diasRestantes)}d`}
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
            <span className="value">
              <PetIdentity
                fallback=""
                layout="inline"
                nameClassName="font-medium"
                record={lembrete}
              />
            </span>
          </div>
          <div className="detail-row">
            <span className="label">Data:</span>
            <span className="value">{dataProxima.toLocaleDateString("pt-BR")}</span>
          </div>
          <div className="detail-row">
            <span className="label">Quantidade:</span>
            <span className="value">{lembrete.quantidade}</span>
          </div>
          {lembrete.preco_estimado && (
            <div className="detail-row">
              <span className="label">Preço Est.:</span>
              <span className="value">R$ {lembrete.preco_estimado.toFixed(2)}</span>
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
