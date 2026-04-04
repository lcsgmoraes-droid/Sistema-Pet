import { formatBRL } from "../../utils/formatters";
import { FRASES_ANIVERSARIO } from "./campanhasConstants";

function CampanhaField({
  label,
  id,
  type = "number",
  step = "any",
  min,
  value,
  onChange,
  placeholder,
  colSpan,
}) {
  return (
    <div className={colSpan ? `col-span-${colSpan}` : ""}>
      <label
        htmlFor={id}
        className="block text-xs font-medium text-gray-600 mb-1"
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        step={step}
        min={min}
        value={value}
        placeholder={placeholder}
        onChange={onChange}
        className="w-full border rounded-lg px-3 py-1.5 text-sm"
      />
    </div>
  );
}

function CampanhaSel({ label, id, value, onChange, children }) {
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

export default function CampanhasParametrosForm({
  campanha,
  paramsEditando,
  setParamsEditando,
}) {
  const tipo = campanha.campaign_type;
  const set = (key, val) => setParamsEditando((p) => ({ ...p, [key]: val }));
  const num = (key) => paramsEditando[key] ?? "";
  const str = (key) => paramsEditando[key] ?? "";

  if (tipo === "loyalty_stamp") {
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
        <CampanhaSel
          label="Tipo de recompensa"
          id="p-reward-type"
          value={str("reward_type") || "coupon"}
          onChange={(e) => set("reward_type", e.target.value)}
        >
          <option value="coupon">Cupom de desconto</option>
          <option value="credit">Credito cashback</option>
        </CampanhaSel>
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
          <CampanhaSel
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
          </CampanhaSel>
        </div>
      </div>
    );
  }

  if (tipo === "cashback") {
    const levels = [
      { key: "bronze_percent", label: "Bronze" },
      { key: "silver_percent", label: "Prata" },
      { key: "gold_percent", label: "Ouro" },
      { key: "diamond_percent", label: "Diamante" },
      { key: "platinum_percent", label: "Platina" },
    ];
    const canais = [
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
            {levels.map((lv) => (
              <CampanhaField
                key={lv.key}
                label={`${lv.label} (%)`}
                id={`p-${lv.key}`}
                value={num(lv.key)}
                onChange={(e) =>
                  set(lv.key, Number.parseFloat(e.target.value) || 0)
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
            {canais.map((canal) => (
              <CampanhaField
                key={canal.key}
                label={canal.label}
                id={`p-${canal.key}`}
                value={num(canal.key)}
                onChange={(e) =>
                  set(canal.key, Number.parseFloat(e.target.value) || 0)
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

  if (["birthday", "birthday_customer", "birthday_pet"].includes(tipo)) {
    const frases =
      FRASES_ANIVERSARIO[tipo] || FRASES_ANIVERSARIO.birthday_customer;
    const tipoPresente = str("tipo_presente") || "cupom";
    const fraseSugerida = frases[tipoPresente] || "";
    const ehPet = tipo === "birthday_pet";

    return (
      <div className="space-y-4">
        <div>
          <p className="text-xs font-semibold text-gray-700 mb-2">
            O que o cliente recebe no aniversario?
          </p>
          <div className="flex gap-4">
            {[
              { value: "cupom", label: "Cupom de desconto" },
              { value: "brinde", label: "Brinde na loja" },
            ].map((opt) => (
              <label
                key={opt.value}
                className={`flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border-2 transition-colors ${
                  tipoPresente === opt.value
                    ? "border-blue-500 bg-blue-50 text-blue-800 font-semibold"
                    : "border-gray-200 bg-white text-gray-600 hover:border-blue-300"
                }`}
              >
                <input
                  type="radio"
                  name={`tipo_presente_${tipo}`}
                  value={opt.value}
                  checked={tipoPresente === opt.value}
                  onChange={() => {
                    set("tipo_presente", opt.value);
                    set("notification_message", frases[opt.value] || "");
                  }}
                  className="accent-blue-600 w-4 h-4"
                />
                <span className="text-sm">{opt.label}</span>
              </label>
            ))}
          </div>
        </div>

        {tipoPresente === "cupom" && (
          <div className="grid grid-cols-2 gap-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
            <CampanhaSel
              label="Tipo de desconto"
              id="p-bday-type"
              value={str("coupon_type") || "fixed"}
              onChange={(e) => set("coupon_type", e.target.value)}
            >
              <option value="fixed">Valor fixo (R$)</option>
              <option value="percent">Percentual (%)</option>
            </CampanhaSel>
            <CampanhaField
              label={
                str("coupon_type") === "percent"
                  ? "Percentual (%)"
                  : "Valor (R$)"
              }
              id="p-bday-val"
              value={num("coupon_value")}
              onChange={(e) =>
                set("coupon_value", Number.parseFloat(e.target.value) || 0)
              }
            />
            <CampanhaField
              label="Validade (dias)"
              id="p-bday-days"
              step="1"
              min="1"
              value={num("coupon_valid_days") || 3}
              onChange={(e) =>
                set(
                  "coupon_valid_days",
                  Number.parseInt(e.target.value, 10) || 3,
                )
              }
            />
            <CampanhaSel
              label="Canal"
              id="p-bday-canal"
              value={str("coupon_channel") || "all"}
              onChange={(e) => set("coupon_channel", e.target.value)}
            >
              <option value="all">Todos os canais</option>
              <option value="pdv">PDV</option>
              <option value="app">App</option>
              <option value="ecommerce">E-commerce</option>
            </CampanhaSel>
          </div>
        )}

        <div>
          <div className="flex items-center justify-between mb-1">
            <label
              htmlFor="p-bday-msg"
              className="block text-xs font-semibold text-gray-700"
            >
              Mensagem enviada ao cliente
            </label>
            <button
              type="button"
              onClick={() => set("notification_message", fraseSugerida)}
              className="text-xs text-blue-600 hover:text-blue-800 underline"
            >
              Usar frase sugerida
            </button>
          </div>
          <textarea
            id="p-bday-msg"
            rows={4}
            value={str("notification_message")}
            onChange={(e) => set("notification_message", e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
          <p className="text-xs text-gray-400 mt-1">
            Variaveis disponiveis:{" "}
            <code className="bg-gray-100 px-1 rounded">{"{nome}"}</code>
            {ehPet && (
              <>
                {" "}
                <code className="bg-gray-100 px-1 rounded">{"{nome_pet}"}</code>
              </>
            )}
            {tipoPresente === "cupom" && (
              <>
                {" "}
                <code className="bg-gray-100 px-1 rounded">{"{code}"}</code>{" "}
                <code className="bg-gray-100 px-1 rounded">
                  {"{desconto}"}
                </code>
              </>
            )}
          </p>
        </div>
      </div>
    );
  }

  if (tipo === "quick_repurchase") {
    return (
      <div className="grid grid-cols-2 gap-3">
        <CampanhaField
          label="Compra minima (R$)"
          id="p-qr-min"
          value={num("min_purchase_value")}
          onChange={(e) =>
            set("min_purchase_value", Number.parseFloat(e.target.value) || 0)
          }
        />
        <CampanhaSel
          label="Tipo de desconto"
          id="p-qr-type"
          value={str("coupon_type") || "percent"}
          onChange={(e) => set("coupon_type", e.target.value)}
        >
          <option value="percent">Percentual (%)</option>
          <option value="fixed">Valor fixo (R$)</option>
        </CampanhaSel>
        <CampanhaField
          label={
            str("coupon_type") === "fixed" ? "Valor (R$)" : "Percentual (%)"
          }
          id="p-qr-val"
          value={num("coupon_value")}
          onChange={(e) =>
            set("coupon_value", Number.parseFloat(e.target.value) || 0)
          }
        />
        <CampanhaField
          label="Validade do cupom (dias)"
          id="p-qr-days"
          step="1"
          min="1"
          value={num("coupon_valid_days") || 15}
          onChange={(e) =>
            set(
              "coupon_valid_days",
              Number.parseInt(e.target.value, 10) || 15,
            )
          }
        />
        <CampanhaSel
          label="Canal"
          id="p-qr-chan"
          value={str("coupon_channel") || "pdv"}
          onChange={(e) => set("coupon_channel", e.target.value)}
        >
          <option value="pdv">PDV</option>
          <option value="app">App</option>
          <option value="ecommerce">E-commerce</option>
          <option value="all">Todos</option>
        </CampanhaSel>
        <div className="col-span-2">
          <label
            htmlFor="p-qr-msg"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Mensagem personalizada
          </label>
          <input
            id="p-qr-msg"
            type="text"
            value={str("notification_message")}
            onChange={(e) => set("notification_message", e.target.value)}
            placeholder="Ex: Obrigado pela compra! Use o cupom {code} na proxima visita."
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          />
        </div>
      </div>
    );
  }

  if (tipo === "inactivity") {
    return (
      <div className="grid grid-cols-2 gap-3">
        <CampanhaField
          label="Dias de inatividade"
          id="p-inact-days"
          step="1"
          min="1"
          value={num("inactivity_days") || 30}
          onChange={(e) =>
            set("inactivity_days", Number.parseInt(e.target.value, 10) || 30)
          }
        />
        <CampanhaSel
          label="Tipo de desconto"
          id="p-inact-type"
          value={str("coupon_type") || "percent"}
          onChange={(e) => set("coupon_type", e.target.value)}
        >
          <option value="fixed">Valor fixo (R$)</option>
          <option value="percent">Percentual (%)</option>
        </CampanhaSel>
        <CampanhaField
          label={
            str("coupon_type") === "fixed" ? "Valor (R$)" : "Percentual (%)"
          }
          id="p-inact-val"
          value={num("coupon_value")}
          onChange={(e) =>
            set("coupon_value", Number.parseFloat(e.target.value) || 0)
          }
        />
        <CampanhaField
          label="Validade do cupom (dias)"
          id="p-inact-valid"
          step="1"
          min="1"
          value={num("coupon_valid_days") || 7}
          onChange={(e) =>
            set("coupon_valid_days", Number.parseInt(e.target.value, 10) || 7)
          }
        />
        <div className="col-span-2">
          <label
            htmlFor="p-inact-msg"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Mensagem
          </label>
          <input
            id="p-inact-msg"
            type="text"
            value={str("notification_message")}
            onChange={(e) => set("notification_message", e.target.value)}
            placeholder="Ex: Sentimos sua falta! Use este cupom."
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          />
        </div>
      </div>
    );
  }

  if (tipo === "welcome" || tipo === "welcome_app") {
    return (
      <div className="grid grid-cols-2 gap-3">
        <CampanhaSel
          label="Tipo de desconto"
          id="p-wel-type"
          value={str("coupon_type") || "fixed"}
          onChange={(e) => set("coupon_type", e.target.value)}
        >
          <option value="fixed">Valor fixo (R$)</option>
          <option value="percent">Percentual (%)</option>
        </CampanhaSel>
        <CampanhaField
          label={
            str("coupon_type") === "percent" ? "Percentual (%)" : "Valor (R$)"
          }
          id="p-wel-val"
          value={num("coupon_value")}
          onChange={(e) =>
            set("coupon_value", Number.parseFloat(e.target.value) || 0)
          }
        />
        <CampanhaField
          label="Validade (dias)"
          id="p-wel-days"
          step="1"
          min="1"
          value={num("coupon_valid_days") || 30}
          onChange={(e) =>
            set(
              "coupon_valid_days",
              Number.parseInt(e.target.value, 10) || 30,
            )
          }
        />
        <CampanhaSel
          label="Canal"
          id="p-wel-chan"
          value={str("coupon_channel") || "app"}
          onChange={(e) => set("coupon_channel", e.target.value)}
        >
          <option value="app">App</option>
          <option value="pdv">PDV</option>
          <option value="ecommerce">E-commerce</option>
        </CampanhaSel>
      </div>
    );
  }

  if (tipo === "ranking_monthly") {
    const levels = ["bronze", "silver", "gold", "diamond", "platinum"];
    const lvLabels = {
      bronze: "Bronze",
      silver: "Prata",
      gold: "Ouro",
      diamond: "Diamante",
      platinum: "Platina",
    };
    const getLv = (lv) => paramsEditando[lv] || {};
    const setLv = (lv, key, val) =>
      setParamsEditando((p) => ({ ...p, [lv]: { ...p[lv], [key]: val } }));

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
              {levels.map((lv) => (
                <tr key={lv}>
                  <td className="px-3 py-2 font-medium text-sm">
                    {lvLabels[lv]}
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={getLv(lv).min_spent ?? ""}
                      onChange={(e) =>
                        setLv(
                          lv,
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
                      value={getLv(lv).min_purchases ?? ""}
                      onChange={(e) =>
                        setLv(
                          lv,
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
                      value={getLv(lv).min_active_months ?? ""}
                      onChange={(e) =>
                        setLv(
                          lv,
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

  return (
    <div className="grid grid-cols-2 gap-3">
      {Object.entries(paramsEditando).map(([chave, valor]) => (
        <div key={chave}>
          <label
            htmlFor={`param-${chave}`}
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            {chave}
          </label>
          <input
            id={`param-${chave}`}
            type="text"
            value={
              typeof valor === "object"
                ? JSON.stringify(valor)
                : String(valor ?? "")
            }
            onChange={(e) =>
              setParamsEditando((prev) => ({
                ...prev,
                [chave]: e.target.value,
              }))
            }
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          />
        </div>
      ))}
    </div>
  );
}
