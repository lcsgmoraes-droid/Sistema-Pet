import { useEffect, useRef, useState } from "react";
import { Coins, PackageCheck, Plus, RefreshCw, WalletCards } from "lucide-react";
import toast from "react-hot-toast";
import BotaoInteracao from "../../../components/v2/BotaoInteracao/BotaoInteracao";
import LoadingState from "../../../components/ui/LoadingState";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, formatNumber, getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaCreditoForm from "./BanhoTosaCreditoForm";
import BanhoTosaCreditosList from "./BanhoTosaCreditosList";
import BanhoTosaPacoteForm from "./BanhoTosaPacoteForm";
import BanhoTosaPacotesList from "./BanhoTosaPacotesList";
import { confirmarCorePet } from "../../../services/corepetDialog";

export default function BanhoTosaPacotesView({ servicos = [], onChanged }) {
  const [pacotes, setPacotes] = useState([]);
  const [creditos, setCreditos] = useState([]);
  const [editingPacote, setEditingPacote] = useState(null);
  const [showPacoteForm, setShowPacoteForm] = useState(false);
  const [showCreditoForm, setShowCreditoForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [erroCarga, setErroCarga] = useState("");
  const ultimaCarga = useRef(0);

  async function carregar() {
    const carga = ++ultimaCarga.current;
    setLoading(true);
    setErroCarga("");
    try {
      const [pacotesRes, creditosRes] = await Promise.all([
        banhoTosaApi.listarPacotes(),
        banhoTosaApi.listarCreditosPacote({ limit: 300 }),
      ]);
      if (carga !== ultimaCarga.current) return;
      setPacotes(Array.isArray(pacotesRes.data) ? pacotesRes.data : []);
      setCreditos(Array.isArray(creditosRes.data) ? creditosRes.data : []);
    } catch (error) {
      if (carga !== ultimaCarga.current) return;
      setErroCarga(
        getApiErrorMessage(
          error,
          "Não foi possível carregar os pacotes. Atualize para tentar novamente.",
        ),
      );
    } finally {
      if (carga === ultimaCarga.current) setLoading(false);
    }
  }

  async function recarregarTudo() {
    await carregar();
    await onChanged?.(true);
  }

  function editarPacote(pacote) {
    setEditingPacote(pacote);
    setShowPacoteForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function excluirPacote(pacote) {
    const confirmou = await confirmarCorePet(
      `Excluir o pacote "${pacote.nome}"? Se ele ja tiver creditos emitidos, o sistema vai apenas desativar.`,
    );
    if (!confirmou) return;

    try {
      const response = await banhoTosaApi.removerPacote(pacote.id);
      toast.success(response.data?.message || "Pacote excluido.");
      if (editingPacote?.id === pacote.id) {
        setEditingPacote(null);
      }
      await recarregarTudo();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel excluir pacote."));
    }
  }

  useEffect(() => {
    carregar();
    return () => {
      ultimaCarga.current += 1;
    };
  }, []);

  const resumo = montarResumo(pacotes, creditos);

  return (
    <div className="space-y-4">
      <Panel
        actions={
          <div className="flex flex-wrap gap-2">
            <BotaoInteracao
              icon={Plus}
              onClick={() => {
                setEditingPacote(null);
                setShowPacoteForm((value) => !value);
              }}
            >
              Novo pacote
            </BotaoInteracao>
            <BotaoInteracao
              icon={WalletCards}
              onClick={() => setShowCreditoForm((value) => !value)}
            >
              Vincular pacote ao pet
            </BotaoInteracao>
            <BotaoInteracao icon={RefreshCw} loading={loading} onClick={carregar}>
              Atualizar
            </BotaoInteracao>
          </div>
        }
        subtitle="Cadastre serviços por pacote, vincule ao pet e acompanhe saldo, validade e pagamento."
        title="Pacotes e créditos"
      />

      {erroCarga && (
        <p
          role="alert"
          className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
        >
          {erroCarga}
        </p>
      )}
      {loading ? (
        <LoadingState label="Carregando pacotes e saldos..." />
      ) : (
        <>
          <MetricGrid>
            <MetricCard
              icon={<PackageCheck size={18} />}
              intent="blue"
              label="Pacotes"
              value={pacotes.length}
            />
            <MetricCard intent="emerald" label="Ativos" value={resumo.ativos} />
            <MetricCard
              icon={<Coins size={18} />}
              intent="cyan"
              label="Créditos disponíveis"
              value={formatNumber(resumo.creditosDisponiveis, 0)}
            />
            <MetricCard
              intent="violet"
              label="Valor de tabela"
              subtitle="Soma dos preços dos pacotes"
              value={formatCurrency(resumo.valorPacotes)}
            />
          </MetricGrid>

          {(showPacoteForm || editingPacote || showCreditoForm) && (
            <div className="grid gap-4 xl:grid-cols-2">
              {(showPacoteForm || editingPacote) && (
                <BanhoTosaPacoteForm
                  key={editingPacote?.id || "novo"}
                  servicos={servicos}
                  editingPacote={editingPacote}
                  onCancelEdit={() => {
                    setEditingPacote(null);
                    setShowPacoteForm(false);
                  }}
                  onChanged={async () => {
                    setEditingPacote(null);
                    setShowPacoteForm(false);
                    await recarregarTudo();
                  }}
                />
              )}
              {showCreditoForm && (
                <BanhoTosaCreditoForm
                  pacotes={pacotes}
                  onCancel={() => setShowCreditoForm(false)}
                  onChanged={async () => {
                    setShowCreditoForm(false);
                    await recarregarTudo();
                  }}
                />
              )}
            </div>
          )}

          <BanhoTosaPacotesList
            pacotes={pacotes}
            onChanged={recarregarTudo}
            onEdit={editarPacote}
            onDelete={excluirPacote}
          />
          <BanhoTosaCreditosList creditos={creditos} onChanged={recarregarTudo} />
        </>
      )}
    </div>
  );
}

function montarResumo(pacotes, creditos) {
  return {
    ativos: pacotes.filter((pacote) => pacote.ativo).length,
    creditosDisponiveis: creditos.reduce(
      (total, credito) => total + (credito.disponivel ? Number(credito.saldo_creditos || 0) : 0),
      0,
    ),
    valorPacotes: pacotes.reduce((total, pacote) => total + Number(pacote.preco || 0), 0),
  };
}
