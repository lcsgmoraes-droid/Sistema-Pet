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
import { useTour } from "../hooks/useTour";
import { tourPessoas } from "../tours/tourDefinitions";

const TIPOS_CADASTRO = {
  cliente: { intent: "info", label: "Cliente" },
  fornecedor: { intent: "success", label: "Fornecedor" },
  veterinario: { intent: "purple", label: "Veterinario" },
};

function getTipoBadge(tipo) {
  return TIPOS_CADASTRO[tipo] || TIPOS_CADASTRO.cliente;
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
  return cnpj.replace(
    /(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/,
    "$1.$2.$3/$4-$5",
  );
}

function getDocumentoPessoa(pessoa) {
  return pessoa.tipo_pessoa === "PF"
    ? formatarCPF(pessoa.cpf)
    : formatarCNPJ(pessoa.cnpj);
}

export default function Pessoas() {
  const navigate = useNavigate();
  const { iniciarTour } = useTour("pessoas", tourPessoas);
  const [pessoas, setPessoas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tipoFiltro, setTipoFiltro] = useState("todos");
  const [buscaTexto, setBuscaTexto] = useState("");
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
        params.tipo_cadastro = tipoFiltro;
      }
      if (buscaTexto) {
        params.search = buscaTexto;
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
    carregarPessoas();
  }, [tipoFiltro, buscaTexto]);

  useEffect(() => {
    setSelecionados((prev) =>
      prev.filter((id) => pessoas.some((pessoa) => pessoa.id === id)),
    );
  }, [pessoas]);

  const selecionarPessoa = (id) => {
    setSelecionados((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

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
        key: "selecao",
        align: "center",
        headerClassName: "w-10",
        className: "w-10",
        renderHeader: () => (
          <input
            type="checkbox"
            checked={todosVisiveisSelecionados}
            onChange={selecionarTodosVisiveis}
            className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            title="Selecionar pessoas visiveis"
          />
        ),
        render: (pessoa) => (
          <input
            type="checkbox"
            checked={selecionados.includes(pessoa.id)}
            onChange={() => selecionarPessoa(pessoa.id)}
            className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            aria-label={`Selecionar ${pessoa.nome}`}
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
        key: "tipo_cadastro",
        header: "Tipo",
        render: (pessoa) => {
          const tipoBadge = getTipoBadge(pessoa.tipo_cadastro);
          return (
            <StatusBadge intent={tipoBadge.intent} size="sm">
              {tipoBadge.label}
            </StatusBadge>
          );
        },
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
    ],
    [navigate, selecionados, todosVisiveisSelecionados],
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
          <input
            type="text"
            placeholder="Buscar por nome, CPF, CNPJ..."
            value={buscaTexto}
            onChange={(event) => setBuscaTexto(event.target.value)}
            className="h-9 rounded-lg border border-slate-300 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />

          <select
            value={tipoFiltro}
            onChange={(event) => setTipoFiltro(event.target.value)}
            className="h-9 rounded-lg border border-slate-300 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          >
            <option value="todos">Todos os tipos</option>
            <option value="cliente">Clientes</option>
            <option value="fornecedor">Fornecedores</option>
            <option value="veterinario">Veterinarios</option>
          </select>
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
        <Panel
          id="tour-pessoas-tabela"
          padding="none"
          className="overflow-hidden"
        >
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
