import { useEffect, useState } from "react";
import { Coins, PackageCheck, Plus, RefreshCw, WalletCards } from "lucide-react";
import toast from "react-hot-toast";
import ActionButton from "../../../components/ui/ActionButton";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, formatNumber, getApiErrorMessage } from "../banhoTosaUtils";
import BanhoTosaCreditoForm from "./BanhoTosaCreditoForm";
import BanhoTosaCreditosList from "./BanhoTosaCreditosList";
import BanhoTosaPacoteForm from "./BanhoTosaPacoteForm";
import BanhoTosaPacotesList from "./BanhoTosaPacotesList";

export default function BanhoTosaPacotesView({ servicos = [], onChanged }) {
  const [pacotes, setPacotes] = useState([]);
  const [creditos, setCreditos] = useState([]);
  const [editingPacote, setEditingPacote] = useState(null);
  const [showPacoteForm, setShowPacoteForm] = useState(false);
  const [showCreditoForm, setShowCreditoForm] = useState(false);
  const [loading, setLoading] = useState(false);

  async function carregar() {
    setLoading(true);
    try {
      const [pacotesRes, creditosRes] = await Promise.all([
        banhoTosaApi.listarPacotes(),
        banhoTosaApi.listarCreditosPacote({ limit: 300 }),
      ]);
      setPacotes(Array.isArray(pacotesRes.data) ? pacotesRes.data : []);
      setCreditos(Array.isArray(creditosRes.data) ? creditosRes.data : []);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel carregar pacotes."));
      setPacotes([]);
      setCreditos([]);
    } finally {
      setLoading(false);
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
    const confirmou = window.confirm(
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
  }, []);

  const resumo = montarResumo(pacotes, creditos);

  return (
    <div className="space-y-4">
      <Panel
        actions={
          <>
            <ActionButton
              icon={Plus}
              intent="create"
              onClick={() => {
                setEditingPacote(null);
                setShowPacoteForm((value) => !value);
              }}
            >
              Novo pacote
            </ActionButton>
            <ActionButton
              icon={WalletCards}
              intent="create"
              tone="soft"
              onClick={() => setShowCreditoForm((value) => !value)}
            >
              Liberar credito
            </ActionButton>
            <ActionButton
              icon={RefreshCw}
              intent="neutral"
              loading={loading}
              onClick={carregar}
              tone="soft"
            >
              Atualizar
            </ActionButton>
          </>
        }
        subtitle="Cadastre planos, libere creditos para clientes e acompanhe saldos sem abrir formularios desnecessarios."
        title="Pacotes e creditos"
      />

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
          label="Creditos em aberto"
          value={formatNumber(resumo.creditosDisponiveis, 0)}
        />
        <MetricCard
          intent="violet"
          label="Receita cadastrada"
          value={formatCurrency(resumo.valorPacotes)}
        />
      </MetricGrid>

      {(showPacoteForm || editingPacote || showCreditoForm) && (
        <div className="grid gap-4 xl:grid-cols-2">
          {(showPacoteForm || editingPacote) && (
            <BanhoTosaPacoteForm
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
      <BanhoTosaCreditosList creditos={creditos} />
    </div>
  );
}

function montarResumo(pacotes, creditos) {
  return {
    ativos: pacotes.filter((pacote) => pacote.ativo).length,
    creditosDisponiveis: creditos.reduce(
      (total, credito) => total + Number(credito.saldo_creditos || 0),
      0,
    ),
    valorPacotes: pacotes.reduce((total, pacote) => total + Number(pacote.preco || 0), 0),
  };
}
