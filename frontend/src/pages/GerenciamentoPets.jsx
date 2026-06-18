import { useState, useEffect } from "react";
import toast from "react-hot-toast";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "../api";
import {
  AlertCircle,
  CheckCircle2,
  Eye,
  Filter,
  PawPrint,
  Pencil,
  Plus,
  Search,
  X,
  XCircle,
} from "lucide-react";
import ActionButton from "../components/ui/ActionButton";
import CustomerIdentity from "../components/ui/CustomerIdentity";
import EmptyState from "../components/ui/EmptyState";
import IconActionButton from "../components/ui/IconActionButton";
import LoadingState from "../components/ui/LoadingState";
import PageHeader from "../components/ui/PageHeader";
import Panel from "../components/ui/Panel";
import EntityCard, { EntityInfoRow } from "../components/ui/EntityCard";
import FilterBar, { FilterAdvanced, FilterRow } from "../components/ui/FilterBar";
import PessoaSelector from "../components/clientes/PessoaSelector";
import { formatarIdadeMeses } from "../helpers/idadeHelper";

const GerenciamentoPets = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const clienteIdParam = searchParams.get("cliente_id");

  const [pets, setPets] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Filtros
  const [buscaTutor, setBuscaTutor] = useState("");
  const [busca, setBusca] = useState("");
  const [clientesSugeridos, setClientesSugeridos] = useState([]);
  const [sugestaoCongelada, setSugestaoCongelada] = useState(false);
  const [clienteFiltro, setClienteFiltro] = useState(clienteIdParam || "");
  const [especieFiltro, setEspecieFiltro] = useState("");
  const [statusFiltro, setStatusFiltro] = useState(""); // '', 'ativo', 'inativo'
  const [mostrarFiltros, setMostrarFiltros] = useState(false);

  // Carregar dados
  useEffect(() => {
    loadPets();
    loadClientes();
  }, [clienteFiltro, especieFiltro, statusFiltro]);

  const loadPets = async () => {
    if (busca.trim() && !clienteFiltro) {
      setPets([]);
      setError("Para pesquisar pet, primeiro selecione o tutor (nome, telefone ou CPF).");
      return;
    }

    try {
      setLoading(true);
      const params = new URLSearchParams();

      if (busca) params.append("busca", busca);
      if (clienteFiltro) params.append("cliente_id", clienteFiltro);
      if (especieFiltro) params.append("especie", especieFiltro);
      if (statusFiltro) params.append("ativo", statusFiltro === "ativo" ? "true" : "false");

      const response = await api.get(`/pets?${params.toString()}`);
      const lista = response.data?.items || response.data?.pets || response.data || [];
      setPets(Array.isArray(lista) ? lista : []);
      setError("");
    } catch (err) {
      console.error("Erro ao carregar pets:", err);
      setError("Erro ao carregar pets");
    } finally {
      setLoading(false);
    }
  };

  const loadClientes = async () => {
    try {
      const response = await api.get("/clientes/");
      const lista = response.data?.items || response.data?.clientes || response.data || [];
      setClientes(Array.isArray(lista) ? lista : []);
    } catch (err) {
      console.error("Erro ao carregar clientes:", err);
      setClientes([]);
    }
  };

  useEffect(() => {
    const termo = buscaTutor.trim();
    if (!termo || sugestaoCongelada) {
      setClientesSugeridos([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const termoDigitos = termo.replace(/\D/g, "");
        const termoBusca = termoDigitos.length >= 8 ? termoDigitos : termo;
        const response = await api.get("/clientes/", {
          params: { search: termoBusca, limit: 20 },
        });
        const lista = response.data?.items || response.data?.clientes || response.data || [];
        setClientesSugeridos(Array.isArray(lista) ? lista : []);
      } catch {
        setClientesSugeridos([]);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [buscaTutor, sugestaoCongelada]);

  const selecionarTutor = (cliente) => {
    setClienteFiltro(String(cliente.id));
    setBuscaTutor(cliente.nome || "");
    setSugestaoCongelada(true);
    setClientesSugeridos([]);
    setError("");
  };

  const handleBusca = (e) => {
    e.preventDefault();
    loadPets();
  };

  const limparFiltros = () => {
    setBuscaTutor("");
    setBusca("");
    setSugestaoCongelada(false);
    setClienteFiltro("");
    setEspecieFiltro("");
    setStatusFiltro("");
    setClientesSugeridos([]);
    setError("");
  };

  const calcularIdade = (dataNascimento) => {
    if (!dataNascimento) return null;
    const hoje = new Date();
    const nascimento = new Date(dataNascimento);
    const anos = hoje.getFullYear() - nascimento.getFullYear();
    const meses = hoje.getMonth() - nascimento.getMonth();

    if (anos === 0) {
      return `${meses} ${meses === 1 ? "mês" : "meses"}`;
    }
    return `${anos} ${anos === 1 ? "ano" : "anos"}`;
  };

  const obterIdadePet = (pet) => {
    const idadeMeses = pet.idade_meses ?? pet.idade_aproximada;

    if (idadeMeses !== null && idadeMeses !== undefined && idadeMeses !== "") {
      const meses = Number(idadeMeses);
      return Number.isFinite(meses) ? formatarIdadeMeses(meses) : String(idadeMeses);
    }

    return pet.data_nascimento ? calcularIdade(pet.data_nascimento) : "";
  };

  const toggleAtivacao = async (pet) => {
    try {
      if (pet.ativo) {
        // Desativar (soft delete)
        await api.delete(`/pets/${pet.id}?soft_delete=true`);
      } else {
        // Reativar
        await api.post(`/pets/${pet.id}/ativar`);
      }
      loadPets();
    } catch (err) {
      console.error("Erro ao alterar status do pet:", err);
      toast.error("Nao foi possivel alterar o status do pet.");
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <Panel>
          <LoadingState label="Carregando pets..." />
        </Panel>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <PageHeader
        icon={PawPrint}
        title="Gerenciamento de Pets"
        subtitle={
          clienteFiltro
            ? `Pets do cliente: ${clientes.find((c) => String(c.id) === String(clienteFiltro))?.nome || ""}`
            : "Gestao completa dos animais de estimacao"
        }
        actions={
          <ActionButton
            onClick={() => navigate("/pets/novo")}
            intent="create"
            icon={Plus}
            size="md"
          >
            Adicionar Pet
          </ActionButton>
        }
      />

      {/* Barra de busca e filtros */}
      <FilterBar onSubmit={handleBusca}>
        {/* Busca principal */}
        <FilterRow className="items-stretch">
          <div className="relative w-full md:min-w-64 md:flex-1">
            <PessoaSelector
              minChars={0}
              onChange={(value) => {
                setBuscaTutor(value);
                setSugestaoCongelada(false);
                if (!value.trim()) {
                  setClienteFiltro("");
                }
              }}
              onSelect={selecionarTutor}
              placeholder="Buscar tutor por nome, telefone ou CPF..."
              showSuggestions={Boolean(clientesSugeridos.length > 0 && buscaTutor.trim())}
              suggestions={clientesSugeridos}
              value={buscaTutor}
            />
          </div>

          <div className="relative w-full md:min-w-64 md:flex-1">
            <Search
              size={18}
              className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              placeholder={clienteFiltro ? "Buscar pet pelo nome..." : "Primeiro selecione o tutor"}
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              disabled={!clienteFiltro}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            />
          </div>
          <ActionButton type="submit" intent="neutral" className="w-full md:w-auto" size="md">
            Buscar
          </ActionButton>
          <ActionButton
            type="button"
            onClick={() => setMostrarFiltros(!mostrarFiltros)}
            intent="neutral"
            tone="soft"
            icon={Filter}
            className="w-full md:w-auto"
            size="md"
          >
            Filtros
          </ActionButton>
        </FilterRow>

        {/* Filtros avançados */}
        {mostrarFiltros && (
          <FilterAdvanced className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cliente (Tutor)
              </label>
              <select
                value={clienteFiltro}
                onChange={(e) => {
                  setClienteFiltro(e.target.value);
                  if (!e.target.value) {
                    setBuscaTutor("");
                    return;
                  }
                  const encontrado = clientes.find((c) => String(c.id) === String(e.target.value));
                  if (encontrado?.nome) {
                    setBuscaTutor(encontrado.nome);
                  }
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              >
                <option value="">Todos os clientes</option>
                {clientes.map((cliente) => (
                  <option key={cliente.id} value={cliente.id}>
                    {cliente.nome}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Espécie</label>
              <select
                value={especieFiltro}
                onChange={(e) => setEspecieFiltro(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              >
                <option value="">Todas as espécies</option>
                <option value="Cão">Cão</option>
                <option value="Gato">Gato</option>
                <option value="Ave">Ave</option>
                <option value="Roedor">Roedor</option>
                <option value="Réptil">Réptil</option>
                <option value="Outro">Outro</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={statusFiltro}
                onChange={(e) => setStatusFiltro(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              >
                <option value="">Todos</option>
                <option value="ativo">Ativos</option>
                <option value="inativo">Inativos</option>
              </select>
            </div>

            <div className="flex justify-end md:col-span-3">
              <ActionButton
                type="button"
                onClick={limparFiltros}
                intent="neutral"
                tone="ghost"
                icon={X}
                className="w-full md:w-auto"
                size="sm"
              >
                Limpar filtros
              </ActionButton>
            </div>
          </FilterAdvanced>
        )}
      </FilterBar>

      {/* Erro */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {/* Lista de pets */}
      {pets.length === 0 ? (
        <EmptyState
          icon={PawPrint}
          title="Nenhum pet encontrado"
          description={
            busca || clienteFiltro || especieFiltro || statusFiltro
              ? "Tente ajustar os filtros ou fazer uma nova busca."
              : "Comece adicionando o primeiro pet deste tenant."
          }
          action={
            <ActionButton
              onClick={() => navigate("/pets/novo")}
              intent="create"
              icon={Plus}
              size="lg"
            >
              Adicionar Primeiro Pet
            </ActionButton>
          }
        />
      ) : (
        <div className="grid auto-rows-fr grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {pets.map((pet) => {
            const infoRows = [
              { label: "Espécie:", value: pet.especie || "" },
              { label: "Raça:", value: pet.raca || "" },
              { label: "Sexo:", value: pet.sexo || "" },
              { label: "Idade:", value: obterIdadePet(pet) },
            ];

            return (
              <EntityCard
                key={pet.id}
                title={pet.nome}
                subtitle={pet.codigo}
                inactive={!pet.ativo}
                statusIcon={
                  pet.ativo ? (
                    <CheckCircle2 className="text-emerald-500" size={16} />
                  ) : (
                    <XCircle className="text-red-500" size={16} />
                  )
                }
                media={
                  pet.foto_url ? (
                    <img
                      src={pet.foto_url}
                      alt={pet.nome}
                      className="h-16 w-16 rounded-full border-2 border-slate-200 object-cover"
                    />
                  ) : null
                }
                actions={
                  <>
                    <ActionButton
                      onClick={() => navigate(`/pets/${pet.id}`)}
                      className="flex-1"
                      intent="edit"
                      icon={Eye}
                      size="sm"
                    >
                      Ver Detalhes
                    </ActionButton>
                    <IconActionButton
                      onClick={() => navigate(`/pets/${pet.id}/editar`)}
                      intent="edit"
                      icon={Pencil}
                      size="sm"
                      title="Editar"
                      aria-label={`Editar ${pet.nome}`}
                    />
                    <IconActionButton
                      onClick={() => toggleAtivacao(pet)}
                      intent={pet.ativo ? "delete" : "create"}
                      icon={pet.ativo ? XCircle : CheckCircle2}
                      size="sm"
                      title={pet.ativo ? "Desativar" : "Reativar"}
                      aria-label={pet.ativo ? `Desativar ${pet.nome}` : `Reativar ${pet.nome}`}
                    />
                  </>
                }
              >
                <div className="space-y-1.5">
                  {infoRows.map((row) => (
                    <EntityInfoRow key={row.label} label={row.label} value={row.value} />
                  ))}
                </div>
                <div className="mt-3 border-t border-slate-100 pt-3">
                  <EntityInfoRow
                    label="Tutor:"
                    value={
                      <CustomerIdentity
                        codeLabel="Cod. tutor"
                        fallback={`Tutor #${pet.cliente_id || "-"}`}
                        className="w-full max-w-full"
                        nameClassName="font-medium text-blue-600"
                        nameWrapperClassName="max-w-full"
                        record={pet}
                      />
                    }
                  />
                </div>
              </EntityCard>
            );
          })}
        </div>
      )}

      {/* Resumo */}
      {pets.length > 0 && (
        <div className="mt-6 text-center text-sm text-gray-600">
          Total: <strong>{pets.length}</strong> pet(s) encontrado(s)
          {statusFiltro === "" && (
            <>
              {" • "}
              <strong className="text-green-600">{pets.filter((p) => p.ativo).length}</strong>{" "}
              ativo(s)
              {" • "}
              <strong className="text-red-600">{pets.filter((p) => !p.ativo).length}</strong>{" "}
              inativo(s)
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default GerenciamentoPets;
