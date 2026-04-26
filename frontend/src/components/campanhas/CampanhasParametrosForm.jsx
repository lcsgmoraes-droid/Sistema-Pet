import {
  CampanhasParametrosBirthdaySection,
  CampanhasParametrosCashbackSection,
  CampanhasParametrosGenericoSection,
  CampanhasParametrosInactivitySection,
  CampanhasParametrosLoyaltySection,
  CampanhasParametrosQuickRepurchaseSection,
  CampanhasParametrosRankingSection,
  CampanhasParametrosWelcomeSection,
} from "./CampanhasParametrosSections";
import {
  BENEFIT_CHANNEL_OPTIONS,
  getBenefitChannelsForEdit,
  getConfiguredBenefitChannels,
  PURCHASE_BENEFIT_CAMPAIGN_TYPES,
} from "../../utils/campaignChannelScope";

function CampanhasCanaisBeneficioSection({ paramsEditando, setParamsEditando }) {
  const selectedChannels = getBenefitChannelsForEdit(paramsEditando);
  const explicitChannels = getConfiguredBenefitChannels(paramsEditando);
  const explicitConfig = explicitChannels !== null;

  const updateChannels = (channels) => {
    setParamsEditando((prev) => ({
      ...prev,
      benefit_channels: [...new Set(channels)],
    }));
  };

  const toggleChannel = (channel) => {
    if (selectedChannels.includes(channel)) {
      updateChannels(selectedChannels.filter((item) => item !== channel));
      return;
    }
    updateChannels([...selectedChannels, channel]);
  };

  return (
    <div className="rounded-xl border border-indigo-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide">
            Canais que geram beneficio
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Marque onde esta campanha pode liberar carimbo, cashback ou cupom
            pos-compra. Banho & Tosa e Veterinario ficam bloqueados ate serem
            liberados aqui.
          </p>
        </div>
        {!explicitConfig && (
          <span className="text-[11px] px-2 py-1 rounded-full bg-amber-100 text-amber-700 font-medium">
            Padrao seguro
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {BENEFIT_CHANNEL_OPTIONS.map((option) => {
          const checked = selectedChannels.includes(option.value);
          return (
            <label
              key={option.value}
              className={`flex items-start gap-3 rounded-lg border px-3 py-2 cursor-pointer transition-colors ${
                checked
                  ? "border-indigo-300 bg-indigo-50 text-indigo-900"
                  : "border-gray-200 bg-white text-gray-600 hover:border-indigo-200"
              }`}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggleChannel(option.value)}
                className="mt-0.5 h-4 w-4 accent-indigo-600"
              />
              <span>
                <span className="block text-sm font-semibold">
                  {option.label}
                </span>
                <span className="block text-xs text-gray-500">
                  {option.description}
                </span>
              </span>
            </label>
          );
        })}
      </div>

      <div className="flex gap-2 mt-3">
        <button
          type="button"
          onClick={() => updateChannels(BENEFIT_CHANNEL_OPTIONS.map((item) => item.value))}
          className="text-xs px-3 py-1.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700"
        >
          Liberar todos
        </button>
        <button
          type="button"
          onClick={() => updateChannels([])}
          className="text-xs px-3 py-1.5 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200"
        >
          Bloquear todos
        </button>
      </div>
    </div>
  );
}

function withPurchaseBenefitChannels(tipo, content, paramsEditando, setParamsEditando) {
  if (!PURCHASE_BENEFIT_CAMPAIGN_TYPES.has(tipo)) return content;

  return (
    <div className="space-y-4">
      {content}
      <CampanhasCanaisBeneficioSection
        paramsEditando={paramsEditando}
        setParamsEditando={setParamsEditando}
      />
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
    return withPurchaseBenefitChannels(
      tipo,
      <CampanhasParametrosLoyaltySection num={num} str={str} set={set} />,
      paramsEditando,
      setParamsEditando,
    );
  }

  if (tipo === "cashback") {
    return withPurchaseBenefitChannels(
      tipo,
      <CampanhasParametrosCashbackSection num={num} set={set} />,
      paramsEditando,
      setParamsEditando,
    );
  }

  if (["birthday", "birthday_customer", "birthday_pet"].includes(tipo)) {
    return (
      <CampanhasParametrosBirthdaySection
        tipo={tipo}
        num={num}
        str={str}
        set={set}
      />
    );
  }

  if (tipo === "quick_repurchase") {
    return withPurchaseBenefitChannels(
      tipo,
      <CampanhasParametrosQuickRepurchaseSection
        num={num}
        str={str}
        set={set}
      />,
      paramsEditando,
      setParamsEditando,
    );
  }

  if (tipo === "inactivity") {
    return (
      <CampanhasParametrosInactivitySection num={num} str={str} set={set} />
    );
  }

  if (tipo === "welcome" || tipo === "welcome_app") {
    return <CampanhasParametrosWelcomeSection num={num} str={str} set={set} />;
  }

  if (tipo === "ranking_monthly") {
    return (
      <CampanhasParametrosRankingSection
        paramsEditando={paramsEditando}
        setParamsEditando={setParamsEditando}
      />
    );
  }

  return (
    <CampanhasParametrosGenericoSection
      paramsEditando={paramsEditando}
      setParamsEditando={setParamsEditando}
    />
  );
}
