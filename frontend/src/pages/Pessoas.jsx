/**
 * Página de Gestão de Pessoas (Clientes, Fornecedores, Veterinários)
 */
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FiHelpCircle } from "react-icons/fi";
import { useNavigate } from "react-router-dom";
import api from "../api";
import ModalImportacaoPessoas from "../components/ModalImportacaoPessoas";
import { useTour } from "../hooks/useTour";
import { tourPessoas } from "../tours/tourDefinitions";

export default function Pessoas() {
  const navigate = useNavigate();
  const { iniciarTour } = useTour("pessoas", tourPessoas);
  const [pessoas, setPessoas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tipoFiltro, setTipoFiltro] = useState("todos"); // todos, cliente, fornecedor, veterinario
  const [buscaTexto, setBuscaTexto] = useState("");
  const [modalImportacao, setModalImportacao] = useState(false);

  // Carregar dados iniciais
  useEffect(() => {
    carregarPessoas();
  }, [tipoFiltro, buscaTexto]);

  const carregarPessoas = async () => {
    try {
      setLoading(true);

      let params = {};
      if (tipoFiltro !== "todos") {
        params.tipo_cadastro = tipoFiltro;
      }
      if (buscaTexto) {
        params.busca = buscaTexto;
      }

      const response = await api.get("/clientes/", { params });

      setPessoas(response.data || []);
    } catch (error) {
      console.error("Erro ao carregar pessoas:", error);
      toast.error("Erro ao carregar pessoas");
    } finally {
      setLoading(false);
    }
  };

  const getTipoBadge = (tipo) => {
    const tipos = {
      cliente: { bg: "bg-blue-100", text: "text-blue-800", label: "Cliente" },
      fornecedor: {
        bg: "bg-green-100",
        text: "text-green-800",
        label: "Fornecedor",
      },
      veterinario: {
        bg: "bg-purple-100",
        text: "text-purple-800",
        label: "Veterinário",
      },
    };
    return tipos[tipo] || tipos.cliente;
  };

  const getTipoPessoa = (tipo) => {
    return tipo === "PJ" ? "Pessoa Jurídica" : "Pessoa Física";
  };

  const formatarCPF = (cpf) => {
    if (!cpf) return "-";
    return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
  };

  const formatarCNPJ = (cnpj) => {
    if (!cnpj) return "-";
    return cnpj.replace(
      /(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/,
      "$1.$2.$3/$4-$5",
    );
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Pessoas</h1>
            <p className="text-gray-600 mt-1">
              Gerencie clientes, fornecedores e veterinários
            </p>
          </div>
          <button
            onClick={iniciarTour}
            title="Ver tour guiado desta página"
            className="flex items-center gap-1 px-2 py-1 text-sm text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors mt-1"
          >
            <FiHelpCircle className="text-base" />
            <span className="hidden sm:inline text-xs">Tour</span>
          </button>
        </div>
        <div className="flex gap-2">
          <button
            id="tour-pessoas-importar"
            onClick={() => setModalImportacao(true)}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium flex items-center gap-2"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            Importar
          </button>
          <button
            onClick={() => navigate("/pessoas/novo")}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            Nova Pessoa
          </button>
        </div>
      </div>

      {/* Filtros */}
      <div
        id="tour-pessoas-filtros"
        className="bg-white rounded-lg shadow p-4 mb-6"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Busca */}
          <input
            type="text"
            placeholder="Buscar por nome, CPF, CNPJ..."
            value={buscaTexto}
            onChange={(e) => setBuscaTexto(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />

          {/* Tipo de cadastro */}
          <select
            value={tipoFiltro}
            onChange={(e) => setTipoFiltro(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="todos">Todos os tipos</option>
            <option value="cliente">Clientes</option>
            <option value="fornecedor">Fornecedores</option>
            <option value="veterinario">Veterinários</option>
          </select>
        </div>
      </div>

      {/* Conteúdo */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="text-gray-500">Carregando pessoas...</div>
        </div>
      ) : pessoas.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <div className="text-4xl mb-3">👤</div>
          <p className="text-gray-600">Nenhuma pessoa encontrada</p>
          <button
            onClick={() => navigate("/pessoas/novo")}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Adicionar primeira pessoa
          </button>
        </div>
      ) : (
        <div
          id="tour-pessoas-tabela"
          className="bg-white rounded-lg shadow overflow-hidden"
        >
          <table className="w-full">
            <thead className="bg-gray-100 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Nome
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Tipo
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Pessoa
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Documento
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Contato
                </th>
                <th className="px-6 py-3 text-center text-sm font-semibold text-gray-700">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {pessoas.map((pessoa) => {
                const tipoBadge = getTipoBadge(pessoa.tipo_cadastro);
                return (
                  <tr key={pessoa.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div>
                        <p className="font-medium text-gray-900">
                          {pessoa.nome}
                        </p>
                        {pessoa.codigo && (
                          <p className="text-xs text-gray-500">
                            Cód: {pessoa.codigo}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${tipoBadge.bg} ${tipoBadge.text}`}
                      >
                        {tipoBadge.label}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {getTipoPessoa(pessoa.tipo_pessoa)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {pessoa.tipo_pessoa === "PF"
                        ? formatarCPF(pessoa.cpf)
                        : formatarCNPJ(pessoa.cnpj)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      <div>
                        {pessoa.email && (
                          <p className="text-blue-600 hover:underline cursor-pointer">
                            {pessoa.email}
                          </p>
                        )}
                        {pessoa.celular && (
                          <p className="text-gray-500">{pessoa.celular}</p>
                        )}
                        {!pessoa.email && !pessoa.celular && "-"}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <button
                        onClick={() => navigate(`/pessoas/${pessoa.id}/editar`)}
                        className="text-blue-600 hover:text-blue-800 font-medium text-sm"
                      >
                        Editar
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal de Importação */}
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
