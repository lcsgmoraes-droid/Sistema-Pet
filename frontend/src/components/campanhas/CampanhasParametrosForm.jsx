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
    return <CampanhasParametrosLoyaltySection num={num} str={str} set={set} />;
  }

  if (tipo === "cashback") {
    return <CampanhasParametrosCashbackSection num={num} set={set} />;
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
    return (
      <CampanhasParametrosQuickRepurchaseSection
        num={num}
        str={str}
        set={set}
      />
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
