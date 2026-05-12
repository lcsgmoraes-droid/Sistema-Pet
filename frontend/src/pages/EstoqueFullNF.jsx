import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import CurrencyInput from "../components/CurrencyInput";
import { formatMoneyBRL } from "../utils/formatters";

let linhaSeq = 1;

function criarLinha() {
  return { id: `linha-${linhaSeq++}`, sku: "", quantidade: "" };
}

function toNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

const CANAIS_FULL = [
  {
    value: "amazon",
    label: "Amazon",
    badgeClass: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  {
    value: "mercado_livre",
    label: "Mercado Livre",
    badgeClass: "border-yellow-200 bg-yellow-50 text-yellow-800",
  },
  {
    value: "shopee",
    label: "Shopee",
    badgeClass: "border-orange-200 bg-orange-50 text-orange-700",
  },
  {
    value: "full",
    label: "FULL (geral)",
    badgeClass: "border-slate-200 bg-slate-50 text-slate-700",
  },
];

const CANAIS_FULL_MAP = Object.fromEntries(CANAIS_FULL.map((canal) => [canal.value, canal]));

function obterCanalConfig(canal, fallbackLabel) {
  return CANAIS_FULL_MAP[canal] || {
    value: canal || "",
    label: fallbackLabel || canal || "Canal nao informado",
    badgeClass: "border-slate-200 bg-slate-50 text-slate-700",
  };
}

function CanalBadge({ canal, label }) {
  const config = obterCanalConfig(canal, label);
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${config.badgeClass}`}>
      {config.label}
    </span>
  );
}

function contarBaixas(resultado) {
  if (!resultado) return 0;
  if (resultado.baixas_estoque !== undefined && resultado.baixas_estoque !== null) {
    return Number(resultado.baixas_estoque) || 0;
  }
  return resultado.estoque_ja_baixado ? 0 : Number(resultado.total_itens || 0);
}

function contarLancamentosFinanceiros(resultado) {
  if (!resultado) return 0;
  if (resultado.lancamentos_financeiros !== undefined && resultado.lancamentos_financeiros !== null) {
    return Number(resultado.lancamentos_financeiros) || 0;
  }
  return resultado?.tarifa_envio?.conta_pagar_id ? 1 : 0;
}

function formatarDataHora(valor) {
  if (!valor) return "-";
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return "-";
  return data.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function normalizarSku(valor) {
  return String(valor || "").trim().toLowerCase();
}

function formatarQuantidade(valor) {
  const numero = Number(valor || 0);
  if (!Number.isFinite(numero)) return "0";
  return numero.toLocaleString("pt-BR", { maximumFractionDigits: 3 });
}

function extrairDetalheErro(error) {
  return error?.response?.data?.detail || error?.message || "Erro ao processar baixa por NF";
}

function ehErroEstoqueFull(detalhe) {
  return Boolean(
    detalhe &&
      typeof detalhe === "object" &&
      detalhe.code === "estoque_insuficiente_full_nf" &&
      Array.isArray(detalhe.itens),
  );
}

export default function EstoqueFullNF() {
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
  const [modalEditarCanal, setModalEditarCanal] = useState({ aberto: false, lancamento: null, canal: "" });
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
      const subcategoriasDre = Array.isArray(subcategoriasResponse.data) ? subcategoriasResponse.data : [];
      const categoriasDespesaMap = new Map(
        categoriasDre
          .filter((cat) => cat.ativo !== false && String(cat.natureza || "").toLowerCase() === "despesa")
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

  const abrirModalVinculoDre = (categoria) => {
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
        id: `linha-${linhaSeq++}`,
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

  const validarTarifaEnvio = (categoriaClassificada = categoriaTarifaSelecionada) => {
    if (!tarifaEnvio || tarifaEnvio <= 0) return true;

    if (!categoriaTarifaId) {
      toast.error("Selecione uma categoria de despesa vinculada a DRE para lancar a tarifa.");
      return false;
    }

    if (!categoriaClassificada?.dre_subcategoria_id) {
      abrirModalVinculoDre(categoriaClassificada);
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

  const processar = async (categoriaClassificada = categoriaTarifaSelecionada) => {
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

    if (!validarTarifaEnvio(categoriaClassificada)) {
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

  const fecharModalDre = () => {
    if (salvandoVinculoDre) return;
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
        prev.map((cat) => (String(cat.id) === String(categoriaAtualizada.id) ? categoriaAtualizada : cat)),
      );
      setCategoriaTarifaId(String(categoriaAtualizada.id));
      setModalDre({ aberto: false, categoria: null });
      setDreSubcategoriaId("");
      toast.success("Categoria vinculada a DRE. Continuando a operacao...");
      await processar(categoriaAtualizada);
    } catch (error) {
      console.error("Erro ao vincular categoria a DRE:", error);
      const detalhe = error?.response?.data?.detail || "Nao foi possivel vincular a categoria a DRE.";
      toast.error(detalhe);
    } finally {
      setSalvandoVinculoDre(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Movimentacao Full por NF</h1>
        <p className="text-gray-600 mt-1">
          Esta tela baixa estoque por NF e, opcionalmente, gera somente a tarifa de envio no financeiro.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-slate-200">
        <button
          type="button"
          onClick={() => setAbaAtiva("lancamento")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 ${
            abaAtiva === "lancamento"
              ? "border-blue-600 text-blue-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          Novo lancamento
        </button>
        <button
          type="button"
          onClick={() => setAbaAtiva("historico")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 ${
            abaAtiva === "historico"
              ? "border-blue-600 text-blue-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          Historico de baixas {historico.length ? `(${historico.length})` : ""}
        </button>
      </div>

      {abaAtiva === "lancamento" && (
        <>
      <div className="bg-white rounded-xl border border-gray-200 p-4 md:p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className="block text-sm font-medium text-gray-700 mb-1">Numero da NF (automatico via XML)</div>
            <input
              id="numero-nf"
              aria-label="Numero da NF"
              type="text"
              value={numeroNF}
              readOnly
              placeholder="Selecione um XML para preencher"
              className="w-full border border-amber-300 bg-amber-50 rounded-lg px-3 py-2 text-gray-900"
            />
          </div>

          <div>
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="block text-sm font-medium text-gray-700">Canal / origem *</div>
              {plataforma && <CanalBadge canal={plataforma} />}
            </div>
            <select
              id="plataforma-full"
              aria-label="Canal ou origem"
              value={plataforma}
              onChange={(e) => setPlataforma(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="">Selecione o canal</option>
              {CANAIS_FULL.map((canal) => (
                <option key={canal.value} value={canal.value}>
                  {canal.label}
                </option>
              ))}
            </select>
            {!plataforma && (
              <p className="mt-1 text-xs text-amber-700">Obrigatorio para direcionar a despesa na DRE correta.</p>
            )}
          </div>

          <div>
            <div className="block text-sm font-medium text-gray-700 mb-1">Data vencimento tarifa</div>
            <input
              id="vencimento-tarifa"
              aria-label="Data vencimento tarifa"
              type="date"
              value={dataVencimentoTarifa}
              onChange={(e) => setDataVencimentoTarifa(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            />
          </div>
        </div>

        <div>
          <div className="block text-sm font-medium text-gray-700 mb-1">Observacao (opcional)</div>
          <input
            id="obs-full"
            aria-label="Observacao"
            type="text"
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
            placeholder="Ex: lote de pedidos da semana"
            className="w-full border border-gray-300 rounded-lg px-3 py-2"
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4 md:p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Itens da NF (baixa de estoque)</h2>
          <button
            type="button"
            onClick={adicionarLinha}
            className="px-3 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700"
          >
            + Adicionar item
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end bg-slate-50 border border-slate-200 rounded-xl p-3 md:p-4">
          <div className="md:col-span-8">
            <div className="block text-sm font-medium text-slate-700 mb-1">Escolher XML da NF (preenche numero e itens)</div>
            <input
              key={xmlInputKey}
              type="file"
              accept=".xml,text/xml,application/xml"
              onChange={(e) => setArquivoXml(e.target.files?.[0] || null)}
              className="w-full border border-slate-300 bg-white rounded-lg px-3 py-2"
            />
          </div>
          <div className="md:col-span-4">
            <button
              type="button"
              onClick={importarItensDoXml}
              disabled={lendoXml}
              className="w-full px-3 py-2 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {lendoXml ? "Lendo XML..." : "Ler XML e preencher"}
            </button>
          </div>
        </div>

        {problemasEstoque.length > 0 && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h3 className="font-semibold">Estoque insuficiente em {problemasEstoque.length} item(ns)</h3>
                <p className="mt-1 text-red-800">
                  Corrija o estoque dos produtos marcados em uma nova aba e depois revalide sem perder esta NF.
                </p>
              </div>
              <button
                type="button"
                onClick={revalidarEstoque}
                disabled={validandoEstoque}
                className="rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-100 disabled:opacity-60"
              >
                {validandoEstoque ? "Revalidando..." : "Revalidar estoque"}
              </button>
            </div>
            <div className="mt-3 grid gap-2">
              {problemasEstoque.map((problema) => (
                <div
                  key={`${problema.entrada_sku || problema.sku}-${problema.produto_id || "sem-produto"}`}
                  className="flex flex-col gap-2 rounded-lg border border-red-200 bg-white px-3 py-2 md:flex-row md:items-center md:justify-between"
                >
                  <div>
                    <p className="font-semibold">{problema.nome || "Produto nao identificado"}</p>
                    <p className="text-xs text-red-700">
                      SKU {problema.sku || problema.entrada_sku || "-"} | Disponivel: {formatarQuantidade(problema.disponivel)} | NF pede:{" "}
                      {formatarQuantidade(problema.solicitado)} | Falta: {formatarQuantidade(problema.faltante)}
                    </p>
                  </div>
                  {problema.url_correcao && (
                    <button
                      type="button"
                      onClick={() => abrirCorrecaoEstoque(problema)}
                      className="rounded-lg bg-red-600 px-3 py-2 text-xs font-semibold text-white hover:bg-red-700"
                    >
                      Corrigir estoque
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-2">
          {itens.map((item) => {
            const problema = problemaDaLinha(item);
            return (
              <div
                key={item.id}
                className={`grid grid-cols-1 gap-2 rounded-xl md:grid-cols-12 ${
                  problema ? "border border-red-300 bg-red-50 p-2" : ""
                }`}
              >
                <div className="md:col-span-7">
                  <input
                    id={`sku-${item.id}`}
                    aria-label={`SKU ${item.id}`}
                    type="text"
                    value={item.sku}
                    onChange={(e) => atualizarLinha(item.id, "sku", e.target.value)}
                    placeholder="SKU do produto"
                    className={`w-full rounded-lg border px-3 py-2 ${
                      problema ? "border-red-300 bg-white text-red-900" : "border-gray-300"
                    }`}
                  />
                </div>
                <div className="md:col-span-3">
                  <input
                    id={`qtd-${item.id}`}
                    aria-label={`Quantidade ${item.id}`}
                    type="number"
                    min="0"
                    step="0.01"
                    value={item.quantidade}
                    onChange={(e) => atualizarLinha(item.id, "quantidade", e.target.value)}
                    placeholder="Quantidade"
                    className={`w-full rounded-lg border px-3 py-2 ${
                      problema ? "border-red-300 bg-white text-red-900" : "border-gray-300"
                    }`}
                  />
                </div>
                <div className="md:col-span-2">
                  <button
                    type="button"
                    onClick={() => removerLinha(item.id)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white hover:bg-gray-50"
                  >
                    Remover
                  </button>
                </div>
                {problema && (
                  <div className="md:col-span-12 flex flex-col gap-2 rounded-lg border border-red-200 bg-white px-3 py-2 text-xs text-red-800 md:flex-row md:items-center md:justify-between">
                    <span>
                      {problema.nome}: disponivel {formatarQuantidade(problema.disponivel)}, solicitado{" "}
                      {formatarQuantidade(problema.solicitado)}, falta {formatarQuantidade(problema.faltante)}.
                    </span>
                    {problema.url_correcao && (
                      <button
                        type="button"
                        onClick={() => abrirCorrecaoEstoque(problema)}
                        className="rounded-md border border-red-300 px-2 py-1 font-semibold text-red-700 hover:bg-red-50"
                      >
                        Abrir ajuste de estoque
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4 md:p-5 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Tarifa de envio (financeiro)</h2>
        <p className="text-sm text-gray-600">
          Se preencher esta parte, o sistema cria uma conta a pagar so da tarifa de envio. Se deixar zero, nao cria nada no financeiro.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="block text-sm font-medium text-gray-700 mb-1">Valor da tarifa</div>
            <CurrencyInput
              id="valor-tarifa"
              aria-label="Valor da tarifa"
              value={tarifaEnvio}
              onChange={setTarifaEnvio}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
              placeholder="0,00"
            />
          </div>

          <div>
            <div className="block text-sm font-medium text-gray-700 mb-1">
              Categoria de despesa {tarifaEnvio > 0 ? "(obrigatoria)" : "(opcional)"}
            </div>
            <select
              id="categoria-tarifa"
              aria-label="Categoria da tarifa"
              value={categoriaTarifaId}
              onChange={(e) => setCategoriaTarifaId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="">Sem categoria</option>
              {categoriasDespesa.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.caminho_completo || cat.nome}
                </option>
              ))}
            </select>
            {tarifaEnvio > 0 && !categoriaTarifaId && (
              <p className="mt-1 text-xs text-amber-700">
                Para gerar o contas a pagar da tarifa, selecione uma categoria com DRE vinculada.
              </p>
            )}
            {tarifaEnvio > 0 && categoriaTarifaId && !categoriaTarifaSelecionada?.dre_subcategoria_id && (
              <p className="mt-1 text-xs text-red-700">
                Esta categoria ainda nao tem vinculo DRE. Ajuste o cadastro da categoria antes de confirmar.
              </p>
            )}
            {tarifaEnvio > 0 && categoriaTarifaSelecionada?.dre_subcategoria_id && (
              <p className="mt-1 text-xs text-emerald-700">
                A despesa sera lancada na DRE do canal/origem selecionado.
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => processar()}
          disabled={salvando}
          className="px-5 py-2.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60"
        >
          {salvando ? "Processando..." : "Confirmar baixa por NF"}
        </button>
      </div>
        </>
      )}

      {abaAtiva === "historico" && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 md:p-5 space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Historico de baixas FULL</h3>
              <p className="text-sm text-gray-600 mt-1">
                Lancamentos processados por NF, com canal, estoque e tarifa financeira quando houver.
              </p>
            </div>
            <button
              type="button"
              onClick={carregarHistorico}
              disabled={carregandoHistorico}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-60"
            >
              {carregandoHistorico ? "Atualizando..." : "Atualizar historico"}
            </button>
          </div>

          {!carregandoHistorico && !historico.length && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-10 text-center text-sm text-slate-600">
              Nenhuma baixa FULL por NF encontrada ainda.
            </div>
          )}

          <div className="space-y-3">
            {historico.map((lancamento) => (
              <div key={lancamento.numero_nf} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="text-base font-semibold text-slate-900">NF {lancamento.numero_nf}</h4>
                      <CanalBadge canal={lancamento.plataforma} label={lancamento.plataforma_label} />
                      <button
                        type="button"
                        onClick={() => abrirModalEditarCanal(lancamento)}
                        className="rounded-full border border-slate-300 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        Editar canal
                      </button>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">Processado em {formatarDataHora(lancamento.processado_em)}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                    <div className="rounded-lg bg-emerald-50 px-3 py-2">
                      <p className="text-xs text-emerald-700">Baixas</p>
                      <p className="font-semibold text-emerald-900">{contarBaixas(lancamento)}</p>
                    </div>
                    <div className="rounded-lg bg-blue-50 px-3 py-2">
                      <p className="text-xs text-blue-700">Financeiro</p>
                      <p className="font-semibold text-blue-900">{contarLancamentosFinanceiros(lancamento)}</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 px-3 py-2">
                      <p className="text-xs text-slate-600">Itens</p>
                      <p className="font-semibold text-slate-900">{lancamento.total_itens || 0}</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 px-3 py-2">
                      <p className="text-xs text-slate-600">Tarifa</p>
                      <p className="font-semibold text-slate-900">
                        {lancamento.tarifa_envio ? formatMoneyBRL(lancamento.tarifa_envio.valor) : "-"}
                      </p>
                    </div>
                  </div>
                </div>

                <details className="mt-3">
                  <summary className="cursor-pointer text-sm font-medium text-blue-700">Ver itens da baixa</summary>
                  <div className="mt-3 overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-left text-slate-600">
                          <th className="py-2">SKU</th>
                          <th className="py-2">Produto</th>
                          <th className="py-2">Qtd</th>
                          <th className="py-2">Antes</th>
                          <th className="py-2">Depois</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(lancamento.itens || []).map((item) => (
                          <tr key={`${lancamento.numero_nf}-${item.movimentacao_id || item.produto_id}`} className="border-b last:border-0">
                            <td className="py-2">{item.sku || "-"}</td>
                            <td className="py-2">{item.nome || "-"}</td>
                            <td className="py-2">{item.quantidade}</td>
                            <td className="py-2">{item.estoque_anterior}</td>
                            <td className="py-2">{item.estoque_novo}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              </div>
            ))}
          </div>
        </div>
      )}

      {modalConclusao.aberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white shadow-2xl">
            <div className="border-b border-slate-200 px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Processamento concluido</p>
              <h3 className="mt-1 text-lg font-semibold text-slate-900">Baixa por NF finalizada</h3>
            </div>

            <div className="space-y-4 px-5 py-4">
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                <div>
                  <p className="text-xs text-slate-500">NF</p>
                  <p className="text-base font-semibold text-slate-900">{modalConclusao.resultado?.numero_nf}</p>
                </div>
                <CanalBadge
                  canal={modalConclusao.resultado?.plataforma}
                  label={modalConclusao.resultado?.plataforma_label}
                />
              </div>

              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                <p className="font-semibold">Confirme a loja/canal antes de seguir.</p>
                <p className="mt-1">
                  Esta baixa ficou registrada em{" "}
                  <strong>{obterCanalConfig(modalConclusao.resultado?.plataforma, modalConclusao.resultado?.plataforma_label).label}</strong>.
                  Se estiver errado, corrija agora para manter estoque, financeiro e DRE na origem certa.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase text-emerald-700">Baixas feitas</p>
                  <p className="mt-1 text-2xl font-bold text-emerald-900">
                    {contarBaixas(modalConclusao.resultado)}
                  </p>
                </div>
                <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase text-blue-700">Financeiro</p>
                  <p className="mt-1 text-2xl font-bold text-blue-900">
                    {contarLancamentosFinanceiros(modalConclusao.resultado)}
                  </p>
                </div>
              </div>

              {modalConclusao.resultado?.estoque_ja_baixado && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  O estoque desta NF ja estava baixado. O sistema nao baixou novamente e executou apenas o que ainda
                  estava pendente.
                </div>
              )}

              {modalConclusao.resultado?.tarifa_envio?.conta_pagar_id && (
                <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                  Conta a pagar gerada: <strong>#{modalConclusao.resultado.tarifa_envio.conta_pagar_id}</strong> no valor de{" "}
                  <strong>{formatMoneyBRL(modalConclusao.resultado.tarifa_envio.valor)}</strong>.
                </div>
              )}
            </div>

            <div className="flex flex-col-reverse gap-2 border-t border-slate-200 px-5 py-4 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={corrigirCanalDoResultado}
                className="rounded-lg border border-amber-300 px-4 py-2 text-sm font-semibold text-amber-800 hover:bg-amber-50"
              >
                Corrigir canal
              </button>
              <button
                type="button"
                onClick={() => fecharModalConclusao(true)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
              >
                Ver historico
              </button>
              <button
                type="button"
                onClick={() => fecharModalConclusao(false)}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
              >
                OK, novo lancamento
              </button>
            </div>
          </div>
        </div>
      )}

      {modalEditarCanal.aberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Correcao de canal</p>
                <h3 className="mt-1 text-lg font-semibold text-slate-900">
                  Editar loja/canal da NF {modalEditarCanal.lancamento?.numero_nf}
                </h3>
              </div>
              <button
                type="button"
                onClick={fecharModalEditarCanal}
                disabled={salvandoCanal}
                className="rounded-lg px-2 py-1 text-xl leading-none text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-60"
                aria-label="Fechar"
              >
                x
              </button>
            </div>

            <div className="space-y-4 px-5 py-4">
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <p>
                  Canal atual:{" "}
                  <CanalBadge
                    canal={modalEditarCanal.lancamento?.plataforma}
                    label={modalEditarCanal.lancamento?.plataforma_label}
                  />
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  A correcao atualiza a baixa de estoque e a conta a pagar da tarifa desta NF.
                </p>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="editar-canal-full">
                  Loja / canal correto
                </label>
                <select
                  id="editar-canal-full"
                  value={modalEditarCanal.canal}
                  onChange={(event) =>
                    setModalEditarCanal((prev) => ({
                      ...prev,
                      canal: event.target.value,
                    }))
                  }
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                >
                  <option value="">Selecione o canal</option>
                  {CANAIS_FULL.map((canal) => (
                    <option key={canal.value} value={canal.value}>
                      {canal.label}
                    </option>
                  ))}
                </select>
              </div>

              {modalEditarCanal.canal && modalEditarCanal.canal !== modalEditarCanal.lancamento?.plataforma && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  Vou mover esta NF para{" "}
                  <strong>{obterCanalConfig(modalEditarCanal.canal).label}</strong>. Confira antes de salvar.
                </div>
              )}
            </div>

            <div className="flex flex-col-reverse gap-2 border-t border-slate-200 px-5 py-4 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={fecharModalEditarCanal}
                disabled={salvandoCanal}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={salvarCanalLancamento}
                disabled={salvandoCanal || !modalEditarCanal.canal}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {salvandoCanal ? "Salvando..." : "Salvar canal"}
              </button>
            </div>
          </div>
        </div>
      )}

      {modalDre.aberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-xl rounded-xl bg-white shadow-2xl border border-slate-200">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Acao necessaria</p>
                <h3 className="mt-1 text-lg font-semibold text-slate-900">Vincular categoria a DRE</h3>
              </div>
              <button
                type="button"
                onClick={fecharModalDre}
                className="rounded-lg px-2 py-1 text-xl leading-none text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                aria-label="Fechar"
              >
                x
              </button>
            </div>

            <div className="space-y-4 px-5 py-4">
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                A categoria <strong>{modalDre.categoria?.caminho_completo || modalDre.categoria?.nome}</strong> ainda
                nao tem vinculo contabil. Para gerar a conta a pagar e jogar a despesa na DRE do canal selecionado, escolha
                abaixo onde essa despesa deve entrar.
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Subcategoria DRE de despesa
                </label>
                <select
                  value={dreSubcategoriaId}
                  onChange={(e) => setDreSubcategoriaId(e.target.value)}
                  disabled={carregandoDre}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 disabled:bg-slate-100"
                >
                  <option value="">
                    {carregandoDre ? "Carregando opcoes..." : "Selecione onde classificar esta despesa"}
                  </option>
                  {dreSubcategoriasDespesa.map((sub) => (
                    <option key={sub.id} value={sub.id}>
                      {sub.categoria_nome} &gt; {sub.nome}
                    </option>
                  ))}
                </select>
                {!carregandoDre && !dreSubcategoriasDespesa.length && (
                  <p className="mt-2 text-xs text-red-700">
                    Nenhuma subcategoria DRE de despesa ativa foi encontrada. Cadastre o plano DRE antes de continuar.
                  </p>
                )}
              </div>

              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
                Esse vinculo fica salvo na categoria financeira. Nas proximas baixas com a mesma categoria, o sistema ja
                segue direto.
              </div>
            </div>

            <div className="flex flex-col-reverse gap-2 border-t border-slate-200 px-5 py-4 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={fecharModalDre}
                disabled={salvandoVinculoDre}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              >
                Resolver depois
              </button>
              <button
                type="button"
                onClick={vincularDreEContinuar}
                disabled={salvandoVinculoDre || carregandoDre || !dreSubcategoriasDespesa.length}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
              >
                {salvandoVinculoDre ? "Salvando..." : "Vincular e continuar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
