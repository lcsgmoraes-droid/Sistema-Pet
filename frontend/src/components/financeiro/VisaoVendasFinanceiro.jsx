import { useAuth } from "../../contexts/AuthContext";
import { useVisaoComercial } from "../../hooks/useVisaoComercial";
import RecebimentosVendas from "./RecebimentosVendas";

export default function VisaoVendasFinanceiro({ PorVenda }) {
  const { user } = useAuth();
  const { visao, erro, tentarNovamente } = useVisaoComercial();
  const acessoFinanceiro =
    user?.is_admin === true || user?.permissions?.includes("relatorios.financeiro");
  if (!acessoFinanceiro) return <PorVenda />;
  if (erro)
    return (
      <div className="p-6" role="alert">
        {erro}{" "}
        <button type="button" onClick={tentarNovamente} className="ml-3 text-teal-700 underline">
          Tentar novamente
        </button>
      </div>
    );
  if (!visao)
    return (
      <div className="p-6" role="status">
        Carregando relatório da empresa...
      </div>
    );
  return visao === "recebimento" ? <RecebimentosVendas /> : <PorVenda />;
}
