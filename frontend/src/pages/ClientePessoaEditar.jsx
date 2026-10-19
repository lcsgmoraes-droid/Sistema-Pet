import { useCallback, useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { ExternalLink, PawPrint, User } from "lucide-react";
import { FiChevronLeft } from "react-icons/fi";
import api from "../api";
import EmptyState from "../components/ui/EmptyState";
import LoadingState from "../components/ui/LoadingState";
import PageHeader from "../components/ui/PageHeader";
import Panel from "../components/ui/Panel";
import BotaoInteracao from "../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../components/v2/BotaoSalva/BotaoSalva";
import LinkPadrao from "../components/v2/LinkPadrao/LinkPadrao";
import PessoaFormulario from "../components/clientes/PessoaFormulario";

function mensagemErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

const ABAS_VALIDAS = ["dados-gerais", "contatos", "endereco", "alertas-pdv", "financeiro"];

// Aba inicial: `location.state.abaInicial` quando a navegação vem de dentro do
// app (ex.: clique num link da própria SPA); `?aba=` na URL quando vem de um
// link externo/recarregado (ex.: "Corrigir cadastro" na pendência fiscal, que
// usa <a href> normal e por isso não carrega state do React Router).
function resolverAbaInicial(location) {
  if (ABAS_VALIDAS.includes(location.state?.abaInicial)) {
    return location.state.abaInicial;
  }
  const abaDaUrl = new URLSearchParams(location.search).get("aba");
  if (ABAS_VALIDAS.includes(abaDaUrl)) {
    return abaDaUrl;
  }
  return "dados-gerais";
}

function formatarDataHoraCadastro(valor) {
  if (!valor) return "Data não registrada";
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return "Data não registrada";
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(data);
}

const FORM_ID = "pessoa-formulario-pagina";

export default function ClientePessoaEditar() {
  const { clienteId } = useParams();
  const location = useLocation();

  const [cliente, setCliente] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [naoEncontrado, setNaoEncontrado] = useState(false);
  const [salvando, setSalvando] = useState(false);

  // `aindaAtivo` protege contra o StrictMode do React, que em dev roda este efeito duas vezes de
  // proposito — sem isso, a segunda rodada reacende "carregando" por um instante mesmo com os
  // dados ja exibidos na tela (mesmo problema resolvido em PetForm.jsx, ver nota no AGENTS.md).
  const carregar = useCallback(
    async (aindaAtivo = () => true) => {
      setCarregando(true);
      setNaoEncontrado(false);
      try {
        const { data } = await api.get(`/clientes/${clienteId}`);
        if (!aindaAtivo()) return;
        setCliente(data);
      } catch (error) {
        if (!aindaAtivo()) return;
        if (error.response?.status === 404) {
          setNaoEncontrado(true);
        } else {
          toast.error(mensagemErro(error, "Não foi possível carregar esta pessoa."));
        }
      } finally {
        if (aindaAtivo()) setCarregando(false);
      }
    },
    [clienteId],
  );

  useEffect(() => {
    let ativo = true;
    carregar(() => ativo);
    return () => {
      ativo = false;
    };
  }, [carregar]);

  if (carregando) {
    return <LoadingState label="Carregando cadastro..." />;
  }

  if (naoEncontrado || !cliente) {
    return (
      <div className="space-y-6 p-6">
        <LinkPadrao to={location.state?.from || "/clientes"}>
          <FiChevronLeft aria-hidden="true" />
          Voltar para Pessoas
        </LinkPadrao>
        <EmptyState
          title="Pessoa não encontrada"
          description="Este cadastro pode ter sido removido."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <LinkPadrao to={location.state?.from || "/clientes"}>
        <FiChevronLeft aria-hidden="true" />
        Voltar para Pessoas
      </LinkPadrao>

      <PageHeader
        icon={User}
        title={cliente.nome}
        subtitle={
          <>
            Código {cliente.codigo || cliente.id} · Editando cadastro · Criado em{" "}
            {formatarDataHoraCadastro(cliente.created_at)} · Criado por{" "}
            {cliente.criado_por_nome || cliente.criado_por_email || "Usuário não registrado"}
          </>
        }
        actions={
          <div className="flex items-center gap-2">
            <BotaoInteracao
              icon={PawPrint}
              tamanho="grande"
              onClick={() =>
                window.open(`/pets?cliente_id=${cliente.id}`, "_blank", "noopener,noreferrer")
              }
            >
              Gerenciar pets
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="sr-only"> (abre em nova aba)</span>
            </BotaoInteracao>
            <BotaoSalva form={FORM_ID} loading={salvando} tamanho="grande">
              Salvar
            </BotaoSalva>
          </div>
        }
      />

      <Panel padding="none">
        <div className="p-4">
          <PessoaFormulario
            abaInicial={resolverAbaInicial(location)}
            formId={FORM_ID}
            onEnderecoSalvo={setCliente}
            onSalvandoChange={setSalvando}
            onSalvo={setCliente}
            pessoa={cliente}
          />
        </div>
      </Panel>
    </div>
  );
}
