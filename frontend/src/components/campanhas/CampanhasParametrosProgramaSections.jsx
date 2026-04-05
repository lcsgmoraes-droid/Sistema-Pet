import { CampanhaField } from "./CampanhasParametrosFields";

function CampanhaSelect({ id, label, value, onChange, children }) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-xs font-medium text-gray-600 mb-1"
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={onChange}
        className="w-full border rounded-lg px-3 py-1.5 text-sm"
      >
        {children}
      </select>
    </div>
  );
}

export function CampanhasParametrosLoyaltySection({ num, str, set }) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <CampanhaField
        label="Compra minima (R$)"
        id="p-min"
        value={num("min_purchase_value")}
        onChange={(e) =>
          set("min_purchase_value", Number.parseFloat(e.target.value) || 0)
        }
      />
      <CampanhaField
        label="Carimbos para completar"
        id="p-stamps"
        step="1"
        min="1"
        value={num("stamps_to_complete")}
        onChange={(e) =>
          set("stamps_to_complete", Number.parseInt(e.target.value, 10) || 0)
        }
      />
      <CampanhaSelect
        label="Tipo de recompensa"
        id="p-reward-type"
        value={str("reward_type") || "coupon"}
        onChange={(e) => set("reward_type", e.target.value)}
      >
        <option value="coupon">Cupom de desconto</option>
        <option value="credit">Credito cashback</option>
      </CampanhaSelect>
      <CampanhaField
        label="Valor da recompensa (R$)"
        id="p-reward-val"
        value={num("reward_value")}
        onChange={(e) =>
          set("reward_value", Number.parseFloat(e.target.value) || 0)
        }
      />
      <CampanhaField
        label="Carimbo intermediario (0 = sem)"
        id="p-inter"
        step="1"
        min="0"
        value={num("intermediate_stamp") || 0}
        onChange={(e) =>
          set("intermediate_stamp", Number.parseInt(e.target.value, 10) || 0)
        }
      />
      <CampanhaField
        label="Recompensa intermediaria (R$)"
        id="p-inter-val"
        value={num("intermediate_reward_value") || 0}
        onChange={(e) =>
          set(
            "intermediate_reward_value",
            Number.parseFloat(e.target.value) || 0,
          )
        }
      />
      <CampanhaField
        label="Validade do cupom (dias)"
        id="p-validity"
        step="1"
        min="1"
        value={num("coupon_days_valid") || 30}
        onChange={(e) =>
          set("coupon_days_valid", Number.parseInt(e.target.value, 10) || 30)
        }
      />
      <div className="col-span-2">
        <CampanhaSelect
          label="Quem participa?"
          id="p-rank-filter"
          value={str("rank_filter") || "all"}
          onChange={(e) => set("rank_filter", e.target.value)}
        >
          <option value="all">Todos os clientes</option>
          <option value="sem_rank">Sem classificacao</option>
          <option value="bronze">Bronze</option>
          <option value="silver">Prata</option>
          <option value="gold">Ouro</option>
          <option value="diamond">Diamante</option>
          <option value="platinum">Platina</option>
        </CampanhaSelect>
      </div>
    </div>
  );
}

