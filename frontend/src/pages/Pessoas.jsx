/**
 * Pagina de Gestao de Pessoas (clientes, fornecedores e veterinarios).
 */
import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { GitMerge, Pencil, Upload, UserPlus, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import ModalImportacaoPessoas from "../components/ModalImportacaoPessoas";
import PessoasFusaoModal from "../components/pessoas/PessoasFusaoModal";
import ActionButton from "../components/ui/ActionButton";
import CustomerIdentity from "../components/ui/CustomerIdentity";
import DataTable from "../components/ui/DataTable";
import EmptyState from "../components/ui/EmptyState";
import IconActionButton from "../components/ui/IconActionButton";
import LoadingState from "../components/ui/LoadingState";
import PageHeader from "../components/ui/PageHeader";
import Panel from "../components/ui/Panel";
import StatusBadge from "../components/ui/StatusBadge";
import InputCheckbox from "../components/v2/InputCheckbox/InputCheckbox";
import InputTexto from "../components/v2/InputTexto/InputTexto";
import SeletorOpcoes from "../components/v2/SeletorOpcoes/SeletorOpcoes";
import { useTour } from "../hooks/useTour";
import useShiftRangeSelection from "../hooks/useShiftRangeSelection";
import { tourPessoas } from "../tours/tourDefinitions";

const OPCOES_TIPO_FILTRO = [
  { valor: "todos", rotulo: "Todos" },
  { valor: "cliente", rotulo: "Clientes" },
  { valor: "fornecedor", rotulo: "Fornecedores" },
  { valor: "veterinario", rotulo: "Veterinarios" },
  { valor: "funcionario", rotulo: "Funcionarios" },
];

const TIPOS_CADASTRO = {
  cliente: { intent: "info", label: "Cliente" },
  fornecedor: { intent: "success", label: "Fornecedor" },
  veterinario: { intent: "purple", label: "Veterinario" },
  funcionario: { intent: "warning", label: "Funcionario" },
};

// Uma pessoa pode ser mais de um tipo ao mesmo tempo (ex. cliente e
// funcionario) — retorna um badge por flag marcada, nao so um.
function getTiposBadges(pessoa) {
  const tipos = [];
  if (pessoa?.is_cliente) tipos.push("cliente");
  if (pessoa?.is_fornecedor) tipos.push("fornecedor");
  if (pessoa?.is_veterinario) tipos.push("veterinario");
  if (pessoa?.is_funcionario) tipos.push("funcionario");
  if (tipos.length === 0) tipos.push("cliente");
  return tipos.map((tipo) => TIPOS_CADASTRO[tipo]);
}

function getTipoPessoa(tipo) {
  return tipo === "PJ" ? "Pessoa Juridica" : "Pessoa Fisica";
}

function formatarCPF(cpf) {
  if (!cpf) return "-";
  return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
}

function formatarCNPJ(cnpj) {
  if (!cnpj) return "-";
  return cnpj.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5");
}

function getDocumentoPessoa(pessoa) {
  return pessoa.tipo_pessoa === "PF" ? formatarCPF(pessoa.cpf) : formatarCNPJ(pessoa.cnpj);
}

export default function Pessoas() {
  const navigate = useNavigate();
  const { iniciarTour } = useTour("pessoas", tourPessoas);
  const [pessoas, setPessoas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tipoFiltro, setTipoFiltro] = useState("todos");
  const [buscaTexto, setBuscaTexto] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [modalImportacao, setModalImportacao] = useState(false);
  const [modalFusao, setModalFusao] = useState(false);
  const [selecionados, setSelecionados] = useState([]);

  const pessoasSelecionadas = useMemo(
    () => pessoas.filter((pessoa) => selecionados.includes(pessoa.id)).slice(0, 2),
    [pessoas, selecionados],
  );

  const carregarPessoas = async () => {
    try {
      setLoading(true);

      const params = {};
      if (tipoFiltro !== "todos") {
        params[`is_${tipoFiltro}`] = true;
      }
      if (buscaAplicada) {
        params.search = buscaAplicada;
      }

      const response = await api.get("/clientes/", { params });
      const lista = response.data?.items || response.data?.clientes || response.data || [];

      setPessoas(Array.isArray(lista) ? lista : []);
    } catch (error) {
      console.error("Erro ao carregar pessoas:", error);
      toast.error("Erro ao carregar pessoas");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => setBuscaAplicada(buscaTexto), 300);
    return () => clearTimeout(timer);
  }, [buscaTexto]);

  useEffect(() => {
    carregarPessoas();
  }, [tipoFiltro, buscaAplicada]);

  useEffect(() => {
    setSelecionados((prev) => prev.filter((id) => pessoas.some((pessoa) => pessoa.id === id)));
  }, [pessoas]);

  const selecionarPessoa = useShiftRangeSelection({
    items: pessoas,
    setSelectedIds: setSelecionados,
  });

  const selecionarTodosVisiveis = () => {
    const idsVisiveis = pessoas.map((pessoa) => pessoa.id);
    const todosSelecionados =
      idsVisiveis.length > 0 && idsVisiveis.every((id) => selecionados.includes(id));

    if (todosSelecionados) {
      setSelecionados((prev) => prev.filter((id) => !idsVisiveis.includes(id)));
      return;
    }

    setSelecionados((prev) => Array.from(new Set([...prev, ...idsVisiveis])));
  };

  const limparSelecao = () => setSelecionados([]);

  const todosVisiveisSelecionados = useMemo(
    () => pessoas.length > 0 && pessoas.every((pessoa) => selecionados.includes(pessoa.id)),
    [pessoas, selecionados],
  );

  const pessoasColumns = useMemo(
    () => [
      {
        key: "acoes",
        header: "Acoes",
        align: "center",
        render: (pessoa) => (
          <IconActionButton
            icon={Pencil}
            intent="edit"
            onClick={() => navigate(`/pessoas/${pessoa.id}/editar`)}
            title="Editar pessoa"
          />
        ),
      },
      {
        key: "selecao",
        align: "center",
        headerClassName: "w-11",
        className: "w-11",
        renderHeader: () => (
          <InputCheckbox
            checked={todosVisiveisSelecionados}
            onChange={selecionarTodosVisiveis}
            rotulo="Selecionar pessoas visiveis"
          />
        ),
        render: (pessoa) => (
          <InputCheckbox
            checked={selecionados.includes(pessoa.id)}
            onChange={(event) => selecionarPessoa(pessoa.id, event)}
            rotulo={`Selecionar ${pessoa.nome}`}
          />
        ),
      },
      {
        key: "nome",
        header: "Nome",
        className: "min-w-[220px]",
        render: (pessoa) => (
          <CustomerIdentity
            customer={pessoa}
            code={pessoa.codigo}
            codeLabel="Cod. pessoa"
            fallback="Pessoa nao informada"
          />
        ),
      },
      {
        key: "tipos_cadastro",
        header: "Tipo",
        render: (pessoa) => (
          <div className="flex flex-wrap gap-1">
            {getTiposBadges(pessoa).map((tipoBadge) => (
              <StatusBadge key={tipoBadge.label} intent={tipoBadge.intent} size="sm">
                {tipoBadge.label}
              </StatusBadge>
            ))}
          </div>
        ),
      },
      {
        key: "tipo_pessoa",
        header: "Pessoa",
        render: (pessoa) => getTipoPessoa(pessoa.tipo_pessoa),
      },
      {
        key: "documento",
        header: "Documento",
        render: getDocumentoPessoa,
      },
      {
        key: "contato",
        header: "Contato",
        className: "min-w-[220px]",
        render: (pessoa) => (
          <div className="space-y-1 text-sm text-slate-600">
            {pessoa.email ? (
              <a className="text-blue-600 hover:underline" href={`mailto:${pessoa.email}`}>
                {pessoa.email}
              </a>
            ) : null}
            {pessoa.celular ? <div className="text-slate-500">{pessoa.celular}</div> : null}
            {!pessoa.email && !pessoa.celular ? "-" : null}
          </div>
        ),
      },
    ],
    [navigate, selecionarPessoa, selecionados, todosVisiveisSelecionados],
  );

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        icon={Users}
        onTour={iniciarTour}
        subtitle="Gerencie clientes, fornecedores e veterinarios"
        title="Pessoas"
        actions={
          <>
            {selecionados.length > 0 ? (
              <ActionButton
                disabled={selecionados.length !== 2}
                icon={GitMerge}
                intent="warning"
                onClick={() => setModalFusao(true)}
                size="md"
                title={
                  selecionados.length === 2
                    ? "Fundir pessoas selecionadas"
                    : "Selecione exatamente 2 pessoas"
                }
              >
                Fundir Pessoas ({selecionados.length})
              </ActionButton>
            ) : null}
            <ActionButton
              id="tour-pessoas-importar"
              icon={Upload}
              intent="info"
              onClick={() => setModalImportacao(true)}
              size="md"
            >
              Importar
            </ActionButton>
            <ActionButton
              id="tour-pessoas-nova"
              icon={UserPlus}
              intent="create"
              onClick={() => navigate("/pessoas/novo")}
              size="md"
            >
              Nova Pessoa
            </ActionButton>
          </>
        }
      />

      <Panel
        id="tour-pessoas-filtros"
        title="Filtros"
        subtitle="Localize cadastros por nome, documento ou tipo."
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <InputTexto
            label="Buscar"
            placeholder="Nome, CPF, CNPJ..."
            value={buscaTexto}
            onChange={setBuscaTexto}
          />

          <SeletorOpcoes
            rotulo="Tipo"
            opcoes={OPCOES_TIPO_FILTRO}
            valorSelecionado={tipoFiltro}
            aoSelecionar={setTipoFiltro}
          />
        </div>
      </Panel>

      {loading ? (
        <Panel>
          <LoadingState label="Carregando pessoas..." />
        </Panel>
      ) : pessoas.length === 0 ? (
        <EmptyState
          icon={Users}
          title="Nenhuma pessoa encontrada"
          description="Cadastre o primeiro cliente, fornecedor ou veterinario deste tenant."
          action={
            <ActionButton
              icon={UserPlus}
              intent="create"
              onClick={() => navigate("/pessoas/novo")}
              size="md"
            >
              Adicionar primeira pessoa
            </ActionButton>
          }
        />
      ) : (
        <Panel id="tour-pessoas-tabela" padding="none" className="overflow-hidden">
          <DataTable
            columns={pessoasColumns}
            data={pessoas}
            emptyMessage="Nenhuma pessoa encontrada"
            getRowKey={(pessoa) => pessoa.id}
          />
        </Panel>
      )}

      <PessoasFusaoModal
        isOpen={modalFusao}
        onClose={() => setModalFusao(false)}
        onSuccess={() => {
          carregarPessoas();
          limparSelecao();
        }}
        pessoasSelecionadas={pessoasSelecionadas}
      />

      <ModalImportacaoPessoas
        isOpen={modalImportacao}
        onClose={() => {
          setModalImportacao(false);
          carregarPessoas();
        }}
      />
    </div>
  );
}
