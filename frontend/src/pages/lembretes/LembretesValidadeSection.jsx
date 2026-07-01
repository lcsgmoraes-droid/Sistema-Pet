import { FiAlertTriangle, FiPackage, FiRefreshCw, FiTrash2 } from "react-icons/fi";
import { formatarDataValidade, formatarMoeda } from "./lembretesFormatters";

export default function LembretesValidadeSection({ controller }) {
  return (
    <>
      {controller.validadeInativa && <ValidadeInativa controller={controller} />}
      {controller.validadeAtivaSemPendencias && <ValidadeAtiva controller={controller} />}
      {controller.validadePendencias.length > 0 && <ValidadePendencias controller={controller} />}
    </>
  );
}

function ValidadeInativa({ controller }) {
  return (
    <div
      style={{
        marginBottom: "20px",
        borderRadius: "12px",
        border: "1px solid var(--lembretes-warning-border, #fed7aa)",
        background: "var(--lembretes-warning-bg, #fff7ed)",
        padding: "14px 20px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "14px",
        flexWrap: "wrap",
      }}
    >
      <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
        <FiAlertTriangle style={{ color: "var(--lembretes-warning-icon, #c2410c)", marginTop: "3px" }} />
        <div>
          <p style={{ margin: "0 0 4px", fontWeight: 700, color: "var(--lembretes-warning-title, #9a3412)" }}>
            Protecao por validade desativada
          </p>
          <p style={{ margin: 0, color: "var(--lembretes-warning-text, #7c2d12)", fontSize: "13px" }}>
            Ative a protecao para retirar automaticamente os lotes que vencem em ate{" "}
            {controller.validadeConfig.dias || 15} dia(s) e gerar pendencias aqui.
          </p>
        </div>
      </div>
      <button type="button" className="btn btn-primary" onClick={controller.irConfiguracoesEstoque}>
        Abrir configuracoes
      </button>
    </div>
  );
}

function ValidadeAtiva({ controller }) {
  return (
    <div
      style={{
        marginBottom: "20px",
        borderRadius: "12px",
        border: "1px solid var(--lembretes-info-border, #bfdbfe)",
        background: "var(--lembretes-info-bg, #eff6ff)",
        padding: "14px 20px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "14px",
        flexWrap: "wrap",
      }}
    >
      <div>
        <p style={{ margin: "0 0 4px", fontWeight: 700, color: "var(--lembretes-info-title, #1d4ed8)" }}>
          Protecao por validade ativa
        </p>
        <p style={{ margin: 0, color: "var(--lembretes-info-text, #1e40af)", fontSize: "13px" }}>
          A busca automatica considera lotes que vencem em ate{" "}
          {controller.validadeConfig.dias || 15} dia(s).
        </p>
      </div>
      <VerificarValidadeButton controller={controller} />
    </div>
  );
}

function ValidadePendencias({ controller }) {
  return (
    <div
      style={{
        marginBottom: "20px",
        borderRadius: "12px",
        border: "1px solid var(--lembretes-warning-border-strong, #fbbf24)",
        overflow: "hidden",
        background: "var(--lembretes-panel-bg, #fff)",
      }}
    >
      <div
        style={{
          background: "var(--lembretes-warning-bg, #fffbeb)",
          padding: "12px 20px",
          borderBottom: "1px solid var(--lembretes-warning-border-strong, #fbbf24)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "10px",
        }}
      >
        <span style={{ fontWeight: "700", color: "var(--lembretes-warning-title, #92400e)", fontSize: "14px" }}>
          Produtos removidos por validade
        </span>
        <span style={{ fontWeight: "700", color: "var(--lembretes-warning-title, #92400e)", fontSize: "14px" }}>
          {controller.validadePendencias.length}
        </span>
        <VerificarValidadeButton controller={controller} />
      </div>
      <div style={{ padding: "14px 20px", display: "grid", gap: "10px" }}>
        {controller.validadePendencias.map((item) => (
          <ValidadePendenciaCard
            key={item.id}
            item={item}
            onResolver={controller.resolverValidade}
          />
        ))}
      </div>
    </div>
  );
}

function VerificarValidadeButton({ controller }) {
  return (
    <button
      type="button"
      className="btn btn-primary"
      disabled={controller.processandoValidade}
      onClick={() => controller.carregarValidadePendencias({ processar: true, mostrarToast: true })}
    >
      <FiRefreshCw />{" "}
      {controller.processandoValidade ? "Verificando..." : "Verificar validade agora"}
    </button>
  );
}

function ValidadePendenciaCard({ item, onResolver }) {
  return (
    <div
      style={{
        border: "1px solid var(--lembretes-warning-border, #fde68a)",
        borderRadius: "10px",
        background: "var(--lembretes-warning-bg, #fffbeb)",
        padding: "12px",
        display: "grid",
        gap: "10px",
      }}
    >
      <div
        style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}
      >
        <div>
          <p style={{ margin: "0 0 4px", color: "var(--lembretes-warning-title, #78350f)", fontWeight: 700 }}>
            {item.produto_nome || "Produto sem nome"}
          </p>
          <p style={{ margin: 0, color: "var(--lembretes-warning-text, #92400e)", fontSize: "13px" }}>
            Lote {item.lote_nome || item.lote_id} - vence em{" "}
            {formatarDataValidade(item.data_validade)}
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          <p style={{ margin: "0 0 4px", color: "var(--lembretes-warning-title, #78350f)", fontWeight: 700 }}>
            {Number(item.quantidade_bloqueada || 0).toLocaleString("pt-BR")} un.
          </p>
          <p style={{ margin: 0, color: "var(--lembretes-warning-text, #92400e)", fontSize: "13px" }}>
            Custo estimado: {formatarMoeda(item.custo_total_estimado)}
          </p>
        </div>
      </div>
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() => onResolver(item, "descartar")}
          className="btn btn-danger"
        >
          <FiTrash2 /> Descartado
        </button>
        <button
          type="button"
          onClick={() => onResolver(item, "trocar")}
          className="btn btn-primary"
        >
          <FiPackage /> Trocado
        </button>
        <button
          type="button"
          onClick={() => onResolver(item, "retornar")}
          className="btn btn-success"
        >
          <FiRefreshCw /> Retornar ao estoque
        </button>
      </div>
    </div>
  );
}
