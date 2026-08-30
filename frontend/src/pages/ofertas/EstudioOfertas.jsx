import {
  AlertTriangle,
  Download,
  FileDown,
  ImageDown,
  Link2,
  Plus,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";

import {
  desativarPublicacaoOferta,
  gerarImagemOferta,
  getContextoOfertas,
  getProdutosOfertas,
  getPublicacoesOfertas,
  getSugestoesOfertas,
  publicarOferta,
} from "../../api/ofertas";
import { uploadImagemProduto } from "../../api/produtos";
import { confirmarCorePet } from "../../services/corepetDialog";
import { resolveMediaUrl } from "../../utils/mediaUrl";
import OfertaCanvas from "./OfertaCanvas";
import OfertaConfiguracao from "./OfertaConfiguracao";
import OfertaEditorItens from "./OfertaEditorItens";
import OfertaPublicacoes from "./OfertaPublicacoes";
import OfertaSelecao from "./OfertaSelecao";
import { capturarPaginasOferta, criarPdfOferta } from "./ofertaCaptura";
import {
  PERIODICIDADES,
  criarItemSelecionado,
  criarPeriodo,
  montarPayloadPublicacao,
} from "./ofertasEstudioUtils";

const TITULOS_PADRAO = {
  diaria: "Ofertas do dia",
  semanal: "Ofertas da semana",
  mensal: "Ofertas do mês",
  avulsa: "Ofertas especiais",
};

function criarConfigInicial() {
  const periodo = criarPeriodo("semanal");
  return {
    titulo: TITULOS_PADRAO.semanal,
    periodicidade: "semanal",
    tipoArte: "jornal",
    formato: "quadrado",
    tema: "premium",
    exibirApp: true,
    exibirEcommerce: true,
    ...periodo,
  };
}

function detalheErro(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return fallback;
}

function nomeArquivo(titulo, indice, extensao) {
  const base = String(titulo || "ofertas")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
    .toLowerCase();
  return `${base || "ofertas"}-pagina-${indice + 1}.${extensao}`;
}

function baixarUrl(url, filename) {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function canvasParaBlob(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Falha ao preparar a imagem."))),
      "image/png",
      1,
    );
  });
}

