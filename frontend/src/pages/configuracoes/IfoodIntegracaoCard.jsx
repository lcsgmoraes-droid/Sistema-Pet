import { useCallback, useEffect, useState } from "react";
import {
  FiAlertTriangle,
  FiCheckCircle,
  FiEye,
  FiPackage,
  FiRefreshCw,
  FiSave,
  FiShoppingBag,
  FiWifi,
  FiXCircle,
} from "react-icons/fi";
import { api } from "../../services/api";
import IfoodPedidosPanel from "./IfoodPedidosPanel";

const initialForm = {
  merchant_id: "",
  active: false,
  catalog_source: "ecommerce",
  default_markup_percent: 0,
  stock_safety: 0,
};

function errorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return fallback;
}

function statusLabel(status) {
  if (status === "connected") return "Conexão validada";
  if (status === "error") return "Requer atenção";
  if (status === "ready") return "Pronto para testar";
  return "Configuração inicial";
}

function connectionBadgeClass(status) {
  if (status === "connected") return "bg-emerald-100 text-emerald-700";
  if (status === "error") return "bg-red-100 text-red-700";
  return "bg-amber-100 text-amber-700";
}

function messageClass(type) {
  if (type === "success") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  return "border-red-200 bg-red-50 text-red-800";
}

function actionText(action, expectedAction, pendingText, idleText) {
  return action === expectedAction ? pendingText : idleText;
}

function CatalogItem({ item }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3 text-sm">
      {item.eligible ? (
        <FiCheckCircle className="mt-0.5 shrink-0 text-emerald-600" />
      ) : (
        <FiXCircle className="mt-0.5 shrink-0 text-amber-600" />
      )}
      <div className="min-w-0">
        <p className="truncate font-medium text-slate-800 dark:text-slate-200">
          {item.name || item.payload?.name || item.sku || `Produto ${item.product_id}`}
        </p>
        <p className="text-xs text-slate-500">
          <span>SKU {item.sku || "não informado"}</span>
          {item.payload?.barcode ? <span> · Código {item.payload.barcode}</span> : null}
        </p>
        {item.errors?.length ? (
          <p className="mt-1 text-xs text-amber-700">{item.errors.join(" ")}</p>
        ) : null}
        {item.warnings?.length ? (
          <p className="mt-1 text-xs text-blue-700">{item.warnings.join(" ")}</p>
        ) : null}
      </div>
    </div>
  );
}

