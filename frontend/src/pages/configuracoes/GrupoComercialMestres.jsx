import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { FiBox, FiChevronLeft, FiGrid, FiHeart, FiUsers } from "react-icons/fi";

import EmptyState from "../../components/ui/EmptyState";
import LoadingState from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import { obterMestresGrupo } from "../../services/gruposComerciais";

function mensagemErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

const SECOES = [
  { chave: "produtos", titulo: "Produtos", icone: FiBox },
  { chave: "pets", titulo: "Pets", icone: FiHeart },
  { chave: "pessoas", titulo: "Pessoas", icone: FiUsers },
  { chave: "especies", titulo: "Espécies", icone: FiGrid },
  { chave: "racas", titulo: "Raças", icone: FiGrid },
];

function ListaMestre({ itens }) {
  if (!itens || itens.length === 0) {
    return (
      <p className="px-4 py-6 text-center text-sm text-slate-500">
        Nada compartilhado ainda neste domínio.
      </p>
    );
  }
  return (
    <ul className="divide-y divide-slate-100">
      {itens.map((item) => (
        <li key={item.id} className="px-4 py-2.5 text-sm text-slate-800">
          {item.nome}
        </li>
      ))}
    </ul>
  );
}

export default function GrupoComercialMestres() {
  const { grupoId } = useParams();
  const [mestres, setMestres] = useState(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    let cancelado = false;
    async function carregar() {
      try {
        const dados = await obterMestresGrupo(grupoId);
        if (!cancelado) setMestres(dados);
      } catch (error) {
        toast.error(mensagemErro(error, "Não foi possível carregar os dados mestre do grupo."));
      } finally {
        if (!cancelado) setCarregando(false);
      }
    }
    carregar();
    return () => {
      cancelado = true;
    };
  }, [grupoId]);

  if (carregando) {
    return <LoadingState label="Carregando dados compartilhados do grupo..." />;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <Link
        to="/configuracoes/grupos-comerciais"
        className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
      >
        <FiChevronLeft aria-hidden="true" />
        Voltar para Grupos Comerciais
      </Link>

      <PageHeader
        icon={FiGrid}
        title="Dados compartilhados do grupo"
        subtitle="Nome, descrição e ficha técnica só — preço, estoque, prontuário e histórico de compra continuam sempre por loja. Vincular ou desvincular um registro específico se faz no cadastro dele, na loja."
      />

      {mestres ? (
        <div className="grid gap-5 sm:grid-cols-2">
          {SECOES.map((secao) => {
            const itens = mestres[secao.chave] || [];
            const Icone = secao.icone;
            return (
              <Panel
                key={secao.chave}
                title={
                  <span className="flex items-center gap-2">
                    <Icone className="text-slate-500" aria-hidden="true" />
                    {secao.titulo}
                    <span className="text-xs font-normal text-slate-400">
                      ({itens.length})
                    </span>
                  </span>
                }
              >
                <ListaMestre itens={itens} />
              </Panel>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon={FiGrid}
          title="Sem dados"
          description="Não foi possível carregar os dados compartilhados deste grupo."
        />
      )}
    </div>
  );
}
