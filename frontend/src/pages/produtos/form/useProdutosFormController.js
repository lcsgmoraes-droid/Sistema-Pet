import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getProduto,
  createProduto,
  updateProduto,
  getCategorias,
  getMarcas,
  getDepartamentos,
  gerarSKU,
  uploadImagemProduto,
  deleteImagemProduto,
  getFornecedoresProduto,
  addFornecedorProduto,
  updateFornecedorProduto,
  deleteFornecedorProduto,
  getLotes,
  entradaEstoque,
  saidaFIFO,
} from "../../../api/produtos";
import api from "../../../api";
import {
  montarEstadoProdutoFormulario,
  montarProdutoComAlteracao,
  montarPayloadProdutoParaSalvar,
  validarArquivoImagemProduto,
  validarProdutoParaSalvar,
} from "../../produtosFormUtils";

export function useProdutosFormController() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [abaAtiva, setAbaAtiva] = useState("dados");
  const [loading, setLoading] = useState(false);
  const [salvando, setSalvando] = useState(false);

  // Listas auxiliares
  const [categorias, setCategorias] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [departamentos, setDepartamentos] = useState([]);
  const [clientes, setClientes] = useState([]);

  // Dados do produto
  const [produto, setProduto] = useState(() => montarEstadoProdutoFormulario());

  // Imagens
  const [imagens, setImagens] = useState([]);
  const [uploadingImage, setUploadingImage] = useState(false);

  // Fornecedores
  const [fornecedores, setFornecedores] = useState([]);
  const [showModalFornecedor, setShowModalFornecedor] = useState(false);
  const [fornecedorEdit, setFornecedorEdit] = useState(null);

  // Lotes
  const [lotes, setLotes] = useState([]);
  const [showModalLote, setShowModalLote] = useState(false);
  const [tipoMovimento, setTipoMovimento] = useState("entrada");

  // Variações (Sprint 2)
  const [variacoes, setVariacoes] = useState([]);
  const [loadingVariacoes, setLoadingVariacoes] = useState(false);

  // Carregar dados iniciais
  useEffect(() => {
    carregarCategorias();
    carregarMarcas();
    carregarDepartamentos();
    carregarClientes();

    if (isEdit) {
      carregarProduto();
    }
  }, [id]);

  const carregarCategorias = async () => {
    try {
      const response = await getCategorias({ apenas_ativas: true });
      setCategorias(response.data);
    } catch (error) {
      console.error("Erro ao carregar categorias:", error);
    }
  };

  const carregarMarcas = async () => {
    try {
      const response = await getMarcas({ apenas_ativas: true });
      setMarcas(response.data);
    } catch (error) {
      console.error("Erro ao carregar marcas:", error);
    }
  };

  const carregarDepartamentos = async () => {
    try {
      const response = await getDepartamentos({ apenas_ativos: true });
      setDepartamentos(response.data);
    } catch (error) {
      console.error("Erro ao carregar departamentos:", error);
    }
  };

  const carregarClientes = async () => {
    try {
      const response = await api.get("/clientes/", {
        params: { tipo: "fornecedor", apenas_ativos: true },
      });
      setClientes(response.data);
    } catch (error) {
      console.error("Erro ao carregar clientes:", error);
    }
  };

  const carregarProduto = async () => {
    try {
      setLoading(true);
      const response = await getProduto(id);
      const prod = response.data;

      setProduto(montarEstadoProdutoFormulario(prod));

      // Carregar imagens
      if (prod.imagens && prod.imagens.length > 0) {
        setImagens(prod.imagens);
      }

      // Carregar fornecedores
      carregarFornecedores();

      // Carregar lotes se tiver controle
      if (prod.controle_lote) {
        carregarLotes();
      }

      // 🔒 SPRINT 2: Carregar variações se for produto PAI
      if (prod.tipo_produto === "PAI") {
        carregarVariacoes();
      }
    } catch (error) {
      console.error("Erro ao carregar produto:", error);
      alert("Erro ao carregar produto");
      navigate("/produtos");
    } finally {
      setLoading(false);
    }
  };

  const carregarFornecedores = async () => {
    if (!id) return;
    try {
      const response = await getFornecedoresProduto(id);
      setFornecedores(response.data);
    } catch (error) {
      console.error("Erro ao carregar fornecedores:", error);
    }
  };

  const carregarLotes = async () => {
    if (!id) return;
    try {
      const response = await getLotes(id);
      setLotes(response.data);
    } catch (error) {
      console.error("Erro ao carregar lotes:", error);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setProduto((prev) => montarProdutoComAlteracao(prev, { name, value, type, checked }));
  };

  // 🔒 SPRINT 2: Carregar variações do produto PAI
  const carregarVariacoes = async () => {
    if (!id) return;

    try {
      setLoadingVariacoes(true);
      const response = await api.get(`/produtos/${id}/variacoes`);
      setVariacoes(response.data || []);
    } catch (error) {
      console.error("Erro ao carregar variações:", error);
      setVariacoes([]);
    } finally {
      setLoadingVariacoes(false);
    }
  };

  const handleGerarCodigo = async () => {
    try {
      const response = await gerarSKU();
      setProduto((prev) => ({ ...prev, codigo: response.data.sku }));
    } catch (error) {
      console.error("Erro ao gerar código:", error);
      alert("Erro ao gerar código");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const mensagemValidacao = validarProdutoParaSalvar(produto);
    if (mensagemValidacao) {
      alert(mensagemValidacao);
      return;
    }

    try {
      setSalvando(true);

      const dados = montarPayloadProdutoParaSalvar(produto);

      if (isEdit) {
        await updateProduto(id, dados);
        alert("Produto atualizado com sucesso!");
      } else {
        const response = await createProduto(dados);
        alert("Produto cadastrado com sucesso!");
        navigate(`/produtos/${response.data.id}/editar`);
      }
    } catch (error) {
      console.error("Erro ao salvar produto:", error);
      alert(error.response?.data?.detail || "Erro ao salvar produto");
    } finally {
      setSalvando(false);
    }
  };

  // ==================== IMAGENS ====================

  const handleUploadImagem = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const mensagemValidacao = validarArquivoImagemProduto(file);
    if (mensagemValidacao) {
      alert(mensagemValidacao);
      return;
    }

    try {
      setUploadingImage(true);

      const formData = new FormData();
      formData.append("file", file);

      const response = await uploadImagemProduto(id, formData);
      setImagens((prev) => [...prev, response.data]);

      alert("Imagem enviada com sucesso!");
    } catch (error) {
      console.error("Erro ao enviar imagem:", error);
      alert(error.response?.data?.detail || "Erro ao enviar imagem");
    } finally {
      setUploadingImage(false);
      e.target.value = "";
    }
  };

  const handleDeleteImagem = async (imagemId) => {
    if (!confirm("Deseja realmente excluir esta imagem?")) return;

    try {
      await deleteImagemProduto(imagemId);
      setImagens((prev) => prev.filter((img) => img.id !== imagemId));
      alert("Imagem excluída com sucesso!");
    } catch (error) {
      console.error("Erro ao excluir imagem:", error);
      alert("Erro ao excluir imagem");
    }
  };

  const handleSetPrincipal = async (imagemId) => {
    try {
      await api.put(`/produtos/imagens/${imagemId}`, { principal: true });
      setImagens((prev) =>
        prev.map((img) => ({
          ...img,
          e_principal: img.id === imagemId,
        })),
      );
      alert("Imagem principal atualizada!");
    } catch (error) {
      console.error("Erro ao definir imagem principal:", error);
      alert("Erro ao definir imagem principal");
    }
  };

  // ==================== FORNECEDORES ====================

  const handleAddFornecedor = () => {
    setFornecedorEdit(null);
    setShowModalFornecedor(true);
  };

  const handleEditFornecedor = (fornecedor) => {
    setFornecedorEdit(fornecedor);
    setShowModalFornecedor(true);
  };

  const handleSaveFornecedor = async (dados) => {
    try {
      if (fornecedorEdit) {
        await updateFornecedorProduto(fornecedorEdit.id, dados);
        alert("Fornecedor atualizado!");
      } else {
        await addFornecedorProduto(id, dados);
        alert("Fornecedor vinculado!");
      }

      carregarFornecedores();
      setShowModalFornecedor(false);
    } catch (error) {
      console.error("Erro ao salvar fornecedor:", error);
      alert(error.response?.data?.detail || "Erro ao salvar fornecedor");
    }
  };

  const handleDeleteFornecedor = async (fornecedorId) => {
    if (!confirm("Deseja realmente desvincular este fornecedor?")) return;

    try {
      await deleteFornecedorProduto(fornecedorId);
      carregarFornecedores();
      alert("Fornecedor desvinculado!");
    } catch (error) {
      console.error("Erro ao desvincular fornecedor:", error);
      alert("Erro ao desvincular fornecedor");
    }
  };

  // ==================== LOTES ====================

  const handleMovimentoEstoque = (tipo) => {
    setTipoMovimento(tipo);
    setShowModalLote(true);
  };

  const handleSaveMovimento = async (dados) => {
    try {
      if (tipoMovimento === "entrada") {
        await entradaEstoque(id, dados);
        alert("Entrada registrada com sucesso!");
      } else {
        await saidaFIFO(id, dados);
        alert("Saída registrada com sucesso!");
      }

      carregarLotes();
      carregarProduto();
      setShowModalLote(false);
    } catch (error) {
      console.error("Erro ao registrar movimento:", error);
      alert(error.response?.data?.detail || "Erro ao registrar movimento");
    }
  };

  const voltarParaProdutos = () => navigate("/produtos");

  const abrirNovaVariacao = () => {
    navigate(`/produtos/novo?produto_pai_id=${id}`);
  };

  const editarVariacao = (variacaoId) => {
    navigate(`/produtos/${variacaoId}/editar`);
  };

  return {
    id,
    isEdit,
    abaAtiva,
    setAbaAtiva,
    loading,
    salvando,
    categorias,
    marcas,
    departamentos,
    clientes,
    produto,
    setProduto,
    imagens,
    uploadingImage,
    fornecedores,
    showModalFornecedor,
    setShowModalFornecedor,
    fornecedorEdit,
    lotes,
    showModalLote,
    setShowModalLote,
    tipoMovimento,
    variacoes,
    loadingVariacoes,
    handleChange,
    handleGerarCodigo,
    handleSubmit,
    handleUploadImagem,
    handleDeleteImagem,
    handleSetPrincipal,
    handleAddFornecedor,
    handleEditFornecedor,
    handleSaveFornecedor,
    handleDeleteFornecedor,
    handleMovimentoEstoque,
    handleSaveMovimento,
    voltarParaProdutos,
    abrirNovaVariacao,
    editarVariacao,
  };
}
