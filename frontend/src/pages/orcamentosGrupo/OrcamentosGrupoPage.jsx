import { useCallback, useEffect, useState } from "react";
import { Building2, FilePlus2, History, Settings2 } from "lucide-react";

import { orcamentosGrupoApi } from "../../api/orcamentosGrupo";
import PageHeader from "../../components/ui/PageHeader";
import EmpresaGrupoConfigPanel from "./EmpresaGrupoConfigPanel";
import OrcamentoGrupoEditor from "./OrcamentoGrupoEditor";
import OrcamentosGrupoHistorico from "./OrcamentosGrupoHistorico";

const tabs = [
  { id: "novo", label: "Novo orçamento", icon: FilePlus2 },
  { id: "historico", label: "Histórico", icon: History },
  { id: "configuracao", label: "Empresas e regras", icon: Settings2 },
];

export default function OrcamentosGrupoPage() {
  const [aba, setAba] = useState("novo");
  const [carregando, setCarregando] = useState(true);
  const [habilitado, setHabilitado] = useState(true);
  const [erro, setErro] = useState("");
  const [configuracao, setConfiguracao] = useState(null);
  const [empresas, setEmpresas] = useState([]);
  const [orcamentos, setOrcamentos] = useState([]);

  const carregar = useCallback(async () => {
    setErro("");
    try {
      const status = await orcamentosGrupoApi.status();
      if (!status.data?.enabled) {
        setHabilitado(false);
        return;
      }
      setHabilitado(true);
      const [configResponse, empresasResponse, orcamentosResponse] = await Promise.all([
        orcamentosGrupoApi.buscarConfiguracao(),
        orcamentosGrupoApi.listarEmpresas(),
        orcamentosGrupoApi.listarOrcamentos(),
      ]);
      setConfiguracao(configResponse.data);
      setEmpresas(empresasResponse.data || []);
      setOrcamentos(orcamentosResponse.data || []);
    } catch (error) {
      setErro(error?.response?.data?.detail || "Não foi possível carregar os orçamentos do grupo.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  if (carregando) {
    return (
      <div className="flex min-h-[55vh] items-center justify-center text-sm text-slate-500">
        Carregando orçamentos...
      </div>
    );
  }

  if (!habilitado) {
    return (
      <div className="mx-auto mt-12 max-w-xl rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <Building2 className="mx-auto text-slate-300" size={40} />
        <h1 className="mt-4 text-xl font-bold text-slate-900 dark:text-slate-100">
          Funcionalidade não habilitada
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          Este piloto ainda não foi liberado para o tenant atual.
        </p>
      </div>
    );
  }

  if (erro || !configuracao) {
    return (
      <div className="mx-auto mt-12 max-w-xl rounded-2xl border border-red-200 bg-red-50 p-6 text-center text-red-800">
        <p>{erro || "Configuração indisponível."}</p>
        <button
          type="button"
          onClick={carregar}
          className="mt-4 rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6">
      <PageHeader
        icon={Building2}
        title="Orçamentos do grupo"
        subtitle="Emita e guarde orçamentos oficiais das empresas vinculadas ao tenant."
      />

      <nav className="flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-2 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const ativa = aba === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setAba(tab.id)}
              className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition ${ativa ? "bg-teal-600 text-white" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-900"}`}
            >
              <Icon size={16} /> {tab.label}
            </button>
          );
        })}
      </nav>

      {aba === "novo" ? (
        <OrcamentoGrupoEditor
          configuracao={configuracao}
          empresas={empresas}
          onEmitido={carregar}
        />
      ) : null}
      {aba === "historico" ? <OrcamentosGrupoHistorico orcamentos={orcamentos} /> : null}
      {aba === "configuracao" ? (
        <EmpresaGrupoConfigPanel
          configuracao={configuracao}
          empresas={empresas}
          onAtualizar={carregar}
        />
      ) : null}
    </div>
  );
}
