import { FRASES_ANIVERSARIO } from "./campanhasConstants";
import { CampanhaField, CampanhaSel } from "./CampanhasParametrosFields";

export function CampanhasParametrosBirthdaySection({ tipo, num, str, set }) {
  const frases =
    FRASES_ANIVERSARIO[tipo] || FRASES_ANIVERSARIO.birthday_customer;
  const tipoPresente = str("tipo_presente") || "cupom";
  const fraseSugerida = frases[tipoPresente] || "";
  const isPet = tipo === "birthday_pet";

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
          ].map((option) => (
            <label
              key={option.value}
              className={`flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border-2 transition-colors ${
                tipoPresente === option.value
                  ? "border-blue-500 bg-blue-50 text-blue-800 font-semibold"
                  : "border-gray-200 bg-white text-gray-600 hover:border-blue-300"
              }`}
            >
              <input
                type="radio"
                name={`tipo_presente_${tipo}`}
                value={option.value}
                checked={tipoPresente === option.value}
                onChange={() => {
                  set("tipo_presente", option.value);
                  set("notification_message", frases[option.value] || "");
                }}
                className="accent-blue-600 w-4 h-4"
              />
              <span className="text-sm">{option.label}</span>
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
              str("coupon_type") === "percent" ? "Percentual (%)" : "Valor (R$)"
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
              set("coupon_valid_days", Number.parseInt(e.target.value, 10) || 3)
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
          {isPet && (
            <>
              {" "}
              <code className="bg-gray-100 px-1 rounded">{"{nome_pet}"}</code>
            </>
          )}
          {tipoPresente === "cupom" && (
            <>
              {" "}
              <code className="bg-gray-100 px-1 rounded">{"{code}"}</code>{" "}
              <code className="bg-gray-100 px-1 rounded">{"{desconto}"}</code>
            </>
          )}
        </p>
      </div>
    </div>
  );
}

export function CampanhasParametrosQuickRepurchaseSection({
  num,
  str,
  set,
}) {
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
          set("coupon_valid_days", Number.parseInt(e.target.value, 10) || 15)
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

export function CampanhasParametrosInactivitySection({ num, str, set }) {
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

export function CampanhasParametrosWelcomeSection({ num, str, set }) {
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
          set("coupon_valid_days", Number.parseInt(e.target.value, 10) || 30)
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
