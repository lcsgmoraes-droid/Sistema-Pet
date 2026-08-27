import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";
import api from "../../api";
import { safeArray } from "../../utils/safeArray";
import {
  criarDadosPadraoContaPagar,
  criarFormCategoriaPadrao,
  filtrarCategoriasDespesa,
  gerarPreviewParcelas,
  montarDadosEdicaoContaPagar,
  montarPayloadContaPagar,
  montarPayloadEdicaoContaPagar,
} from "./contaPagarFormState";

export function useModalNovaContaPagarController({ isOpen, onClose, onSave, contaEdicao }) {
  const isEditando = Boolean(contaEdicao?.id);
  const pertenceRecorrencia = Boolean(
    contaEdicao?.eh_recorrente || contaEdicao?.conta_recorrencia_origem_id,
  );
  const [loading, setLoading] = useState(false);
  const [fornecedores, setFornecedores] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [subcategoriasDRE, setSubcategoriasDRE] = useState([]);
  const [tiposDespesa, setTiposDespesa] = useState([]);
  const [previewParcelas, setPreviewParcelas] = useState([]);
  const [intervaloParcelas, setIntervaloParcelas] = useState(30);
  const [showModalCategoria, setShowModalCategoria] = useState(false);
  const [showModalVinculoDRE, setShowModalVinculoDRE] = useState(false);
  const [vinculoDRESubcategoriaId, setVinculoDRESubcategoriaId] = useState("");
  const [salvandoVinculoDRE, setSalvandoVinculoDRE] = useState(false);
  const [formCategoria, setFormCategoria] = useState(criarFormCategoriaPadrao);
  const [dados, setDados] = useState(criarDadosPadraoContaPagar);

  const fornecedorSelecionado = useMemo(
    () =>
      safeArray(fornecedores).find(
        (fornecedor) => String(fornecedor.id) === String(dados.fornecedor_id),
      ) || null,
    [dados.fornecedor_id, fornecedores],
  );

  const categoriaSelecionada = useMemo(
    () =>
      safeArray(categorias).find(
        (categoria) => String(categoria.id) === String(dados.categoria_id),
      ) || null,
    [categorias, dados.categoria_id],
  );

  const carregarDados = async () => {
    try {
      const [fornecedoresRes, categoriasRes, subcategoriasDRERes, tiposDespesaRes] =
        await Promise.all([
          api.get("/clientes/?tipo_cadastro=fornecedor"),
          api.get("/categorias-financeiras"),
          api.get("/dre/subcategorias"),
          api.get("/cadastros/tipo-despesa/"),
        ]);

      const categoriasDespesa = filtrarCategoriasDespesa(categoriasRes.data);
      setFornecedores(safeArray(fornecedoresRes.data));
      setCategorias(categoriasDespesa);
      setSubcategoriasDRE(safeArray(subcategoriasDRERes.data));
      setTiposDespesa(safeArray(tiposDespesaRes.data));
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
      toast.error("Erro ao carregar formulário");
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    carregarDados();
    setDados(isEditando ? montarDadosEdicaoContaPagar(contaEdicao) : criarDadosPadraoContaPagar());
    setPreviewParcelas([]);
    setShowModalVinculoDRE(false);
    setVinculoDRESubcategoriaId("");
  }, [isOpen, contaEdicao?.id]);

  const resetForm = () => {
    setDados(criarDadosPadraoContaPagar());
  };

  const fecharComReset = () => {
    onClose();
    setShowModalVinculoDRE(false);
    resetForm();
  };

  const abrirModalVinculoDRE = (categoriaId = dados.categoria_id) => {
    const categoria = safeArray(categorias).find(
      (item) => String(item.id) === String(categoriaId),
    );
    if (!categoria) return;

    const nomeCategoria = String(categoria.nome || "").trim().toLocaleLowerCase("pt-BR");
    const subcategoriaSugerida = safeArray(subcategoriasDRE).find(
      (subcategoria) =>
        subcategoria.ativo !== false &&
        String(subcategoria.nome || "").trim().toLocaleLowerCase("pt-BR") === nomeCategoria,
    );

    setVinculoDRESubcategoriaId(
      String(
        categoria.dre_subcategoria_id ||
          (String(dados.categoria_id) === String(categoriaId) && dados.dre_subcategoria_id) ||
          subcategoriaSugerida?.id ||
          "",
      ),
    );
    setShowModalVinculoDRE(true);
  };

  const handleCategoriaChange = (categoriaIdValue) => {
    const categoriaId = categoriaIdValue ? parseInt(categoriaIdValue, 10) : null;
    const categoria = safeArray(categorias).find((item) => item.id === categoriaId) || null;
    const dreSubcategoriaId = categoria?.dre_subcategoria_id || null;

    setDados((dadosAtuais) => ({
      ...dadosAtuais,
      categoria_id: categoriaId,
      dre_subcategoria_id: dreSubcategoriaId,
    }));

    if (categoria && !dreSubcategoriaId) {
      abrirModalVinculoDRE(categoria.id);
    }
  };

  const handleSubmitVinculoDRE = async (event) => {
    event.preventDefault();

    const categoriaId = Number(dados.categoria_id);
    const subcategoriaId = Number(vinculoDRESubcategoriaId);
    if (!categoriaId || !subcategoriaId) {
      toast.error("Selecione uma subcategoria DRE");
      return;
    }

    try {
      setSalvandoVinculoDRE(true);
      await api.put(`/categorias-financeiras/${categoriaId}`, {
        dre_subcategoria_id: subcategoriaId,
      });
      setCategorias((categoriasAtuais) =>
        categoriasAtuais.map((categoria) =>
          Number(categoria.id) === categoriaId
            ? { ...categoria, dre_subcategoria_id: subcategoriaId }
            : categoria,
        ),
      );
      setDados((dadosAtuais) => ({
        ...dadosAtuais,
        dre_subcategoria_id: subcategoriaId,
      }));
      setShowModalVinculoDRE(false);
      toast.success("Categoria vinculada ao DRE!");
    } catch (error) {
      console.error("Erro ao vincular categoria ao DRE:", error);
      toast.error(error.response?.data?.detail || "Erro ao vincular categoria ao DRE");
    } finally {
      setSalvandoVinculoDRE(false);
    }
  };

  const gerarPreview = () => {
    setPreviewParcelas(gerarPreviewParcelas(dados, intervaloParcelas));
  };

  const atualizarDataParcela = (index, novaData) => {
    setPreviewParcelas((parcelasAtuais) =>
      parcelasAtuais.map((parcela, parcelaIndex) =>
        parcelaIndex === index ? { ...parcela, data_vencimento: novaData } : parcela,
      ),
    );
  };

  const atualizarValorParcela = (index, novoValor) => {
    setPreviewParcelas((parcelasAtuais) =>
      parcelasAtuais.map((parcela, parcelaIndex) =>
        parcelaIndex === index ? { ...parcela, valor: parseFloat(novoValor) || 0 } : parcela,
      ),
    );
  };

  const adicionarSubcategoriaNova = () => {
    setFormCategoria((categoriaAtual) => ({
      ...categoriaAtual,
      novasSubcategorias: [
        ...categoriaAtual.novasSubcategorias,
        { nome: "", descricao: "", ativo: true },
      ],
    }));
  };

  const atualizarSubcategoriaNova = (index, field, value) => {
    setFormCategoria((categoriaAtual) => ({
      ...categoriaAtual,
      novasSubcategorias: categoriaAtual.novasSubcategorias.map((subcategoria, subIndex) =>
        subIndex === index ? { ...subcategoria, [field]: value } : subcategoria,
      ),
    }));
  };

  const removerSubcategoriaNova = (index) => {
    setFormCategoria((categoriaAtual) => ({
      ...categoriaAtual,
      novasSubcategorias: categoriaAtual.novasSubcategorias.filter(
        (_, subIndex) => subIndex !== index,
      ),
    }));
  };

  const handleKeyDownSubcategoria = (event, index) => {
    if (
      event.key === "Tab" &&
      !event.shiftKey &&
      index === formCategoria.novasSubcategorias.length - 1
    ) {
      event.preventDefault();
      adicionarSubcategoriaNova();
    }
  };

  const handleSubmitCategoria = async (event) => {
    event.preventDefault();

    if (!formCategoria.nome) {
      toast.error("Preencha o nome da categoria");
      return;
    }

    try {
      const response = await api.post("/categorias-financeiras", {
        nome: formCategoria.nome,
        tipo: formCategoria.tipo,
        cor: formCategoria.cor,
        icone: formCategoria.icone,
        descricao: formCategoria.descricao,
        ativo: formCategoria.ativo,
      });

      const categoriaId = response.data.id;
      toast.success("Categoria criada com sucesso!");

      const subsValidas = formCategoria.novasSubcategorias.filter((sub) => sub.nome.trim());
      for (const sub of subsValidas) {
        try {
          await api.post("/dre/subcategorias", {
            categoria_id: categoriaId,
            nome: sub.nome,
            tipo_custo: "direto",
            escopo_rateio: "ambos",
          });
        } catch (subError) {
          console.error("Erro ao criar subcategoria:", subError);
        }
      }

      if (subsValidas.length > 0) {
        toast.success(`${subsValidas.length} subcategoria(s) criada(s)!`);
      }

      await carregarDados();
      setDados((dadosAtuais) => ({ ...dadosAtuais, categoria_id: categoriaId }));
      setShowModalCategoria(false);
      setFormCategoria(criarFormCategoriaPadrao());
    } catch (error) {
      console.error("Erro ao salvar categoria:", error);
      toast.error(error.response?.data?.detail || "Erro ao salvar categoria");
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!dados.descricao || !dados.valor_original || !dados.data_vencimento) {
      toast.error("Preencha todos os campos obrigatórios");
      return;
    }

    if (categoriaSelecionada && !categoriaSelecionada.dre_subcategoria_id) {
      abrirModalVinculoDRE(categoriaSelecionada.id);
      return;
    }

    setLoading(true);

    try {
      const payloadNormalizado = await montarPayloadContaPagar(
        dados,
        contaEdicao,
        pertenceRecorrencia,
      );

      if (isEditando) {
        await api.patch(
          `/contas-pagar/${contaEdicao.id}`,
          montarPayloadEdicaoContaPagar(payloadNormalizado),
        );
      } else {
        await api.post("/contas-pagar/", payloadNormalizado);
      }

      toast.success(
        isEditando
          ? "Conta atualizada com sucesso!"
          : dados.eh_recorrente
            ? "Conta recorrente criada com sucesso!"
            : "Conta criada com sucesso!",
      );
      onSave();
      onClose();
      resetForm();
    } catch (error) {
      console.error("Erro ao salvar conta:", error);
      toast.error(error.response?.data?.detail || "Erro ao salvar conta a pagar");
    } finally {
      setLoading(false);
    }
  };

  return {
    adicionarSubcategoriaNova,
    atualizarDataParcela,
    atualizarSubcategoriaNova,
    atualizarValorParcela,
    abrirModalVinculoDRE,
    categorias,
    categoriaSelecionada,
    dados,
    fecharComReset,
    formCategoria,
    fornecedorSelecionado,
    fornecedores,
    gerarPreview,
    handleKeyDownSubcategoria,
    handleCategoriaChange,
    handleSubmit,
    handleSubmitCategoria,
    handleSubmitVinculoDRE,
    intervaloParcelas,
    isEditando,
    loading,
    pertenceRecorrencia,
    previewParcelas,
    removerSubcategoriaNova,
    salvandoVinculoDRE,
    setDados,
    setFormCategoria,
    setFornecedores,
    setIntervaloParcelas,
    setPreviewParcelas,
    setShowModalCategoria,
    setShowModalVinculoDRE,
    showModalCategoria,
    showModalVinculoDRE,
    subcategoriasDRE,
    tiposDespesa,
    vinculoDRESubcategoriaId,
    setVinculoDRESubcategoriaId,
  };
}
