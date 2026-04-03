import { useState } from "react";

export default function CampanhasRetencaoForm({
  inicial,
  salvando,
  onSalvar,
  onCancelar,
}) {
  const [form, setForm] = useState({ ...inicial });
  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));
  const isNew = !form.id;

  return (
    <div className="bg-orange-50 border border-orange-300 rounded-xl p-4 space-y-3">
      <p className="font-semibold text-orange-800">
        {isNew ? "Nova Regra" : "Editar Regra"}
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="md:col-span-2">
          <label
            htmlFor="ret-name"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Nome da regra
          </label>
          <input
            id="ret-name"
            type="text"
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            placeholder="Ex: Retenção 30 dias"
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          />
        </div>

        <div>
          <label
            htmlFor="ret-days"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Dias sem compra
          </label>
          <input
            id="ret-days"
            type="number"
            min="1"
            value={form.inactivity_days ?? 30}
            onChange={(e) =>
              set("inactivity_days", Number.parseInt(e.target.value, 10) || 30)
            }
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          />
        </div>

        <div>
          <label
            htmlFor="ret-priority"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Prioridade
          </label>
          <input
            id="ret-priority"
            type="number"
            min="1"
            value={form.priority ?? 50}
            onChange={(e) =>
              set("priority", Number.parseInt(e.target.value, 10) || 50)
            }
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          />
        </div>

        <div>
          <label
            htmlFor="ret-coupon-type"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Tipo do cupom
          </label>
          <select
            id="ret-coupon-type"
            value={form.coupon_type ?? "percent"}
            onChange={(e) => set("coupon_type", e.target.value)}
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="percent">Percentual</option>
            <option value="fixed">Valor fixo</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="ret-coupon-value"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Valor do cupom
          </label>
          <input
            id="ret-coupon-value"
            type="number"
            min="0"
            step="0.01"
            value={form.coupon_value ?? 10}
            onChange={(e) =>
              set("coupon_value", Number.parseFloat(e.target.value) || 0)
            }
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          />
        </div>

        <div>
          <label
            htmlFor="ret-coupon-valid"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Validade do cupom (dias)
          </label>
          <input
            id="ret-coupon-valid"
            type="number"
            min="1"
            value={form.coupon_valid_days ?? 7}
            onChange={(e) =>
              set(
                "coupon_valid_days",
                Number.parseInt(e.target.value, 10) || 7,
              )
            }
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          />
        </div>

        <div>
          <label
            htmlFor="ret-coupon-channel"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Canal do cupom
          </label>
          <select
            id="ret-coupon-channel"
            value={form.coupon_channel ?? "all"}
            onChange={(e) => set("coupon_channel", e.target.value)}
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="all">Todos os canais</option>
            <option value="pdv">PDV</option>
            <option value="delivery">Delivery</option>
            <option value="app">App</option>
          </select>
        </div>

        <div className="md:col-span-2">
          <label
            htmlFor="ret-message"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Mensagem
          </label>
          <textarea
            id="ret-message"
            rows={4}
            value={form.notification_message ?? ""}
            onChange={(e) => set("notification_message", e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <button
          onClick={onCancelar}
          className="px-4 py-2 border rounded-lg text-sm hover:bg-white"
        >
          Cancelar
        </button>
        <button
          onClick={() => onSalvar(form)}
          disabled={salvando}
          className="px-4 py-2 bg-orange-600 text-white rounded-lg text-sm font-medium hover:bg-orange-700 disabled:opacity-50"
        >
          {salvando ? "Salvando..." : "Salvar regra"}
        </button>
      </div>
    </div>
  );
}
