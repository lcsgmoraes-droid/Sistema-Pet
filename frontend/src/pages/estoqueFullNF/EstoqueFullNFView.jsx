import { PackageMinus } from "lucide-react";
import ModuleTabs from "../../components/ui/ModuleTabs";
import PageHeader from "../../components/ui/PageHeader";
import EstoqueFullNFHistoricoPanel from "./EstoqueFullNFHistoricoPanel";
import EstoqueFullNFLancamentoPanel from "./EstoqueFullNFLancamentoPanel";
import EstoqueFullNFModals from "./EstoqueFullNFModals";

export default function EstoqueFullNFView({ controller }) {
  const { abaAtiva, setAbaAtiva, historico } = controller;

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-6 space-y-6">
      <PageHeader
        icon={PackageMinus}
        title="Movimentacao FULL por documento"
        subtitle="Baixe o estoque pelo PDF do inbound, DANFE ou XML e, opcionalmente, lance a tarifa de envio."
      />

      <ModuleTabs
        active={abaAtiva}
        onChange={setAbaAtiva}
        tabs={[
          { id: "lancamento", label: "Novo lancamento" },
          {
            id: "historico",
            label: `Historico de baixas ${historico.length ? `(${historico.length})` : ""}`,
          },
        ]}
      />

      {abaAtiva === "lancamento" && <EstoqueFullNFLancamentoPanel controller={controller} />}
      {abaAtiva === "historico" && <EstoqueFullNFHistoricoPanel controller={controller} />}

      <EstoqueFullNFModals controller={controller} />
    </div>
  );
}
