import ModuleTabs from "../ui/ModuleTabs";

const CAMPANHAS_TABS = [
  { id: "dashboard", label: "\u{1F4CA} Dashboard" },
  { id: "campanhas", label: "\u{1F4CB} Campanhas" },
  { id: "validade", label: "\u23F3 Validade" },
  { id: "retencao", label: "\u{1F504} Retencao" },
  { id: "destaque", label: "\u{1F31F} Destaque Mensal" },
  { id: "sorteios", label: "\u{1F3B2} Sorteios" },
  { id: "ranking", label: "\u{1F3C6} Ranking" },
  { id: "cupons", label: "\u{1F39F}\uFE0F Cupons" },
  { id: "unificacao", label: "\u{1F517} Unificacao" },
  { id: "relatorios", label: "\u{1F4C8} Relatorios" },
  { id: "gestor", label: "\u{1F6E0}\uFE0F Gestor" },
  { id: "config", label: "\u2699\uFE0F Configuracoes" },
  { id: "canais", label: "\u{1F3F7}\uFE0F Descontos por Canal" },
];

export default function CampanhasTabsBar({ aba, onChange }) {
  return (
    <ModuleTabs
      active={aba}
      ariaLabel="Abas de campanhas"
      onChange={onChange}
      tabs={CAMPANHAS_TABS}
    />
  );
}
