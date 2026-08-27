import { getGuiaInlineStyle } from "../../utils/guiaHighlight";
import EntregadorPadraoSection from "./entregasConfig/EntregadorPadraoSection";
import EnderecoLojaSection from "./entregasConfig/EnderecoLojaSection";
import MetodoDistanciaSection from "./entregasConfig/MetodoDistanciaSection";
import RegrasComerciaisSection from "./entregasConfig/RegrasComerciaisSection";
import { useEntregasConfigController } from "./entregasConfig/useEntregasConfigController";

export default function EntregasConfig() {
  const guiaAtiva = new URLSearchParams(window.location.search).get("guia");
  const destacarEntregaConfig = guiaAtiva === "entrega-config";
  const destaqueBloco = getGuiaInlineStyle(destacarEntregaConfig);
  const {
    addDistanceTier,
    buscandoCep,
    buscarCep,
    changeBillingMode,
    entregadores,
    form,
    handleSave,
    loading,
    removeDistanceTier,
    saving,
    setForm,
    updateDistanceTier,
  } = useEntregasConfigController();

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 200,
          color: "#64748b",
        }}
      >
        Carregando configurações...
      </div>
    );
  }

  return (
    <div className="page">
      {destacarEntregaConfig && (
        <div
          style={{
            marginBottom: 16,
            border: "1px solid #f59e0b",
            background: "#fffbeb",
            color: "#92400e",
            borderRadius: 10,
            padding: "10px 14px",
            fontSize: 14,
          }}
        >
          Etapa da introducao guiada: revise entregador padrao, endereco de partida e metodo de km.
          Depois clique em <strong>Salvar Configuracoes</strong>.
        </div>
      )}

      <div style={{ marginBottom: 28 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: "#1e293b" }}>
          🚚 Configurações de Entregas
        </h1>
        <p style={{ margin: "6px 0 0", fontSize: 14, color: "#64748b" }}>
          Uma única regra de entrega para o aplicativo e para o e-commerce.
        </p>
      </div>

      <form onSubmit={handleSave} style={{ maxWidth: 760 }}>
        <EntregadorPadraoSection
          destaqueBloco={destaqueBloco}
          entregadores={entregadores}
          form={form}
          setForm={setForm}
        />
        <EnderecoLojaSection
          buscandoCep={buscandoCep}
          buscarCep={buscarCep}
          destaqueBloco={destaqueBloco}
          form={form}
          setForm={setForm}
        />
        <RegrasComerciaisSection
          addDistanceTier={addDistanceTier}
          changeBillingMode={changeBillingMode}
          form={form}
          removeDistanceTier={removeDistanceTier}
          setForm={setForm}
          updateDistanceTier={updateDistanceTier}
        />
        <MetodoDistanciaSection destaqueBloco={destaqueBloco} form={form} setForm={setForm} />

        <button
          type="submit"
          disabled={saving}
          style={{
            backgroundColor: destacarEntregaConfig ? "#d97706" : "#2563eb",
            color: "white",
            padding: "12px 24px",
            border: "none",
            borderRadius: "6px",
            fontSize: "16px",
            fontWeight: "500",
            cursor: saving ? "not-allowed" : "pointer",
            opacity: saving ? 0.6 : 1,
            transition: "all 0.2s",
            boxShadow: destaqueBloco.boxShadow || "none",
          }}
          onMouseOver={(e) => {
            if (!saving)
              e.target.style.backgroundColor = destacarEntregaConfig ? "#b45309" : "#1d4ed8";
          }}
          onMouseOut={(e) => {
            if (!saving)
              e.target.style.backgroundColor = destacarEntregaConfig ? "#d97706" : "#2563eb";
          }}
        >
          {saving ? "Salvando..." : "Salvar Configurações"}
        </button>
      </form>
    </div>
  );
}