export default function IfoodIntegracaoCard() {
  const [data, setData] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState(null);
  const [message, setMessage] = useState(null);

  const load = useCallback(async () => {
    try {
      const response = await api.get("/integracoes/ifood/status");
      setData(response.data);
      setForm({ ...initialForm, ...response.data.config });
    } catch (error) {
      setMessage({
        type: "error",
        text: errorMessage(error, "Não foi possível consultar a integração com o iFood."),
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function updateField(event) {
    const { name, type, checked, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function save() {
    try {
      setAction("save");
      const payload = {
        ...form,
        merchant_id: form.merchant_id.trim() || null,
        default_markup_percent: Number(form.default_markup_percent || 0),
        stock_safety: Number(form.stock_safety || 0),
      };
      await api.put("/integracoes/ifood/config", payload);
      setMessage({ type: "success", text: "Configuração do iFood salva." });
      setPreview(null);
      await load();
    } catch (error) {
      setMessage({
        type: "error",
        text: errorMessage(error, "Não foi possível salvar a configuração."),
      });
    } finally {
      setAction(null);
    }
  }

  async function loadPreview() {
    try {
      setAction("preview");
      const response = await api.get("/integracoes/ifood/catalogo/preview", {
        params: { limit: 50, only_issues: true },
      });
      setPreview(response.data);
      setMessage({
        type: "success",
        text: "Prévia gerada somente para conferência. Nada foi enviado ao iFood.",
      });
    } catch (error) {
      setMessage({
        type: "error",
        text: errorMessage(error, "Não foi possível gerar a prévia do catálogo."),
      });
    } finally {
      setAction(null);
    }
  }

  async function testConnection() {
    try {
      setAction("test");
      await api.post("/integracoes/ifood/testar-conexao");
      setMessage({ type: "success", text: "Loja localizada e conexão validada no iFood." });
      await load();
    } catch (error) {
      setMessage({
        type: "error",
        text: errorMessage(error, "Não foi possível validar a conexão com o iFood."),
      });
      await load();
    } finally {
      setAction(null);
    }
  }

  async function simulateSync() {
    try {
      setAction("simulate");
      const response = await api.post("/integracoes/ifood/catalogo/sincronizar", {
        operation: "create",
        dry_run: true,
        confirm_send: false,
      });
      setPreview(response.data);
      setMessage({
        type: "success",
        text: "Simulação concluída. Nenhum anúncio foi criado ou alterado no iFood.",
      });
    } catch (error) {
      setMessage({
        type: "error",
        text: errorMessage(error, "Não foi possível simular a sincronização."),
      });
    } finally {
      setAction(null);
    }
  }

  const catalog = preview?.summary || data?.catalog || {};
  const connectionStatus = data?.config?.status || "draft";
  const connectionClass = connectionBadgeClass(connectionStatus);

  return (
    <section className="rounded-2xl border border-red-100 bg-white p-6 shadow-sm dark:border-red-950 dark:bg-slate-950">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-red-100 p-2 text-red-700 dark:bg-red-950 dark:text-red-300">
            <FiShoppingBag size={19} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">iFood</h2>
            <p className="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
              Use o cadastro do CorePet como fonte dos anúncios, preços e estoque. Nesta primeira
              fase, a publicação permanece protegida em modo de simulação.
            </p>
          </div>
        </div>
        <span
          className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${connectionClass}`}
        >
          {connectionStatus === "connected" ? <FiCheckCircle /> : <FiAlertTriangle />}
          {statusLabel(connectionStatus)}
        </span>
      </div>

      {message ? (
        <div className={`mt-4 rounded-xl border px-4 py-3 text-sm ${messageClass(message.type)}`}>
          {message.text}
        </div>
      ) : null}

      {loading ? (
        <div className="mt-5 flex items-center gap-2 text-sm text-slate-500">
          <FiRefreshCw className="animate-spin" /> Consultando integração...
        </div>
      ) : (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900">
              <p className="text-xs uppercase tracking-wide text-slate-500">Produtos analisados</p>
              <p className="mt-1 text-xl font-semibold text-slate-900 dark:text-slate-100">
                {catalog.total_scanned || 0}
              </p>
            </div>
            <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-3 dark:border-emerald-950 dark:bg-emerald-950/30">
              <p className="text-xs uppercase tracking-wide text-emerald-700">
                Prontos para enviar
              </p>
              <p className="mt-1 text-xl font-semibold text-emerald-800 dark:text-emerald-300">
                {catalog.eligible || 0}
              </p>
            </div>
            <div className="rounded-xl border border-amber-100 bg-amber-50 p-3 dark:border-amber-950 dark:bg-amber-950/30">
              <p className="text-xs uppercase tracking-wide text-amber-700">Precisam de ajuste</p>
              <p className="mt-1 text-xl font-semibold text-amber-800 dark:text-amber-300">
                {catalog.rejected || 0}
              </p>
            </div>
          </div>

          {!data?.credentials_configured ? (
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <FiAlertTriangle className="mt-0.5 shrink-0" />
              <p>
                O aplicativo CorePet ainda precisa ser aprovado e receber as credenciais do iFood.
                Você já pode preparar e validar o catálogo sem essas credenciais.
              </p>
            </div>
          ) : null}

          <div className="mt-5 grid gap-4 rounded-xl border border-slate-200 p-4 dark:border-slate-800 sm:grid-cols-2">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300 sm:col-span-2">
              <span>Merchant ID da loja no iFood</span>
              <input
                name="merchant_id"
                value={form.merchant_id || ""}
                onChange={updateField}
                placeholder="00000000-0000-0000-0000-000000000000"
                className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-900 outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
              />
            </label>

            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
              <span>Fonte do catálogo</span>
              <select
                name="catalog_source"
                value={form.catalog_source}
                onChange={updateField}
                className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              >
                <option value="ecommerce">Produtos anunciados no e-commerce</option>
                <option value="erp">Todos os produtos vendáveis do ERP</option>
              </select>
            </label>

            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
              <span>Acréscimo de preço no iFood (%)</span>
              <input
                name="default_markup_percent"
                type="number"
                min="-50"
                max="300"
                step="0.01"
                value={form.default_markup_percent}
                onChange={updateField}
                className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              />
            </label>

            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
              <span>Reserva de segurança do estoque</span>
              <input
                name="stock_safety"
                type="number"
                min="0"
                step="0.001"
                value={form.stock_safety}
                onChange={updateField}
                className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              />
            </label>

            <label className="flex items-center gap-3 self-end rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-300">
              <input
                name="active"
                type="checkbox"
                checked={Boolean(form.active)}
                onChange={updateField}
                className="h-4 w-4 rounded border-slate-300 text-red-600"
              />
              <span>Ativar integração para esta empresa</span>
            </label>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={save}
              disabled={Boolean(action)}
              className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60"
            >
              <FiSave /> {actionText(action, "save", "Salvando...", "Salvar configuração")}
            </button>
            <button
              type="button"
              onClick={loadPreview}
              disabled={Boolean(action)}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:text-slate-300"
            >
              <FiEye /> {actionText(action, "preview", "Analisando...", "Conferir produtos")}
            </button>
            <button
              type="button"
              onClick={simulateSync}
              disabled={Boolean(action)}
              className="inline-flex items-center gap-2 rounded-xl border border-red-200 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-60"
            >
              <FiPackage />
              {actionText(action, "simulate", "Simulando...", "Simular publicação")}
            </button>
            <button
              type="button"
              onClick={testConnection}
              disabled={Boolean(action) || !data?.credentials_configured || !form.merchant_id}
              className="inline-flex items-center gap-2 rounded-xl border border-emerald-200 px-4 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
            >
              <FiWifi /> {actionText(action, "test", "Testando...", "Testar conexão")}
            </button>
          </div>

          {preview ? (
            <div className="mt-5 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
              <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
                <p className="font-medium text-slate-900 dark:text-slate-100">
                  Diagnóstico do catálogo
                </p>
                <p className="text-xs text-slate-500">
                  A lista mostra até 50 bloqueios reais e informa o que precisa ser corrigido no
                  ERP.
                </p>
              </div>
              {preview.issues?.length ? (
                <div className="grid gap-2 border-b border-slate-200 p-3 sm:grid-cols-2 dark:border-slate-800">
                  {preview.issues.map((issue) => (
                    <div
                      key={issue.message}
                      className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900"
                    >
                      <strong>{issue.count}</strong> · {issue.message}
                    </div>
                  ))}
                </div>
              ) : null}
              <div className="max-h-96 divide-y divide-slate-100 overflow-y-auto dark:divide-slate-800">
                {(preview.items || []).map((item) => (
                  <CatalogItem key={item.product_id} item={item} />
                ))}
              </div>
            </div>
          ) : null}

          <IfoodPedidosPanel
            enabled={Boolean(data?.order_operations_enabled)}
            onMessage={(type, text) => setMessage({ type, text })}
          />

          <div className="mt-5 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-950 dark:bg-blue-950/30 dark:text-blue-200">
            Os anúncios não precisam ser cadastrados um a um: o CorePet monta o catálogo a partir da
            base já existente. Produtos sem identificador, preço válido ou situação de venda
            aparecem no diagnóstico para correção antes da publicação.
          </div>
        </>
      )}
    </section>
  );
}