export default function EstudioOfertas() {
  const previewRef = useRef(null);
  const [contexto, setContexto] = useState(null);
  const [produtos, setProdutos] = useState([]);
  const [selecionados, setSelecionados] = useState([]);
  const [publicacoes, setPublicacoes] = useState([]);
  const [config, setConfig] = useState(criarConfigInicial);
  const [busca, setBusca] = useState("");
  const [filtro, setFiltro] = useState("todos");
  const [estrategia, setEstrategia] = useState("mesclado");
  const [dias, setDias] = useState(7);
  const [carregando, setCarregando] = useState(true);
  const [sugerindo, setSugerindo] = useState(false);
  const [exportando, setExportando] = useState(false);
  const [publicando, setPublicando] = useState(false);
  const [gerandoImagemId, setGerandoImagemId] = useState(null);
  const [enviandoImagemId, setEnviandoImagemId] = useState(null);
  const [salvandoImagemId, setSalvandoImagemId] = useState(null);
  const [desativandoId, setDesativandoId] = useState(null);

  const carregarProdutos = useCallback(async (termo = "") => {
    const { data } = await getProdutosOfertas({ busca: termo, limite: 120 });
    setProdutos(data?.items || []);
  }, []);

  useEffect(() => {
    Promise.all([
      getContextoOfertas(),
      getProdutosOfertas({ limite: 120 }),
      getPublicacoesOfertas(),
    ])
      .then(([contextoResponse, produtosResponse, publicacoesResponse]) => {
        setContexto(contextoResponse.data);
        setProdutos(produtosResponse.data?.items || []);
        setPublicacoes(publicacoesResponse.data?.items || []);
      })
      .catch((error) =>
        toast.error(detalheErro(error, "Não foi possível abrir o Estúdio de Ofertas.")),
      )
      .finally(() => setCarregando(false));
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      carregarProdutos(busca).catch((error) =>
        toast.error(detalheErro(error, "Não foi possível buscar os produtos.")),
      );
    }, 350);
    return () => window.clearTimeout(timer);
  }, [busca, carregarProdutos]);

  const produtosFiltrados = useMemo(() => {
    if (filtro === "validade") return produtos.filter((produto) => produto.lote_validade);
    if (filtro === "sem_imagem") return produtos.filter((produto) => !produto.imagem_url);
    return produtos;
  }, [filtro, produtos]);

  const itensSemImagem = selecionados.filter((item) => !(item.imagem_url_arte || item.imagem_url));
  const periodoLabel = PERIODICIDADES[config.periodicidade] || "Promoção";

  function atualizarConfig(patch) {
    setConfig((anterior) => ({ ...anterior, ...patch }));
  }

  function mudarPeriodicidade(periodicidade) {
    setConfig((anterior) => ({
      ...anterior,
      periodicidade,
      titulo: TITULOS_PADRAO[periodicidade],
      ...criarPeriodo(periodicidade),
    }));
  }

  function alternarProduto(produto) {
    setSelecionados((atuais) => {
      if (atuais.some((item) => item.produto_id === produto.id)) {
        return atuais.filter((item) => item.produto_id !== produto.id);
      }
      return [...atuais, criarItemSelecionado(produto)];
    });
  }

  function alternarTodos() {
    const idsExibidos = new Set(produtosFiltrados.map((produto) => produto.id));
    const todosMarcados = produtosFiltrados.every((produto) =>
      selecionados.some((item) => item.produto_id === produto.id),
    );
    setSelecionados((atuais) => {
      if (todosMarcados) return atuais.filter((item) => !idsExibidos.has(item.produto_id));
      const jaMarcados = new Set(atuais.map((item) => item.produto_id));
      return [
        ...atuais,
        ...produtosFiltrados
          .filter((produto) => !jaMarcados.has(produto.id))
          .map((produto) => criarItemSelecionado(produto)),
      ];
    });
  }

  async function montarSugestao() {
    setSugerindo(true);
    try {
      const { data } = await getSugestoesOfertas({ estrategia, dias, limite: 8 });
      const sugestoes = data?.items || [];
      setSelecionados((atuais) => {
        const existentes = new Map(atuais.map((item) => [item.produto_id, item]));
        sugestoes.forEach((produto) => {
          const anterior = existentes.get(produto.id);
          existentes.set(
            produto.id,
            anterior
              ? { ...anterior, motivo_sugestao: produto.motivo_sugestao }
              : criarItemSelecionado(produto, estrategia === "validade_proxima"),
          );
        });
        return Array.from(existentes.values());
      });
      setProdutos((atuais) => {
        const porId = new Map(atuais.map((produto) => [produto.id, produto]));
        sugestoes.forEach((produto) => porId.set(produto.id, produto));
        return Array.from(porId.values());
      });
      toast.success(`${sugestoes.length} produto(s) incluído(s) pela sugestão.`);
    } catch (error) {
      toast.error(detalheErro(error, "Não foi possível montar a sugestão."));
    } finally {
      setSugerindo(false);
    }
  }

  function atualizarItem(produtoId, patch) {
    setSelecionados((atuais) =>
      atuais.map((item) => (item.produto_id === produtoId ? { ...item, ...patch } : item)),
    );
  }

  function adicionarFotoAoProduto(produtoId, foto, usarNaArte = true) {
    setProdutos((atuais) =>
      atuais.map((produto) => {
        if (produto.id !== produtoId) return produto;
        const imagens = Array.isArray(produto.imagens) ? produto.imagens : [];
        const novasImagens = imagens.some((item) => item.url === foto.url)
          ? imagens
          : [...imagens, foto];
        return {
          ...produto,
          imagens: novasImagens,
          imagem_url: produto.imagem_url || foto.url,
        };
      }),
    );
    setSelecionados((atuais) =>
      atuais.map((item) => {
        if (item.produto_id !== produtoId) return item;
        const imagens = Array.isArray(item.imagens_disponiveis) ? item.imagens_disponiveis : [];
        const novasImagens = imagens.some((imagem) => imagem.url === foto.url)
          ? imagens
          : [...imagens, foto];
        return {
          ...item,
          imagens_disponiveis: novasImagens,
          imagem_url: item.imagem_url || foto.url,
          ...(usarNaArte
            ? {
                imagem_original_url: foto.url,
                imagem_url_arte: foto.url,
                imagem_gerada_url: null,
                imagem_gerada_salva: false,
              }
            : {}),
        };
      }),
    );
  }

  async function enviarImagem(produto, file) {
    if (!file) return;
    setEnviandoImagemId(produto.produto_id || produto.id);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await uploadImagemProduto(produto.produto_id || produto.id, formData);
      const url = data?.url;
      if (!url) throw new Error("A imagem enviada não retornou endereço.");
      adicionarFotoAoProduto(produto.produto_id || produto.id, data);
      toast.success("Foto adicionada ao produto.");
    } catch (error) {
      toast.error(detalheErro(error, error.message || "Não foi possível enviar a foto."));
    } finally {
      setEnviandoImagemId(null);
    }
  }

  async function gerarImagemProfissional(item) {
    setGerandoImagemId(item.produto_id);
    try {
      const origem = resolveMediaUrl(item.imagem_url_arte || item.imagem_url);
      if (!origem) throw new Error("Envie primeiro uma foto real do produto.");
      const imagemResponse = await fetch(origem, { credentials: "include" });
      if (!imagemResponse.ok) throw new Error("Não foi possível ler a foto escolhida.");
      const blob = await imagemResponse.blob();
      const formData = new FormData();
      formData.append("produto_id", String(item.produto_id));
      formData.append("estilo", config.tema === "natural" ? "natural" : "profissional");
      formData.append("orientacao", config.formato === "quadrado" ? "quadrada" : "vertical");
      if (item.prompt_criacao?.trim()) {
        formData.append("prompt_usuario", item.prompt_criacao.trim());
      }
      formData.append("file", blob, "produto.png");
      const { data } = await gerarImagemOferta(formData);
      atualizarItem(item.produto_id, {
        imagem_gerada_url: data.url,
        imagem_gerada_salva: false,
        imagem_url_arte: data.url,
      });
      toast.success("Versão profissional criada. Confira a embalagem antes de publicar.");
    } catch (error) {
      toast.error(detalheErro(error, error.message || "Não foi possível gerar a imagem."));
    } finally {
      setGerandoImagemId(null);
    }
  }

  async function salvarImagemGeradaNoProduto(item) {
    if (!item.imagem_gerada_url) return;
    setSalvandoImagemId(item.produto_id);
    try {
      const origem = resolveMediaUrl(item.imagem_gerada_url);
      const imagemResponse = await fetch(origem, { credentials: "include" });
      if (!imagemResponse.ok) throw new Error("Não foi possível ler a imagem gerada.");
      const blob = await imagemResponse.blob();
      const formData = new FormData();
      formData.append("file", blob, `produto-${item.produto_id}-ia.png`);
      const { data } = await uploadImagemProduto(item.produto_id, formData);
      if (!data?.url) throw new Error("A imagem salva não retornou endereço.");
      adicionarFotoAoProduto(item.produto_id, data, false);
      atualizarItem(item.produto_id, {
        imagem_gerada_url: data.url,
        imagem_url_arte: data.url,
        imagem_gerada_salva: true,
      });
      toast.success("Imagem gerada salva na galeria do produto.");
    } catch (error) {
      toast.error(detalheErro(error, error.message || "Não foi possível salvar a imagem."));
    } finally {
      setSalvandoImagemId(null);
    }
  }

  async function capturarPaginas() {
    return capturarPaginasOferta(previewRef.current, config.formato);
  }

  function validarGeracao() {
    if (!selecionados.length) throw new Error("Selecione ao menos um produto.");
    if (itensSemImagem.length) {
      throw new Error(`Adicione uma foto para ${itensSemImagem.length} produto(s) antes de gerar.`);
    }
    if (!config.titulo.trim()) throw new Error("Informe um título para a promoção.");
    if (new Date(config.fim) <= new Date(config.inicio)) {
      throw new Error("A data final deve ser posterior ao início.");
    }
    if (
      new Date(config.expira) <= new Date() ||
      new Date(config.expira) <= new Date(config.inicio)
    ) {
      throw new Error("A validade do link deve ser posterior ao início da promoção.");
    }
    const validadeIncompativel = selecionados.find(
      (item) =>
        item.mostrar_validade &&
        item.lote_validade?.data_validade &&
        config.fim.slice(0, 10) > item.lote_validade.data_validade.slice(0, 10),
    );
    if (validadeIncompativel) {
      throw new Error(
        `A promoção de ${validadeIncompativel.nome} deve terminar até a validade do lote.`,
      );
    }
  }

  async function baixarPng() {
    setExportando(true);
    try {
      validarGeracao();
      const canvases = await capturarPaginas();
      canvases.forEach((canvas, indice) =>
        baixarUrl(canvas.toDataURL("image/png", 1), nomeArquivo(config.titulo, indice, "png")),
      );
      toast.success(`${canvases.length} imagem(ns) gerada(s).`);
    } catch (error) {
      toast.error(error.message || "Não foi possível gerar as imagens.");
    } finally {
      setExportando(false);
    }
  }

  async function baixarPdf() {
    setExportando(true);
    try {
      validarGeracao();
      const canvases = await capturarPaginas();
      const pdf = criarPdfOferta(canvases, config.formato);
      pdf.save(nomeArquivo(config.titulo, 0, "pdf").replace("-pagina-1", ""));
      toast.success("PDF gerado.");
    } catch (error) {
      toast.error(error.message || "Não foi possível gerar o PDF.");
    } finally {
      setExportando(false);
    }
  }

  async function publicarLink() {
    setPublicando(true);
    try {
      validarGeracao();
      const canvases = await capturarPaginas();
      const formData = new FormData();
      const payload = montarPayloadPublicacao({ ...config, itens: selecionados });
      formData.append("payload", JSON.stringify(payload));
      const blobs = await Promise.all(canvases.map(canvasParaBlob));
      blobs.forEach((blob, indice) =>
        formData.append("files", blob, nomeArquivo(config.titulo, indice, "png")),
      );
      const { data } = await publicarOferta(formData);
      setPublicacoes((atuais) => [data, ...atuais.filter((item) => item.id !== data.id)]);
      const link = `${window.location.origin}${data.link_path}`;
      await navigator.clipboard?.writeText(link).catch(() => {});
      toast.success(
        "Campanha salva e publicada. O link foi copiado e você pode criar outras campanhas.",
      );
    } catch (error) {
      toast.error(detalheErro(error, error.message || "Não foi possível publicar o link."));
    } finally {
      setPublicando(false);
    }
  }

  async function iniciarNovaCampanha() {
    if (
      selecionados.length &&
      !(await confirmarCorePet(
        "Começar uma nova campanha? A seleção e as configurações atuais serão limpas, mas as campanhas já salvas continuarão publicadas.",
      ))
    ) {
      return;
    }
    setSelecionados([]);
    setConfig(criarConfigInicial());
    toast.success("Nova campanha iniciada. As campanhas anteriores continuam salvas.");
  }

  async function desativar(id) {
    if (
      !(await confirmarCorePet(
        "Desativar este link de ofertas? Quem o abrir não verá mais as imagens.",
      ))
    ) {
      return;
    }
    setDesativandoId(id);
    try {
      const { data } = await desativarPublicacaoOferta(id);
      setPublicacoes((atuais) => atuais.map((item) => (item.id === id ? data : item)));
      toast.success("Link desativado.");
    } catch (error) {
      toast.error(detalheErro(error, "Não foi possível desativar o link."));
    } finally {
      setDesativandoId(null);
    }
  }

  async function copiar(texto) {
    try {
      await navigator.clipboard.writeText(texto);
      toast.success("Link copiado.");
    } catch {
      toast.error("Não foi possível copiar automaticamente.");
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1600px]">
        <header className="mb-6 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.16em] text-violet-700">
              <Sparkles size={18} /> Campanhas
            </div>
            <h1 className="mt-1 text-3xl font-black text-slate-950">Estúdio de Ofertas</h1>
            <p className="mt-1 max-w-3xl text-sm text-slate-600">
              Monte jornais, cards individuais ou imagens limpas. Ajuste preços, use a validade
              quando desejar e compartilhe por link, WhatsApp ou Instagram.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={iniciarNovaCampanha}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet-700 px-4 py-2 text-sm font-bold text-white"
            >
              <Plus size={16} /> Nova campanha
            </button>
            <button
              type="button"
              onClick={() => carregarProdutos(busca)}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700"
            >
              <RefreshCw size={16} /> Atualizar produtos
            </button>
          </div>
        </header>

        <div className="grid items-start gap-6 2xl:grid-cols-[minmax(0,1.15fr)_minmax(480px,.85fr)]">
          <div className="space-y-6">
            <OfertaConfiguracao
              config={config}
              onChange={atualizarConfig}
              onPeriodicidade={mudarPeriodicidade}
            />
            <OfertaSelecao
              produtos={produtosFiltrados}
              selecionados={selecionados}
              busca={busca}
              onBusca={setBusca}
              filtro={filtro}
              onFiltro={setFiltro}
              estrategia={estrategia}
              onEstrategia={setEstrategia}
              dias={dias}
              onDias={setDias}
              onSugerir={montarSugestao}
              sugerindo={sugerindo}
              onToggle={alternarProduto}
              onSelecionarTodos={alternarTodos}
              onUpload={enviarImagem}
              enviandoImagemId={enviandoImagemId}
              carregando={carregando}
            />
            <OfertaEditorItens
              itens={selecionados}
              tipoArte={config.tipoArte}
              onUpdate={atualizarItem}
              onRemove={(produtoId) =>
                setSelecionados((atuais) => atuais.filter((item) => item.produto_id !== produtoId))
              }
              onRemoveMany={(produtoIds) => {
                const ids = new Set(produtoIds);
                setSelecionados((atuais) => atuais.filter((item) => !ids.has(item.produto_id)));
              }}
              onUpload={enviarImagem}
              onGerarImagem={gerarImagemProfissional}
              onSalvarImagemGerada={salvarImagemGeradaNoProduto}
              gerandoImagemId={gerandoImagemId}
              enviandoImagemId={enviandoImagemId}
              salvandoImagemId={salvandoImagemId}
            />
            <OfertaPublicacoes
              publicacoes={publicacoes}
              onDesativar={desativar}
              onCopiar={copiar}
              desativandoId={desativandoId}
            />
          </div>

          <aside className="space-y-4 2xl:sticky 2xl:top-5">
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
              <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="font-black text-slate-950">Prévia pronta para compartilhar</h2>
                  <p className="text-xs text-slate-500">
                    A arte final usa os preços e as imagens escolhidos ao lado.
                  </p>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-black text-slate-600">
                  {selecionados.length} produto(s)
                </span>
              </div>

              {itensSemImagem.length ? (
                <div className="mb-4 flex gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-900">
                  <AlertTriangle size={17} className="shrink-0" />
                  Adicione uma foto para {itensSemImagem.length} produto(s). Você pode tirar a foto
                  agora e depois escolher entre a original e a versão profissional criada pela IA.
                </div>
              ) : null}

              <div className="max-h-[64vh] overflow-y-auto rounded-xl bg-slate-100 p-3">
                <OfertaCanvas
                  itens={selecionados}
                  contexto={contexto}
                  titulo={config.titulo}
                  periodicidadeLabel={periodoLabel}
                  tipoArte={config.tipoArte}
                  formato={config.formato}
                  tema={config.tema}
                  containerRef={previewRef}
                />
              </div>

              <div className="mt-4 grid gap-2 sm:grid-cols-3">
                <button
                  type="button"
                  disabled={exportando || publicando}
                  onClick={baixarPng}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 px-3 py-3 text-xs font-black text-slate-700 disabled:opacity-50"
                >
                  <ImageDown size={17} /> Baixar PNG
                </button>
                <button
                  type="button"
                  disabled={exportando || publicando}
                  onClick={baixarPdf}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 px-3 py-3 text-xs font-black text-slate-700 disabled:opacity-50"
                >
                  <FileDown size={17} /> Baixar PDF
                </button>
                <button
                  type="button"
                  disabled={exportando || publicando}
                  onClick={publicarLink}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-teal-700 px-3 py-3 text-xs font-black text-white disabled:opacity-50"
                >
                  <Link2 size={17} />
                  {publicando ? "Salvando..." : "Salvar campanha e gerar link"}
                </button>
              </div>
              {(exportando || publicando) && (
                <p className="mt-3 flex items-center justify-center gap-2 text-xs font-semibold text-slate-500">
                  <Download size={14} className="animate-bounce" /> Preparando arte em alta
                  resolução...
                </p>
              )}
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}