export function CampanhasParametrosCashbackSection({ num, set }) {
  const levels = [
    { key: "bronze_percent", label: "Bronze" },
    { key: "silver_percent", label: "Prata" },
    { key: "gold_percent", label: "Ouro" },
    { key: "diamond_percent", label: "Diamante" },
    { key: "platinum_percent", label: "Platina" },
  ];
  const channels = [
    { key: "pdv_bonus_percent", label: "PDV (bonus %)" },
    { key: "app_bonus_percent", label: "App (bonus %)" },
    { key: "ecommerce_bonus_percent", label: "E-commerce (bonus %)" },
  ];

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs text-gray-500 mb-2">
          % base por nivel de ranking (credito automatico em toda compra).
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {levels.map((level) => (
            <CampanhaField
              key={level.key}
              label={`${level.label} (%)`}
              id={`p-${level.key}`}
              value={num(level.key)}
              onChange={(e) =>
                set(level.key, Number.parseFloat(e.target.value) || 0)
              }
            />
          ))}
        </div>
      </div>
      <div>
        <p className="text-xs text-gray-500 mb-2">
          Bonus adicional por canal (somado ao % do nivel). Ex.: App +1%
          incentiva o uso do aplicativo.
        </p>
        <div className="grid grid-cols-3 gap-3">
          {channels.map((channel) => (
            <CampanhaField
              key={channel.key}
              label={channel.label}
              id={`p-${channel.key}`}
              value={num(channel.key)}
              onChange={(e) =>
                set(channel.key, Number.parseFloat(e.target.value) || 0)
              }
            />
          ))}
        </div>
      </div>
      <div className="border-t pt-4">
        <p className="text-xs font-semibold text-gray-700 mb-2">
          Validade e alertas
        </p>
        <div className="grid grid-cols-2 gap-3">
          <CampanhaField
            label="Validade do cashback (dias, 0 = sem prazo)"
            id="p-cashback_valid_days"
            value={num("cashback_valid_days")}
            onChange={(e) =>
              set(
                "cashback_valid_days",
                Number.parseInt(e.target.value, 10) || 0,
              )
            }
          />
          <CampanhaField
            label="Alertar cliente X dias antes de expirar"
            id="p-cashback_alerta_dias"
            value={num("cashback_alerta_dias") || 7}
            onChange={(e) =>
              set(
                "cashback_alerta_dias",
                Number.parseInt(e.target.value, 10) || 7,
              )
            }
          />
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Se validade = 0, o cashback nunca expira. O alerta envia e-mail ou
          push ao cliente quando faltar X dias para o vencimento.
        </p>
      </div>
    </div>
  );
}

export function CampanhasParametrosRankingSection({
  paramsEditando,
  setParamsEditando,
}) {
  const levels = ["bronze", "silver", "gold", "diamond", "platinum"];
  const levelLabels = {
    bronze: "Bronze",
    silver: "Prata",
    gold: "Ouro",
    diamond: "Diamante",
    platinum: "Platina",
  };
  const getLevel = (level) => paramsEditando[level] || {};
  const setLevel = (level, key, value) =>
    setParamsEditando((prev) => ({
      ...prev,
      [level]: { ...prev[level], [key]: value },
    }));

  return (
    <div>
      <p className="text-xs text-gray-500 mb-2">
        Criterios minimos para cada nivel. Recalculado mensalmente.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                Nivel
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                Gasto minimo (R$)
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                Compras minimas
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                Meses ativos minimos
              </th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {levels.map((level) => (
              <tr key={level}>
                <td className="px-3 py-2 font-medium text-sm">
                  {levelLabels[level]}
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="any"
                    min="0"
                    value={getLevel(level).min_spent ?? ""}
                    onChange={(e) =>
                      setLevel(
                        level,
                        "min_spent",
                        Number.parseFloat(e.target.value) || 0,
                      )
                    }
                    className="w-24 border rounded px-2 py-1 text-xs"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="1"
                    min="0"
                    value={getLevel(level).min_purchases ?? ""}
                    onChange={(e) =>
                      setLevel(
                        level,
                        "min_purchases",
                        Number.parseInt(e.target.value, 10) || 0,
                      )
                    }
                    className="w-20 border rounded px-2 py-1 text-xs"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="1"
                    min="0"
                    value={getLevel(level).min_active_months ?? ""}
                    onChange={(e) =>
                      setLevel(
                        level,
                        "min_active_months",
                        Number.parseInt(e.target.value, 10) || 0,
                      )
                    }
                    className="w-20 border rounded px-2 py-1 text-xs"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function CampanhasParametrosGenericoSection({
  paramsEditando,
  setParamsEditando,
}) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {Object.entries(paramsEditando).map(([key, value]) => (
        <div key={key}>
          <label
            htmlFor={`param-${key}`}
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            {key}
          </label>
          <input
            id={`param-${key}`}
            type="text"
            value={
              typeof value === "object"
                ? JSON.stringify(value)
                : String(value ?? "")
            }
            onChange={(e) =>
              setParamsEditando((prev) => ({
                ...prev,
                [key]: e.target.value,
              }))
            }
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          />
        </div>
      ))}
    </div>
  );
}
