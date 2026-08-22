import React, { useState, useEffect } from "react";
import {
  FiPlus,
  FiEdit2,
  FiTrash2,
  FiChevronDown,
  FiChevronRight,
  FiAlertCircle,
} from "react-icons/fi";
import api from "../../api";
import CatalogoProdutoModal from "../../components/produtos/CatalogoProdutoModal";
import { confirmarCorePet } from "../../services/corepetDialog";

const Categorias = () => {
  const [categorias, setCategorias] = useState([]);
  const [departamentos, setDepartamentos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editando, setEditando] = useState(null);
  const [expandidas, setExpandidas] = useState(new Set());
  const [valoresIniciaisModal, setValoresIniciaisModal] = useState({});

  const MAX_NIVEL = 4; // Limite de 4 níveis

  useEffect(() => {
    carregarCategorias();
    carregarDepartamentos();
  }, []);

  const carregarCategorias = async () => {
    try {
      setLoading(true);
      const response = await api.get("/produtos/categorias");
      setCategorias(response.data);
    } catch (error) {
      console.error("Erro ao carregar categorias:", error);
      alert("Erro ao carregar categorias");
    } finally {
      setLoading(false);
    }
  };

  const carregarDepartamentos = async () => {
    try {
      const response = await api.get("/produtos/departamentos");
      setDepartamentos(response.data);
    } catch (error) {
      console.error("Erro ao carregar departamentos:", error);
    }
  };

  const toggleExpansao = (categoriaId) => {
    const novasExpandidas = new Set(expandidas);
    if (novasExpandidas.has(categoriaId)) {
      novasExpandidas.delete(categoriaId);
    } else {
      novasExpandidas.add(categoriaId);
    }
    setExpandidas(novasExpandidas);
  };

  const handleEditar = (categoria) => {
    setEditando(categoria);
    setValoresIniciaisModal({});
    setShowModal(true);
  };

  const handleExcluir = async (categoria) => {
    if (categoria.total_filhos > 0) {
      alert(`Esta categoria possui ${categoria.total_filhos} subcategoria(s). Remova-as primeiro.`);
      return;
    }

    if (categoria.total_produtos > 0) {
      if (
        !await confirmarCorePet(
          `Esta categoria possui ${categoria.total_produtos} produto(s). Deseja realmente excluir?`,
        )
      ) {
        return;
      }
    }

    try {
      await api.delete(`/produtos/categorias/${categoria.id}`);
      sessionStorage.removeItem("produtos_catalogos_cache_v1");
      carregarCategorias();
    } catch (error) {
      console.error("Erro ao excluir categoria:", error);
      alert(error.response?.data?.detail || "Erro ao excluir categoria");
    }
  };

  const handleNovaSubcategoria = (categoriaPai) => {
    if (categoriaPai.nivel >= MAX_NIVEL) {
      alert(`Limite de ${MAX_NIVEL} níveis de categorias atingido.`);
      return;
    }

    setEditando(null);
    setValoresIniciaisModal({
      categoria_pai_id: categoriaPai.id,
      departamento_id: categoriaPai.departamento_id || null,
      ordem: 0,
    });
    setShowModal(true);
  };

  const handleNovaCategoriaRaiz = () => {
    setEditando(null);
    setValoresIniciaisModal({
      categoria_pai_id: null,
      departamento_id: null,
      ordem: 0,
    });
    setShowModal(true);
  };

  const fecharModal = () => {
    setShowModal(false);
    setEditando(null);
    setValoresIniciaisModal({});
  };

  const handleCategoriaSalva = async () => {
    fecharModal();
    await carregarCategorias();
  };

  const handleDepartamentoCriado = (departamento) => {
    setDepartamentos((atuais) => {
      const semDuplicado = atuais.filter((atual) => String(atual.id) !== String(departamento.id));
      return [...semDuplicado, departamento].sort((a, b) =>
        String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR"),
      );
    });
  };

  // Construir árvore hierárquica
  const construirArvore = (parentId = null, nivel = 1) => {
    return categorias
      .filter((cat) => cat.categoria_pai_id === parentId)
      .sort((a, b) => a.ordem - b.ordem || a.nome.localeCompare(b.nome))
      .map((categoria) => ({
        ...categoria,
        nivel,
        filhos: construirArvore(categoria.id, nivel + 1),
      }));
  };

  // Renderizar categoria recursivamente
  const renderCategoria = (categoria, nivel = 1) => {
    const temFilhos = categoria.filhos && categoria.filhos.length > 0;
    const estaExpandida = expandidas.has(categoria.id);
    const podeAdicionarFilho = nivel < MAX_NIVEL;

    // Calcula a indentação
    const indentacao = (nivel - 1) * 30;

    return (
      <React.Fragment key={categoria.id}>
        <div
          className="flex items-center gap-3 p-3 bg-white hover:bg-gray-50 border-b"
          style={{ paddingLeft: `${20 + indentacao}px` }}
        >
          {/* Ícone de expansão ou placeholder */}
          <div className="w-5 flex items-center justify-center">
            {temFilhos ? (
              <button
                onClick={() => toggleExpansao(categoria.id)}
                className="text-gray-500 hover:text-gray-700 transition-colors"
              >
                {estaExpandida ? <FiChevronDown size={18} /> : <FiChevronRight size={18} />}
              </button>
            ) : (
              <span className="text-gray-300">•</span>
            )}
          </div>

          {/* Nome e informações */}
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-800">{categoria.nome}</span>
              <span className="text-xs text-gray-500">Nível {nivel}</span>
              {categoria.departamento_nome && (
                <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                  {categoria.departamento_nome}
                </span>
              )}
              {categoria.total_filhos > 0 && (
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                  {categoria.total_filhos} sub
                </span>
              )}
              {categoria.total_produtos > 0 && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                  {categoria.total_produtos} produtos
                </span>
              )}
            </div>
            {categoria.descricao && (
              <p className="text-sm text-gray-600 mt-1">{categoria.descricao}</p>
            )}
          </div>

          {/* Ações */}
          <div className="flex items-center gap-2">
            {podeAdicionarFilho && (
              <button
                onClick={() => handleNovaSubcategoria(categoria)}
                className="p-2 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                title="Adicionar subcategoria"
              >
                <FiPlus size={18} />
              </button>
            )}
            {!podeAdicionarFilho && (
              <span
                className="p-2 text-gray-300 cursor-not-allowed"
                title={`Limite de ${MAX_NIVEL} níveis atingido`}
              >
                <FiAlertCircle size={18} />
              </span>
            )}
            <button
              onClick={() => handleEditar(categoria)}
              className="p-2 text-yellow-600 hover:bg-yellow-50 rounded transition-colors"
              title="Editar"
            >
              <FiEdit2 size={18} />
            </button>
            <button
              onClick={() => handleExcluir(categoria)}
              className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors"
              title="Excluir"
            >
              <FiTrash2 size={18} />
            </button>
          </div>
        </div>

        {/* Renderizar filhos se expandido */}
        {temFilhos && estaExpandida && (
          <div>{categoria.filhos.map((filho) => renderCategoria(filho, nivel + 1))}</div>
        )}
      </React.Fragment>
    );
  };

  const arvore = construirArvore();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">Carregando categorias...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Categorias</h1>
          <p className="text-gray-600 mt-1">
            Gerencie suas categorias hierarquicamente (até {MAX_NIVEL} níveis)
          </p>
        </div>
        <button
          onClick={handleNovaCategoriaRaiz}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
        >
          <FiPlus size={20} />
          Nova Categoria
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {arvore.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <FiAlertCircle size={48} className="mx-auto mb-4 opacity-50" />
            <p>Nenhuma categoria cadastrada</p>
            <button
              onClick={handleNovaCategoriaRaiz}
              className="mt-4 text-blue-600 hover:text-blue-700"
            >
              Criar primeira categoria
            </button>
          </div>
        ) : (
          <div>{arvore.map((categoria) => renderCategoria(categoria))}</div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <CatalogoProdutoModal
          tipo="categoria"
          item={editando}
          initialValues={valoresIniciaisModal}
          departamentos={departamentos}
          onClose={fecharModal}
          onDepartamentoCriado={handleDepartamentoCriado}
          onSaved={handleCategoriaSalva}
        />
      )}
    </div>
  );
};

export default Categorias;
