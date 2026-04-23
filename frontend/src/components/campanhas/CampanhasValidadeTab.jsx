import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import {
  getCampanhaValidadeConfig,
  salvarCampanhaValidadeConfig,
} from "../../api/campanhasValidade";
import ProdutosValidadeProxima from "../../pages/ProdutosValidadeProxima";

const CONFIG_INICIAL = {
  ativo: false,
  aplicar_app: true,
  aplicar_ecommerce: true,
  desconto_60_dias: 10,
  desconto_30_dias: 20,
  desconto_7_dias: 35,
  rotulo_publico: "Validade proxima",
  mensagem_publica: "Oferta por lote com quantidade limitada.",
  total_exclusoes: 0,
};

function CardResumo({ titulo, valor, descricao, className = "" }) {
  return (
    <div className={`rounded-2xl border border-gray-200 bg-white p-5 shadow-sm ${className}`}>
      <p className="text-sm font-medium text-gray-500">{titulo}</p>
      <p className="mt-2 text-2xl font-bold text-gray-900">{valor}</p>
      <p className="mt-2 text-xs text-gray-500">{descricao}</p>
    </div>
  );
}

export default function CampanhasValidadeTab() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [reloadSignal, setReloadSignal] = useState(0);
  const [form, setForm] = useState(CONFIG_INICIAL);

  useEffect(() => {
    void carregarConfig();
  }, []);

  const carregarConfig = async () => {
    try {
      setLoading(true);
      const response = await getCampanhaValidadeConfig();
      setForm({
        ...CONFIG_INICIAL,
        ...(response.data || {}),
      });
    } catch (error) {
      console.error("Erro ao carregar config de validade:", error);
      toast.error("Nao foi possivel carregar a campanha de validade.");
    } finally {
      setLoading(false);
    }
  };

  const atualizarCampo = (campo, valor) => {
    setForm((prev) => ({
      ...prev,
      [campo]: valor,
    }));
  };

  const salvarConfig = async () => {
    try {
      setSalvando(true);
      const payload = {
        ...form,
        desconto_60_dias: Number(form.desconto_60_dias) || 0,
        desconto_30_dias: Number(form.desconto_30_dias) || 0,
        desconto_7_dias: Number(form.desconto_7_dias) || 0,
      };
      const response = await salvarCampanhaValidadeConfig(payload);
      setForm((prev) => ({
        ...prev,
        ...(response.data || {}),
      }));
      setReloadSignal((prev) => prev + 1);
      toast.success("Campanha automatica por validade atualizada.");
    } catch (error) {
      console.error("Erro ao salvar campanha de validade:", error);
      toast.error(
        error?.response?.data?.detail ||
          "Nao foi possivel salvar a campanha de validade.",
      );
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-emerald-100 bg-gradient-to-r from-emerald-50 via-white to-amber-50 p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <h2 className="text-xl font-semibold text-gray-900">
              Campanha automatica por validade
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              Todo lote dentro da janela entra sozinho na oferta de app/site,
              com limite pela quantidade do proprio lote. Se pausar a campanha,
              remover a validade ou zerar o lote, o item sai automaticamente.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => navigate("/estoque/alertas?aba=validade")}
              className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
            >
              Abrir alertas de validade
            </button>
            <button
              type="button"
              onClick={() => {
                void carregarConfig();
                setReloadSignal((prev) => prev + 1);
              }}
              className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              Atualizar
            </button>
            <button
              type="button"
              onClick={salvarConfig}
              disabled={loading || salvando}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {salvando ? "Salvando..." : "Salvar campanha"}
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <CardResumo
          titulo="Status"
          valor={form.ativo ? "Ativa" : "Pausada"}
          descricao="Quando ativa, lotes elegiveis entram sozinhos nos canais digitais."
          className={form.ativo ? "border-emerald-200 bg-emerald-50" : ""}
        />
        <CardResumo
          titulo="Canais"
          valor={[
            form.aplicar_app ? "App" : null,
            form.aplicar_ecommerce ? "Site" : null,
          ]
            .filter(Boolean)
            .join(" + ") || "Nenhum"}
          descricao="A campanha so publica desconto nos canais marcados."
        />
        <CardResumo
          titulo="Itens fora da campanha"
          valor={form.total_exclusoes || 0}
          descricao="Produtos/lotes removidos manualmente sem desligar a regra geral."
        />
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
          <div className="space-y-4">
            <div className="flex flex-wrap gap-4">
              <label className="inline-flex items-center gap-2 text-sm font-medium text-gray-700">
                <input
                  type="checkbox"
                  checked={Boolean(form.ativo)}
                  onChange={(event) => atualizarCampo("ativo", event.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                />
                Campanha ativa
              </label>
              <label className="inline-flex items-center gap-2 text-sm font-medium text-gray-700">
                <input
                  type="checkbox"
                  checked={Boolean(form.aplicar_app)}
                  onChange={(event) =>
                    atualizarCampo("aplicar_app", event.target.checked)
                  }
                  className="h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                />
                Aplicar no app
              </label>
              <label className="inline-flex items-center gap-2 text-sm font-medium text-gray-700">
                <input
                  type="checkbox"
                  checked={Boolean(form.aplicar_ecommerce)}
                  onChange={(event) =>
                    atualizarCampo("aplicar_ecommerce", event.target.checked)
                  }
                  className="h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                />
                Aplicar no site
              </label>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {[
                ["desconto_60_dias", "60 dias"],
                ["desconto_30_dias", "30 dias"],
                ["desconto_7_dias", "7 dias"],
              ].map(([campo, label]) => (
                <label key={campo} className="block">
                  <span className="mb-1 block text-sm font-medium text-gray-700">
                    Desconto {label}
                  </span>
                  <div className="flex items-center rounded-xl border border-gray-300 px-3 py-2.5 focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-100">
                    <input
                      type="number"
                      min="0"
                      max="95"
                      step="0.1"
                      value={form[campo]}
                      onChange={(event) =>
                        atualizarCampo(campo, event.target.value)
                      }
                      className="w-full border-0 p-0 text-sm focus:outline-none focus:ring-0"
                    />
                    <span className="text-sm text-gray-500">%</span>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-gray-700">
                Rotulo publico
              </span>
              <input
                type="text"
                value={form.rotulo_publico || ""}
                onChange={(event) =>
                  atualizarCampo("rotulo_publico", event.target.value)
                }
                className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-100"
                placeholder="Ex.: Validade proxima"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-sm font-medium text-gray-700">
                Mensagem publica
              </span>
              <textarea
                rows={4}
                value={form.mensagem_publica || ""}
                onChange={(event) =>
                  atualizarCampo("mensagem_publica", event.target.value)
                }
                className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-100"
                placeholder="Mensagem curta para app/site."
              />
            </label>
          </div>
        </div>
      </div>

      <ProdutosValidadeProxima embedded reloadSignal={reloadSignal} />
    </div>
  );
}
