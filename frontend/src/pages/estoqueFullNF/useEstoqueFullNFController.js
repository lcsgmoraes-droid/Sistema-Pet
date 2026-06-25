import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import {
  criarLinha,
  ehErroEstoqueFull,
  extrairDetalheErro,
  formatarQuantidade,
  normalizarSku,
  toNumber,
} from "./estoqueFullNFUtils";

export function useEstoqueFullNFController() {
  const [numeroNF, setNumeroNF] = useState("");
  const [plataforma, setPlataforma] = useState("");
  const [observacao, setObservacao] = useState("");
  const [itens, setItens] = useState([criarLinha()]);

  const [tarifaEnvio, setTarifaEnvio] = useState(0);
  const [dataVencimentoTarifa, setDataVencimentoTarifa] = useState("");
  const [categoriaTarifaId, setCategoriaTarifaId] = useState("");
  const [categoriasDespesa, setCategoriasDespesa] = useState([]);

  const [abaAtiva, setAbaAtiva] = useState("lancamento");
  const [modalConclusao, setModalConclusao] = useState({ aberto: false, resultado: null });
  const [modalEditarCanal, setModalEditarCanal] = useState({
    aberto: false,
    lancamento: null,
    canal: "",
  });
  const [processamentoPendente, setProcessamentoPendente] = useState({});
  const [historico, setHistorico] = useState([]);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [salvandoCanal, setSalvandoCanal] = useState(false);
  const [arquivoXml, setArquivoXml] = useState(null);
  const [xmlInputKey, setXmlInputKey] = useState(0);
  const [lendoXml, setLendoXml] = useState(false);
  const [modalDre, setModalDre] = useState({ aberto: false, categoria: null });
  const [dreSubcategoriasDespesa, setDreSubcategoriasDespesa] = useState([]);
  const [dreSubcategoriaId, setDreSubcategoriaId] = useState("");
  const [carregandoDre, setCarregandoDre] = useState(false);
  const [salvandoVinculoDre, setSalvandoVinculoDre] = useState(false);
  const [alertaEstoque, setAlertaEstoque] = useState(null);
  const [validandoEstoque, setValidandoEstoque] = useState(false);

  const hojeISO = useMemo(() => new Date().toISOString().slice(0, 10), []);

  useEffect(() => {
    setDataVencimentoTarifa(hojeISO);
  }, [hojeISO]);

  useEffect(() => {
    const carregarCategorias = async () => {
      try {
        const response = await api.get("/categorias-financeiras?tipo=despesa");
        setCategoriasDespesa(Array.isArray(response.data) ? response.data : []);
      } catch (error) {
        console.error("Erro ao carregar categorias de despesa:", error);
      }
    };

    carregarCategorias();
  }, []);

  const carregarHistorico = async () => {
    try {
      setCarregandoHistorico(true);
      const response = await api.get("/estoque/saida-full-nf/historico?limit=200");
      setHistorico(Array.isArray(response.data?.items) ? response.data.items : []);
    } catch (error) {
      console.error("Erro ao carregar historico FULL por NF:", error);
      toast.error("Nao foi possivel carregar o historico de baixas FULL.");
    } finally {
      setCarregandoHistorico(false);
    }
  };

  useEffect(() => {
    carregarHistorico();
  }, []);

  const categoriaTarifaSelecionada = useMemo(
    () => categoriasDespesa.find((cat) => String(cat.id) === String(categoriaTarifaId)),
    [categoriasDespesa, categoriaTarifaId],
  );

  const problemasEstoque = useMemo(
    () => (Array.isArray(alertaEstoque?.itens) ? alertaEstoque.itens : []),
    [alertaEstoque],
  );

  const problemasEstoquePorSku = useMemo(() => {
    const mapa = new Map();
    problemasEstoque.forEach((problema) => {
      const skuEntrada = normalizarSku(problema.entrada_sku || problema.sku);
      if (skuEntrada && !mapa.has(skuEntrada)) {
        mapa.set(skuEntrada, problema);
      }
    });
    return mapa;
  }, [problemasEstoque]);

  const podeLancarNegativo = useMemo(
    () =>
      problemasEstoque.length > 0 &&
      problemasEstoque.every((problema) => problema.tipo !== "produto_nao_encontrado"),
    [problemasEstoque],
  );

  const problemaDaLinha = (item) => problemasEstoquePorSku.get(normalizarSku(item.sku));

  const carregarSubcategoriasDespesaDre = async () => {
    if (dreSubcategoriasDespesa.length) return;

    try {
      setCarregandoDre(true);
      const [categoriasResponse, subcategoriasResponse] = await Promise.all([
        api.get("/dre/categorias"),
        api.get("/dre/subcategorias"),
      ]);

      const categoriasDre = Array.isArray(categoriasResponse.data) ? categoriasResponse.data : [];
      const subcategoriasDre = Array.isArray(subcategoriasResponse.data)
        ? subcategoriasResponse.data
        : [];
      const categoriasDespesaMap = new Map(
        categoriasDre
          .filter(
            (cat) => cat.ativo !== false && String(cat.natureza || "").toLowerCase() === "despesa",
          )
          .map((cat) => [Number(cat.id), cat]),
      );

      const opcoes = subcategoriasDre
        .filter((sub) => sub.ativo !== false && categoriasDespesaMap.has(Number(sub.categoria_id)))
        .map((sub) => ({
          ...sub,
          categoria_nome: categoriasDespesaMap.get(Number(sub.categoria_id))?.nome || "Despesa",
        }))
        .sort((a, b) =>
          `${a.categoria_nome} ${a.nome}`.localeCompare(`${b.categoria_nome} ${b.nome}`, "pt-BR"),
        );

      setDreSubcategoriasDespesa(opcoes);
    } catch (error) {
      console.error("Erro ao carregar DRE de despesa:", error);
      toast.error("Nao foi possivel carregar as subcategorias DRE de despesa.");
    } finally {
      setCarregandoDre(false);
    }
  };

  const abrirModalVinculoDre = (categoria, opcoesProcessamento = {}) => {
    setProcessamentoPendente(opcoesProcessamento);
    setModalDre({ aberto: true, categoria });
    setDreSubcategoriaId("");
    carregarSubcategoriasDespesaDre();
  };

  const atualizarLinha = (linhaId, campo, valor) => {
    setAlertaEstoque(null);
    setItens((prev) =>
      prev.map((item) => (item.id === linhaId ? { ...item, [campo]: valor } : item)),
    );
  };

  const adicionarLinha = () => {
    setAlertaEstoque(null);
    setItens((prev) => [...prev, criarLinha()]);
  };

  const removerLinha = (linhaId) => {
    setAlertaEstoque(null);
    setItens((prev) => (prev.length > 1 ? prev.filter((item) => item.id !== linhaId) : prev));
  };

  const limparFormulario = () => {
    setAlertaEstoque(null);
    setNumeroNF("");
    setPlataforma("");
    setItens([criarLinha()]);
    setObservacao("");
    setArquivoXml(null);
    setXmlInputKey((prev) => prev + 1);
    setTarifaEnvio(0);
    setDataVencimentoTarifa(hojeISO);
    setCategoriaTarifaId("");
  };

  const importarItensDoXml = async () => {
    if (!arquivoXml) {
      toast.error("Selecione um arquivo XML primeiro");
      return;
    }

    try {
      setLendoXml(true);
      const formData = new FormData();
      formData.append("file", arquivoXml);

      const response = await api.post("/estoque/saida-full-xml/parse", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const numeroNfXml = (response?.data?.numero_nf || "").toString().trim();
      const itensXml = Array.isArray(response?.data?.itens) ? response.data.itens : [];

      if (!numeroNfXml) {
        toast.error("Nao foi possivel identificar o numero da NF no XML");
        return;
      }

      if (!itensXml.length) {
        toast.error("Nenhum item foi identificado no XML");
        return;
      }

      const linhas = itensXml.map((item) => ({
        ...criarLinha(),
        sku: item.sku || "",
        quantidade: item.quantidade || "",
      }));

      setNumeroNF(numeroNfXml);
      setItens(linhas);
      setAlertaEstoque(null);
      toast.success(`XML lido com sucesso: NF ${numeroNfXml} com ${linhas.length} item(ns)`);
    } catch (error) {
      console.error("Erro ao ler XML FULL NF:", error);
      const detalhe = error?.response?.data?.detail || "Erro ao ler XML";
      toast.error(detalhe);
    } finally {
      setLendoXml(false);
    }
  };

  const validarTarifaEnvio = (
    categoriaClassificada = categoriaTarifaSelecionada,
    opcoesProcessamento = {},
  ) => {
    if (!tarifaEnvio || tarifaEnvio <= 0) return true;

    if (!categoriaTarifaId) {
      toast.error("Selecione uma categoria de despesa vinculada a DRE para lancar a tarifa.");
      return false;
    }

    if (!categoriaClassificada?.dre_subcategoria_id) {
      abrirModalVinculoDre(categoriaClassificada, opcoesProcessamento);
      return false;
    }

    return true;
  };

  const obterItensValidos = () =>
    itens
      .map((item) => ({
        sku: item.sku.trim(),
        quantidade: toNumber(item.quantidade),
      }))
      .filter((item) => item.sku && item.quantidade > 0);

  const abrirCorrecaoEstoque = (problema) => {
    if (!problema?.url_correcao) return;
    window.open(problema.url_correcao, "_blank", "noopener,noreferrer");
  };

  const revalidarEstoque = async () => {
    const itensValidos = obterItensValidos();
    if (!itensValidos.length) {
      toast.error("Informe ao menos um item com SKU e quantidade");
      return;
    }

    try {
      setValidandoEstoque(true);
      const payload = {
        numero_nf: numeroNF.trim() || "validacao",
        plataforma: plataforma || "full",
        observacao: observacao.trim() || null,
        itens: itensValidos,
      };
      const response = await api.post("/estoque/saida-full-nf/validar-estoque", payload);
      const problemas = Array.isArray(response.data?.problemas) ? response.data.problemas : [];
      if (problemas.length) {
        const detalhe = {
          code: "estoque_insuficiente_full_nf",
          message: "Ainda existem itens sem estoque suficiente.",
          itens: problemas,
        };
        setAlertaEstoque(detalhe);
        toast.error("Ainda existe produto sem estoque suficiente.");
        return;
      }

      setAlertaEstoque(null);
      toast.success("Estoque revalidado. Pode confirmar a baixa.");
    } catch (error) {
      console.error("Erro ao revalidar estoque FULL por NF:", error);
      const detalhe = extrairDetalheErro(error);
      if (ehErroEstoqueFull(detalhe)) {
        setAlertaEstoque(detalhe);
        toast.error(detalhe.message || "Ainda existe produto sem estoque suficiente.");
        return;
      }
      toast.error(typeof detalhe === "string" ? detalhe : "Nao foi possivel revalidar o estoque.");
    } finally {
      setValidandoEstoque(false);
    }
  };

  const processar = async (categoriaClassificada = categoriaTarifaSelecionada, opcoes = {}) => {
    if (!numeroNF.trim()) {
      toast.error("Informe o numero da NF");
      return;
    }

    if (!plataforma) {
      toast.error("Selecione o canal/origem da movimentacao.");
      return;
    }

    const itensValidos = obterItensValidos();

    if (!itensValidos.length) {
      toast.error("Informe ao menos um item com SKU e quantidade");
      return;
    }

    if (!validarTarifaEnvio(categoriaClassificada, opcoes)) {
      return;
    }

    try {
      setSalvando(true);
      setAbaAtiva("lancamento");

      const payload = {
        numero_nf: numeroNF.trim(),
        plataforma,
        observacao: observacao.trim() || null,
        itens: itensValidos,
      };

      if (opcoes.permitirEstoqueNegativo) {
        payload.permitir_estoque_negativo = true;
      }

      if (tarifaEnvio > 0) {
        payload.tarifa_envio = Number(tarifaEnvio);
        payload.categoria_tarifa_id = Number(categoriaTarifaId);
        payload.dre_subcategoria_tarifa_id = Number(categoriaClassificada.dre_subcategoria_id);
        payload.data_vencimento_tarifa = dataVencimentoTarifa || hojeISO;
      }

      const response = await api.post("/estoque/saida-full-nf", payload);
      const resultadoProcessado = response.data;
      setAlertaEstoque(null);
      setModalConclusao({ aberto: true, resultado: resultadoProcessado });
      carregarHistorico();
      limparFormulario();
    } catch (error) {
      console.error("Erro ao processar FULL por NF:", error);
      const detalhe = extrairDetalheErro(error);
      if (ehErroEstoqueFull(detalhe)) {
        setAlertaEstoque(detalhe);
        toast.error(detalhe.message || "Corrija os produtos marcados e tente novamente.");
        return;
      }
      toast.error(typeof detalhe === "string" ? detalhe : "Erro ao processar baixa por NF");
    } finally {
      setSalvando(false);
    }
  };

  const lancarNegativo = async () => {
    if (!podeLancarNegativo) {
      toast.error("Nao e possivel lancar negativo quando existe produto nao encontrado.");
      return;
    }

    const totalFaltante = problemasEstoque.reduce(
      (soma, problema) => soma + Number(problema.faltante || 0),
      0,
    );
    const confirmou = confirm(
      `Lancar a NF mesmo deixando estoque negativo?\n\nItens com falta: ${problemasEstoque.length}\nTotal faltante: ${formatarQuantidade(totalFaltante)}\n\nUse esta opcao apenas para nao travar o fluxo agora. Depois ajuste o estoque dos produtos.`,
    );
    if (!confirmou) return;

    await processar(categoriaTarifaSelecionada, { permitirEstoqueNegativo: true });
  };

  const fecharModalDre = () => {
    if (salvandoVinculoDre) return;
    setProcessamentoPendente({});
    setModalDre({ aberto: false, categoria: null });
    setDreSubcategoriaId("");
  };

  const fecharModalConclusao = (verResumo = false) => {
    setModalConclusao({ aberto: false, resultado: null });
    setAbaAtiva(verResumo ? "historico" : "lancamento");
  };

  const abrirModalEditarCanal = (lancamento) => {
    if (!lancamento?.numero_nf) {
      toast.error("Nao foi possivel identificar a NF para corrigir o canal.");
      return;
    }
    setModalEditarCanal({
      aberto: true,
      lancamento,
      canal: lancamento.plataforma || "",
    });
  };

  const fecharModalEditarCanal = () => {
    if (salvandoCanal) return;
    setModalEditarCanal({ aberto: false, lancamento: null, canal: "" });
  };

  const corrigirCanalDoResultado = () => {
    const resultado = modalConclusao.resultado;
    if (!resultado) return;
    setModalConclusao({ aberto: false, resultado: null });
    setAbaAtiva("historico");
    abrirModalEditarCanal(resultado);
  };

  const salvarCanalLancamento = async () => {
    const lancamento = modalEditarCanal.lancamento;
    const canal = modalEditarCanal.canal;
    if (!lancamento?.numero_nf) {
      toast.error("Nao foi possivel identificar a NF para corrigir o canal.");
      return;
    }
    if (!canal) {
      toast.error("Selecione o canal correto.");
      return;
    }

    try {
      setSalvandoCanal(true);
      const response = await api.put(
        `/estoque/saida-full-nf/${encodeURIComponent(lancamento.numero_nf)}/canal`,
        { plataforma: canal },
      );
      toast.success(response.data?.message || "Canal atualizado.");
      setModalEditarCanal({ aberto: false, lancamento: null, canal: "" });
      await carregarHistorico();
      setAbaAtiva("historico");
    } catch (error) {
      console.error("Erro ao atualizar canal da baixa FULL:", error);
      const detalhe = error?.response?.data?.detail || "Nao foi possivel atualizar o canal.";
      toast.error(typeof detalhe === "string" ? detalhe : "Nao foi possivel atualizar o canal.");
    } finally {
      setSalvandoCanal(false);
    }
  };

  const vincularDreEContinuar = async () => {
    const categoria = modalDre.categoria;
    if (!categoria) return;
    if (!dreSubcategoriaId) {
      toast.error("Selecione a subcategoria DRE para vincular.");
      return;
    }

    try {
      setSalvandoVinculoDre(true);
      const response = await api.put(`/categorias-financeiras/${categoria.id}`, {
        dre_subcategoria_id: Number(dreSubcategoriaId),
      });
      const categoriaAtualizada = response.data;

      setCategoriasDespesa((prev) =>
        prev.map((cat) =>
          String(cat.id) === String(categoriaAtualizada.id) ? categoriaAtualizada : cat,
        ),
      );
      setCategoriaTarifaId(String(categoriaAtualizada.id));
      setModalDre({ aberto: false, categoria: null });
      setDreSubcategoriaId("");
      const opcoesProcessamento = processamentoPendente || {};
      setProcessamentoPendente({});
      toast.success("Categoria vinculada a DRE. Continuando a operacao...");
      await processar(categoriaAtualizada, opcoesProcessamento);
    } catch (error) {
      console.error("Erro ao vincular categoria a DRE:", error);
      const detalhe =
        error?.response?.data?.detail || "Nao foi possivel vincular a categoria a DRE.";
      toast.error(detalhe);
    } finally {
      setSalvandoVinculoDre(false);
    }
  };

  return {
    numeroNF,
    setNumeroNF,
    plataforma,
    setPlataforma,
    observacao,
    setObservacao,
    itens,
    setItens,
    tarifaEnvio,
    setTarifaEnvio,
    dataVencimentoTarifa,
    setDataVencimentoTarifa,
    categoriaTarifaId,
    setCategoriaTarifaId,
    categoriasDespesa,
    setCategoriasDespesa,
    abaAtiva,
    setAbaAtiva,
    modalConclusao,
    setModalConclusao,
    modalEditarCanal,
    setModalEditarCanal,
    processamentoPendente,
    setProcessamentoPendente,
    historico,
    setHistorico,
    carregandoHistorico,
    setCarregandoHistorico,
    salvando,
    setSalvando,
    salvandoCanal,
    setSalvandoCanal,
    arquivoXml,
    setArquivoXml,
    xmlInputKey,
    setXmlInputKey,
    lendoXml,
    setLendoXml,
    modalDre,
    setModalDre,
    dreSubcategoriasDespesa,
    setDreSubcategoriasDespesa,
    dreSubcategoriaId,
    setDreSubcategoriaId,
    carregandoDre,
    setCarregandoDre,
    salvandoVinculoDre,
    setSalvandoVinculoDre,
    alertaEstoque,
    setAlertaEstoque,
    validandoEstoque,
    setValidandoEstoque,
    hojeISO,
    categoriaTarifaSelecionada,
    problemasEstoque,
    problemasEstoquePorSku,
    podeLancarNegativo,
    problemaDaLinha,
    carregarSubcategoriasDespesaDre,
    abrirModalVinculoDre,
    atualizarLinha,
    adicionarLinha,
    removerLinha,
    limparFormulario,
    importarItensDoXml,
    validarTarifaEnvio,
    obterItensValidos,
    abrirCorrecaoEstoque,
    revalidarEstoque,
    processar,
    lancarNegativo,
    fecharModalDre,
    fecharModalConclusao,
    abrirModalEditarCanal,
    fecharModalEditarCanal,
    corrigirCanalDoResultado,
    salvarCanalLancamento,
    vincularDreEContinuar,
    carregarHistorico,
  };
}
