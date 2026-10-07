import { useState, useEffect } from "react";
import api from "../api";
import { toast } from "react-hot-toast";
import ModalNovaContaReceberContent from "./contasReceber/ModalNovaContaReceberContent";
import { normalizarListaClientes } from "./contasReceber/contasReceberFilterHelpers";
import { garantirCategoriaDRE } from "../utils/dreCategoriaFinanceira";

const ModalNovaContaReceber = ({ isOpen, onClose, onSave }) => {
  const [loading, setLoading] = useState(false);
  const [clientes, setClientes] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [subcategoriasDRE, setSubcategoriasDRE] = useState([]);
  const [categoriasDRE, setCategoriasDRE] = useState([]);
  const [previewParcelas, setPreviewParcelas] = useState([]);
  const [intervaloParcelas, setIntervaloParcelas] = useState(30);
  const [showModalCategoria, setShowModalCategoria] = useState(false);
  const [formCategoria, setFormCategoria] = useState({
    nome: "",
    tipo: "receita",
    cor: "#10b981",
    icone: "\ud83d\udcb0",
    descricao: "",
    ativo: true,
    novasSubcategorias: [],
  });

  const [dados, setDados] = useState({
    descricao: "",
    cliente_id: null,
    categoria_id: null,
    dre_subcategoria_id: null,
    valor_original: "",
    data_emissao: new Date().toISOString().split("T")[0],
    data_vencimento: new Date().toISOString().split("T")[0],
    documento: "",
    observacoes: "",

    // Parcelamento
    eh_parcelado: false,
    total_parcelas: 1,

    // Recorrência
    eh_recorrente: false,
    tipo_recorrencia: "mensal",
    intervalo_dias: null,
    data_inicio_recorrencia: null,
    data_fim_recorrencia: null,
    numero_repeticoes: null,
  });

  useEffect(() => {
    if (isOpen) {
      carregarDados();
    }
  }, [isOpen]);

  const carregarDados = async () => {
    try {
      const [clientesRes, categoriasRes, subcategoriasDRERes, categoriasDRERes] = await Promise.all([
        api.get("/clientes/?is_cliente=true"),
        api.get("/categorias-financeiras"),
        api.get("/dre/subcategorias"),
        api.get("/dre/categorias"),
      ]);

      console.log("📦 Categorias recebidas:", categoriasRes.data);

      setClientes(normalizarListaClientes(clientesRes.data));

      // Filtrar categorias: Mostrar APENAS receitas/entradas
      const categoriasReceita = categoriasRes.data.filter((c) => {
        const tipo = c.tipo ? c.tipo.toLowerCase() : "";
        const nome = c.nome ? c.nome.toLowerCase() : "";

        // ACEITAR se for receita ou entrada
        const ehReceita = tipo === "receita" || tipo === "entrada";
        const temReceitaNoNome = nome.includes("receita") || nome.includes("venda");

        // BLOQUEAR despesas explícitas
        const ehDespesa = tipo === "despesa" || tipo === "saida" || tipo === "saída";

        return (ehReceita || temReceitaNoNome) && !ehDespesa;
      });

      setCategorias(categoriasReceita);
      setSubcategoriasDRE(subcategoriasDRERes.data || []);
      setCategoriasDRE(categoriasDRERes.data || []);

      console.log("✅ Categorias de RECEITA setadas:", categoriasReceita.length);
      console.log("📋 Lista completa:", categoriasReceita);
      console.log("📊 Subcategorias DRE carregadas:", subcategoriasDRERes.data?.length);
    } catch (error) {
      console.error("❌ Erro ao carregar dados:", error);
      toast.error("Erro ao carregar formulário");
    }
  };

  const gerarPreviewParcelas = () => {
    if (
      !dados.eh_parcelado ||
      !dados.total_parcelas ||
      !dados.data_vencimento ||
      !dados.valor_original
    ) {
      setPreviewParcelas([]);
      return;
    }

    const numParcelas = parseInt(dados.total_parcelas);
    const valorTotal = parseFloat(dados.valor_original);
    const valorParcela = (valorTotal / numParcelas).toFixed(2);
    const dataBase = new Date(dados.data_vencimento);

    const parcelas = [];
    for (let i = 0; i < numParcelas; i++) {
      const dataVencimento = new Date(dataBase);
      dataVencimento.setDate(dataBase.getDate() + i * intervaloParcelas);

      parcelas.push({
        numero: i + 1,
        valor: parseFloat(valorParcela),
        data_vencimento: dataVencimento.toISOString().split("T")[0],
      });
    }

    // Ajustar última parcela
    const somaCalculada = parcelas.reduce((sum, p) => sum + p.valor, 0);
    const diferenca = valorTotal - somaCalculada;
    if (Math.abs(diferenca) > 0.01) {
      parcelas[parcelas.length - 1].valor += diferenca;
    }

    setPreviewParcelas(parcelas);
  };

  const adicionarSubcategoriaNova = () => {
    setFormCategoria((atual) => ({
      ...atual,
      novasSubcategorias: [...atual.novasSubcategorias, { nome: "", descricao: "", ativo: true }],
    }));
  };

  const atualizarSubcategoriaNova = (index, field, value) => {
    setFormCategoria((atual) => ({
      ...atual,
      novasSubcategorias: atual.novasSubcategorias.map((subcategoria, subIndex) =>
        subIndex === index ? { ...subcategoria, [field]: value } : subcategoria,
      ),
    }));
  };

  const removerSubcategoriaNova = (index) => {
    setFormCategoria((atual) => ({
      ...atual,
      novasSubcategorias: atual.novasSubcategorias.filter((_, i) => i !== index),
    }));
  };

  const handleKeyDownSubcategoria = (e, index) => {
    if (e.key === "Tab" && !e.shiftKey && index === formCategoria.novasSubcategorias.length - 1) {
      e.preventDefault();
      adicionarSubcategoriaNova();
    }
  };

  const handleSubmitCategoria = async (e) => {
    e.preventDefault();

    if (!formCategoria.nome) {
      toast.error("Preencha o nome da categoria");
      return;
    }

    let categoriaId;
    try {
      const response = await api.post("/categorias-financeiras", {
        nome: formCategoria.nome,
        tipo: formCategoria.tipo,
        cor: formCategoria.cor,
        icone: formCategoria.icone,
        descricao: formCategoria.descricao,
        ativo: formCategoria.ativo,
      });

      categoriaId = response.data.id;

      // Criar subcategorias se houver
      let primeiraSubDREId = null;
      if (formCategoria.novasSubcategorias.length > 0) {
        const subsValidas = formCategoria.novasSubcategorias.filter((sub) => sub.nome.trim());
        if (subsValidas.length > 0) {
          const categoriaDREId = await garantirCategoriaDRE(api, {
            nome: formCategoria.nome,
            tipo: formCategoria.tipo,
          });
          for (const sub of subsValidas) {
            const subResp = await api.post("/dre/subcategorias", {
              categoria_id: categoriaDREId,
              categoria_financeira_id: categoriaId,
              nome: sub.nome.trim(),
              tipo_custo: "direto",
              escopo_rateio: "ambos",
            });
            primeiraSubDREId ||= subResp.data.id;
          }
          await api.put(`/categorias-financeiras/${categoriaId}`, {
            dre_subcategoria_id: primeiraSubDREId,
          });
        }
      }

      // Atualizar lista de categorias e selecionar a nova
      await carregarDados();
      setDados((atual) => ({
        ...atual,
        categoria_id: categoriaId,
        dre_subcategoria_id: primeiraSubDREId,
      }));
      setShowModalCategoria(false);
      setFormCategoria({
        nome: "",
        tipo: "receita",
        cor: "#10b981",
        icone: "\ud83d\udcb0",
        descricao: "",
        ativo: true,
        novasSubcategorias: [],
      });
      toast.success("Categoria e subcategorias salvas com sucesso!");
    } catch (error) {
      console.error("Erro ao salvar categoria:", error);
      toast.error(
        categoriaId
          ? "Categoria criada, mas houve erro nas subcategorias. Reabra a categoria para concluir."
          : error.response?.data?.detail || "Erro ao salvar categoria",
      );
      if (categoriaId) await carregarDados();
    }
  };

  const atualizarDataParcela = (index, novaData) => {
    const novasParcelas = [...previewParcelas];
    novasParcelas[index].data_vencimento = novaData;
    setPreviewParcelas(novasParcelas);
  };

  const atualizarValorParcela = (index, novoValor) => {
    const novasParcelas = [...previewParcelas];
    novasParcelas[index].valor = parseFloat(novoValor) || 0;
    setPreviewParcelas(novasParcelas);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!dados.descricao || !dados.valor_original || !dados.data_vencimento) {
      toast.error("Preencha todos os campos obrigatórios");
      return;
    }
    if (!subcategoriasReceita.some((sub) => sub.id === dados.dre_subcategoria_id)) {
      toast.error("Selecione uma subcategoria DRE de receita para esta conta");
      return;
    }

    setLoading(true);

    try {
      await api.post("/contas-receber/", {
        ...dados,
        valor_original: parseFloat(dados.valor_original),
        total_parcelas: dados.eh_parcelado ? parseInt(dados.total_parcelas) : 1,
        intervalo_dias:
          dados.tipo_recorrencia === "personalizado" ? parseInt(dados.intervalo_dias) : null,
        numero_repeticoes: dados.numero_repeticoes ? parseInt(dados.numero_repeticoes) : null,
      });

      toast.success(
        dados.eh_recorrente ? "Conta recorrente criada com sucesso!" : "Conta criada com sucesso!",
      );
      onSave();
      onClose();
      resetForm();
    } catch (error) {
      console.error("Erro ao criar conta:", error);
      toast.error(error.response?.data?.detail || "Erro ao criar conta a receber");
    } finally {
      setLoading(false);
    }
  };

  const idsCategoriasReceita = new Set(
    categoriasDRE
      .filter((categoria) => categoria.natureza === "receita")
      .map((categoria) => categoria.id),
  );
  const subcategoriasReceita = subcategoriasDRE.filter(
    (subcategoria) =>
      subcategoria.ativo !== false && idsCategoriasReceita.has(subcategoria.categoria_id),
  );

  const resetForm = () => {
    setDados({
      descricao: "",
      cliente_id: null,
      categoria_id: null,
      dre_subcategoria_id: null,
      valor_original: "",
      data_emissao: new Date().toISOString().split("T")[0],
      data_vencimento: new Date().toISOString().split("T")[0],
      documento: "",
      observacoes: "",
      eh_parcelado: false,
      total_parcelas: 1,
      eh_recorrente: false,
      tipo_recorrencia: "mensal",
      intervalo_dias: null,
      data_inicio_recorrencia: null,
      data_fim_recorrencia: null,
      numero_repeticoes: null,
    });
    setPreviewParcelas([]);
  };

  if (!isOpen) return null;

  return (
    <ModalNovaContaReceberContent
      adicionarSubcategoriaNova={adicionarSubcategoriaNova}
      atualizarDataParcela={atualizarDataParcela}
      atualizarSubcategoriaNova={atualizarSubcategoriaNova}
      atualizarValorParcela={atualizarValorParcela}
      categorias={categorias}
      clientes={clientes}
      dados={dados}
      formCategoria={formCategoria}
      gerarPreviewParcelas={gerarPreviewParcelas}
      handleKeyDownSubcategoria={handleKeyDownSubcategoria}
      handleSubmit={handleSubmit}
      handleSubmitCategoria={handleSubmitCategoria}
      intervaloParcelas={intervaloParcelas}
      loading={loading}
      onClose={onClose}
      previewParcelas={previewParcelas}
      removerSubcategoriaNova={removerSubcategoriaNova}
      resetForm={resetForm}
      setDados={setDados}
      setFormCategoria={setFormCategoria}
      setIntervaloParcelas={setIntervaloParcelas}
      setPreviewParcelas={setPreviewParcelas}
      setShowModalCategoria={setShowModalCategoria}
      showModalCategoria={showModalCategoria}
      subcategoriasDRE={subcategoriasReceita}
    />
  );
};

export default ModalNovaContaReceber;
