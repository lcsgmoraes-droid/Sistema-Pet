import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import "../styles/CalculadoraRacao.css";

const camposIncompletosTexto = (campos = []) =>
  campos.length ? `Falta preencher: ${campos.join(", ")}` : "";

const normalizarTexto = (valor) =>
  String(valor || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

const termosBusca = (valor) =>
  normalizarTexto(valor)
    .split(/\s+/)
    .map((termo) => termo.trim())
    .filter(Boolean);

const aliasesBusca = {
  cao: ["cao", "caes", "canino", "dog", "cachorro"],
  caes: ["caes", "cao", "canino", "dog", "cachorro"],
  cachorro: ["cachorro", "cao", "caes", "canino", "dog"],
  dog: ["dog", "cao", "caes", "canino", "cachorro"],
  especial: ["especial", "special"],
  felino: ["felino", "gato", "cat"],
  gato: ["gato", "felino", "cat"],
  cat: ["cat", "gato", "felino"],
  racao: ["racao", "racoes"],
  racoes: ["racoes", "racao"],
  special: ["special", "especial"],
};

const variacoesTermoBusca = (termo) => aliasesBusca[termo] || [termo];

const temValorPreenchido = (valor) => {
  if (valor === null || valor === undefined) return false;
  if (Array.isArray(valor)) return valor.length > 0;
  if (typeof valor === "object") return Object.keys(valor).length > 0;

  const texto = String(valor).trim();
  return !["", "{}", "[]", "null", "undefined", "none"].includes(
    texto.toLowerCase(),
  );
};

const temJsonPreenchido = (valor) => {
  if (!temValorPreenchido(valor)) return false;
  if (typeof valor === "object") return temValorPreenchido(valor);

  try {
    const parsed = JSON.parse(valor);
    if (Array.isArray(parsed)) return parsed.length > 0;
    if (parsed && typeof parsed === "object") {
      return Object.values(parsed).some((item) => temValorPreenchido(item));
    }
    return temValorPreenchido(parsed);
  } catch {
    return temValorPreenchido(valor);
  }
};

const numeroPositivo = (valor) => {
  const numero = Number(valor);
  return Number.isFinite(numero) && numero > 0;
};

const produtoTemConfigRacao = (produto) => {
  const tipo = normalizarTexto(produto?.tipo);
  const classificacao = normalizarTexto(produto?.classificacao_racao);

  return (
    produto?.eh_racao === true ||
    tipo.startsWith("racao") ||
    tipo.startsWith("ra") ||
    Boolean(produto?.linha_racao_id) ||
    (Boolean(classificacao) && !["nao", "não"].includes(classificacao))
  );
};

const produtoPareceRacao = (produto) => {
  const textoBusca = normalizarTexto(
    [
      produto?.nome,
      produto?.categoria_nome,
      produto?.categoria?.nome,
      produto?.marca?.nome,
      produto?.classificacao_racao,
      produto?.especies_indicadas,
    ]
      .filter(Boolean)
      .join(" "),
  );

  return (
    produtoTemConfigRacao(produto) ||
    temValorPreenchido(produto?.tabela_consumo) ||
    temValorPreenchido(produto?.tabela_nutricional) ||
    /(racao|racoes|dog|cat|gato|cao|caes|canino|felino|royal|premier|special|especial)/.test(
      textoBusca,
    )
  );
};

const avaliarAptidaoRacao = (produto) => {
  const faltantes = [];

  if (!produtoTemConfigRacao(produto)) faltantes.push("aba Ração");
  if (!numeroPositivo(produto?.peso_embalagem))
    faltantes.push("peso da embalagem");
  if (!numeroPositivo(produto?.preco_venda)) faltantes.push("preço de venda");
  if (!temValorPreenchido(produto?.linha_racao_id || produto?.classificacao_racao))
    faltantes.push("linha/classificação");
  if (!temValorPreenchido(produto?.porte_animal_id || produto?.porte_animal))
    faltantes.push("porte");
  if (
    !temValorPreenchido(
      produto?.fase_publico_id || produto?.fase_publico || produto?.categoria_racao,
    )
  )
    faltantes.push("fase/público");
  if (!temValorPreenchido(produto?.sabor_proteina_id || produto?.sabor_proteina))
    faltantes.push("sabor/proteína");
  if (!temValorPreenchido(produto?.especies_indicadas))
    faltantes.push("espécie indicada");
  if (!temJsonPreenchido(produto?.tabela_consumo))
    faltantes.push("tabela de consumo");

  return {
    apta: faltantes.length === 0,
    faltantes,
  };
};

const formatarMoeda = (valor) =>
  Number(valor || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });

const formatarPeso = (valor) => {
  if (!numeroPositivo(valor)) return "sem peso";
  return `${Number(valor).toLocaleString("pt-BR", {
    maximumFractionDigits: 3,
  })}kg`;
};

const formatarRacaoLabel = (produto) =>
  `${produto.nome} - ${formatarPeso(produto.peso_embalagem)} - ${formatarMoeda(produto.preco_venda)}`;

const extrairListaProdutos = (data) => {
  if (typeof data === "string") {
    try {
      return extrairListaProdutos(JSON.parse(data));
    } catch {
      return [];
    }
  }

  if (Array.isArray(data)) return data;
  if (!data || typeof data !== "object") return [];

  return data.items || data.produtos || data.itens || data.data || [];
};

const prepararProdutosComAptidao = (lista = []) =>
  lista
    .filter((produto) => produto && produtoPareceRacao(produto))
    .map((produto) => ({
      ...produto,
      aptidao: avaliarAptidaoRacao(produto),
    }));

const combinarProdutosComAptidao = (...listas) => {
  const mapa = new Map();

  listas.flat().forEach((produto) => {
    if (!produto?.id) return;
    const chave = String(produto.id);
    const anterior = mapa.get(chave) || {};
    mapa.set(chave, {
      ...anterior,
      ...produto,
      aptidao: produto.aptidao || avaliarAptidaoRacao(produto),
    });
  });

  return Array.from(mapa.values());
};

const variantesBuscaRemota = (valor) => {
  const termo = String(valor || "").trim();
  const normalizado = normalizarTexto(termo);
  const variantes = [termo, normalizado];

  if (/\bspecial\b/.test(normalizado)) {
    variantes.push(normalizado.replace(/\bspecial\b/g, "especial"));
  }

  if (/\bespecial\b/.test(normalizado)) {
    variantes.push(normalizado.replace(/\bespecial\b/g, "special"));
  }

  return [...new Set(variantes.filter(Boolean))].slice(0, 3);
};

const buscarRacoesNoCadastro = async (termo, pageSize = 80) => {
  const response = await api.get("/produtos/calculadora-racao/opcoes", {
    params: {
      busca: String(termo || "").trim() || undefined,
      page: 1,
      page_size: pageSize,
      _ts: Date.now(),
    },
  });

  return extrairListaProdutos(response.data);
};

const textoBuscaRacao = (produto) =>
  normalizarTexto(
    [
      produto?.nome,
      produto?.codigo,
      produto?.sku,
      produto?.codigo_barras,
      produto?.categoria_nome,
      produto?.categoria?.nome,
      produto?.marca?.nome,
      produto?.marca_nome,
      produto?.descricao_curta,
      produto?.descricao_completa,
      produto?.classificacao_racao,
      produto?.categoria_racao,
      produto?.especies_indicadas,
      formatarPeso(produto?.peso_embalagem),
      formatarMoeda(produto?.preco_venda),
    ]
      .filter(Boolean)
      .join(" "),
  );

const termoCasaComPalavra = (termo, palavras) =>
  palavras.some((palavra) => {
    if (palavra.includes(termo)) return true;
    return termo.length >= 4 && palavra.length >= 4 && termo.includes(palavra);
  });

const termoEncontradoNoProduto = (termo, texto, palavras) =>
  variacoesTermoBusca(termo).some(
    (alias) => texto.includes(alias) || termoCasaComPalavra(alias, palavras),
  );

const pontuarBuscaRacao = (produto, valor) => {
  const consulta = normalizarTexto(valor);
  if (!consulta) return 1;

  const termos = termosBusca(valor);
  const texto = textoBuscaRacao(produto);
  const nome = normalizarTexto(produto?.nome);
  const palavras = texto.split(/\s+/).filter(Boolean);

  const todosTermosEncontrados = termos.every((termo) =>
    termoEncontradoNoProduto(termo, texto, palavras),
  );

  if (!todosTermosEncontrados) return 0;

  let score = 10;
  if (nome === consulta) score += 120;
  if (nome.startsWith(consulta)) score += 90;
  if (texto.includes(consulta)) score += 70;

  termos.forEach((termo) => {
    if (nome.split(/\s+/).includes(termo)) score += 12;
    else if (nome.includes(termo)) score += 8;
    else score += 4;
  });

  return score;
};

const produtoCasaComTextoSelecionado = (produto, valor) => {
  const consulta = normalizarTexto(valor);
  if (!consulta) return false;

  const nome = normalizarTexto(produto?.nome);
  const labelCompleta = normalizarTexto(formatarRacaoLabel(produto));
  const labelSemPreco = normalizarTexto(
    `${produto?.nome || ""} - ${formatarPeso(produto?.peso_embalagem)}`,
  );

  return (
    consulta === nome ||
    consulta === labelCompleta ||
    consulta === labelSemPreco ||
    consulta.includes(nome) ||
    labelCompleta.includes(consulta)
  );
};

const escolherRacaoAptaPorTexto = (valor, ...listas) => {
  const consulta = normalizarTexto(valor);
  if (!consulta) return null;

  const candidatos = combinarProdutosComAptidao(...listas).filter(
    (produto) => produto?.aptidao?.apta,
  );

  const matchDireto = candidatos.find((produto) =>
    produtoCasaComTextoSelecionado(produto, valor),
  );
  if (matchDireto) return matchDireto;

  const pontuados = candidatos
    .map((produto) => ({
      produto,
      score: pontuarBuscaRacao(produto, valor),
    }))
    .filter((item) => item.score > 0)
    .sort((a, b) => {
      if (a.score !== b.score) return b.score - a.score;
      return a.produto.nome.localeCompare(b.produto.nome, "pt-BR");
    });

  return pontuados.length === 1 ? pontuados[0].produto : null;
};

function RacaoSearchInput({
  disabled = false,
  hint,
  id,
  label,
  loading = false,
  name,
  onChange,
  onClear,
  onSelect,
  placeholder,
  produtos,
  value,
  warning,
}) {
  const [aberto, setAberto] = useState(false);
  const [dropdown, setDropdown] = useState({
    direction: "down",
    maxHeight: 320,
  });
  const controlRef = useRef(null);
  const termo = normalizarTexto(value);

  const abrirDropdown = () => {
    if (disabled) return;

    if (typeof window === "undefined" || !controlRef.current) {
      setAberto(true);
      return;
    }

    const rect = controlRef.current.getBoundingClientRect();
    const margemTela = 16;
    const espacoAbaixo = window.innerHeight - rect.bottom - margemTela;
    const espacoAcima = rect.top - margemTela;
    const direction =
      espacoAbaixo < 260 && espacoAcima > espacoAbaixo ? "up" : "down";
    const espacoDisponivel = direction === "up" ? espacoAcima : espacoAbaixo;

    setDropdown({
      direction,
      maxHeight: Math.max(140, Math.min(320, Math.floor(espacoDisponivel))),
    });
    setAberto(true);
  };

  const opcoes = useMemo(() => {
    const filtradas = produtos
      .map((produto) => ({
        produto,
        score: termo ? pontuarBuscaRacao(produto, value) : 1,
      }))
      .filter((item) => item.score > 0);

    return filtradas
      .sort((a, b) => {
        if (a.produto.aptidao.apta !== b.produto.aptidao.apta) {
          return a.produto.aptidao.apta ? -1 : 1;
        }
        if (a.score !== b.score) {
          return b.score - a.score;
        }
        return a.produto.nome.localeCompare(b.produto.nome, "pt-BR");
      })
      .map((item) => item.produto)
      .slice(0, 12);
  }, [produtos, termo, value]);

  const selecionar = (produto) => {
    if (!produto.aptidao.apta) {
      toast.error(camposIncompletosTexto(produto.aptidao.faltantes));
      return;
    }
    onSelect(produto);
    setAberto(false);
  };

  return (
    <div className="racao-search-field">
      <label htmlFor={id}>{label}</label>
      <div className="racao-search-control" ref={controlRef}>
        <input
          id={id}
          name={name}
          type="text"
          value={value || ""}
          onChange={(e) => {
            onChange(e.target.value);
            abrirDropdown();
          }}
          onFocus={abrirDropdown}
          onClick={abrirDropdown}
          onBlur={() => setTimeout(() => setAberto(false), 160)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
        />
        {value && onClear && (
          <button
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={onClear}
            className="btn-clear btn-clear-compact"
            title="Limpar seleção"
          >
            ✕
          </button>
        )}
      </div>

      {aberto && !disabled && (
        <div
          className={`racao-options open-${dropdown.direction}`}
          role="listbox"
          style={{
            "--racao-options-max-height": `${dropdown.maxHeight}px`,
          }}
        >
          {loading && (
            <div className="racao-empty">Buscando no cadastro...</div>
          )}
          {!loading && opcoes.length === 0 ? (
            <div className="racao-empty">Nenhuma ração encontrada.</div>
          ) : (
            opcoes.map((produto) => (
              <button
                key={produto.id}
                type="button"
                className={`racao-option ${
                  produto.aptidao.apta ? "is-ready" : "is-incomplete"
                }`}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => selecionar(produto)}
                aria-disabled={!produto.aptidao.apta}
              >
                <div className="racao-option-main">
                  <span className="racao-option-name">{produto.nome}</span>
                  <span
                    className={`racao-status ${
                      produto.aptidao.apta ? "ready" : "incomplete"
                    }`}
                  >
                    {produto.aptidao.apta ? "Apta" : "Cadastro incompleto"}
                  </span>
                </div>
                <div className="racao-option-meta">
                  <span>{formatarPeso(produto.peso_embalagem)}</span>
                  <span>{formatarMoeda(produto.preco_venda)}</span>
                  {produto.classificacao_racao && (
                    <span>{produto.classificacao_racao}</span>
                  )}
                </div>
                {!produto.aptidao.apta && (
                  <div className="racao-option-missing">
                    {camposIncompletosTexto(produto.aptidao.faltantes)}
                  </div>
                )}
              </button>
            ))
          )}
        </div>
      )}

      {warning && <small className="form-warning">{warning}</small>}
      {hint && <small className="form-hint">{hint}</small>}
    </div>
  );
}

export default function CalculadoraRacao() {
  const [produtos, setProdutos] = useState([]);
  const [produtosBuscaPrincipal, setProdutosBuscaPrincipal] = useState([]);
  const [produtosBuscaComparativo, setProdutosBuscaComparativo] = useState([]);
  const [pets, setPets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingBuscaPrincipal, setLoadingBuscaPrincipal] = useState(false);
  const [loadingBuscaComparativo, setLoadingBuscaComparativo] = useState(false);

  // Formulário
  const [form, setForm] = useState({
    pet_id: "",
    pet_nome: "",
    produto_id: "",
    produto_nome: "",
    categoria_racao: "", // filhote, adulto, senior
    peso_pet_kg: "",
    idade_meses: "",
    nivel_atividade: "normal",
    // Filtros para comparativo
    classificacao: "",
    especies: "dog",
    produto_comparar_id: "",
    produto_comparar_nome: "",
  });

  // Resultado
  const [resultado, setResultado] = useState(null);
  const [comparativo, setComparativo] = useState([]);

  useEffect(() => {
    carregarProdutos();
    carregarPets();
  }, []);

  const produtosComAptidao = useMemo(
    () => prepararProdutosComAptidao(produtos),
    [produtos],
  );

  const produtosBuscaPrincipalComAptidao = useMemo(
    () => prepararProdutosComAptidao(produtosBuscaPrincipal),
    [produtosBuscaPrincipal],
  );

  const produtosBuscaComparativoComAptidao = useMemo(
    () => prepararProdutosComAptidao(produtosBuscaComparativo),
    [produtosBuscaComparativo],
  );

  const opcoesRacaoPrincipal = useMemo(
    () =>
      combinarProdutosComAptidao(
        produtosBuscaPrincipalComAptidao,
        produtosComAptidao,
      ),
    [produtosBuscaPrincipalComAptidao, produtosComAptidao],
  );

  const opcoesRacaoComparativo = useMemo(
    () =>
      combinarProdutosComAptidao(
        produtosBuscaComparativoComAptidao,
        produtosComAptidao,
      ),
    [produtosBuscaComparativoComAptidao, produtosComAptidao],
  );

  const resumoAptidao = useMemo(() => {
    const aptas = produtosComAptidao.filter((produto) => produto.aptidao.apta);
    return {
      aptas: aptas.length,
      incompletas: produtosComAptidao.length - aptas.length,
    };
  }, [produtosComAptidao]);

  useEffect(() => {
    const termo = String(form.produto_nome || "").trim();

    if (form.produto_id || termo.length < 2) {
      setProdutosBuscaPrincipal([]);
      setLoadingBuscaPrincipal(false);
      return undefined;
    }

    let ativo = true;
    const timer = setTimeout(async () => {
      try {
        setLoadingBuscaPrincipal(true);
        const racoes = await buscarRacoesNoCadastro(termo);

        if (ativo) {
          setProdutosBuscaPrincipal(racoes);
        }
      } catch (error) {
        console.error("Erro ao buscar rações no cadastro:", error);
        if (ativo) {
          setProdutosBuscaPrincipal([]);
        }
      } finally {
        if (ativo) {
          setLoadingBuscaPrincipal(false);
        }
      }
    }, 250);

    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, [form.produto_nome, form.produto_id]);

  useEffect(() => {
    const termo = String(form.produto_comparar_nome || "").trim();

    if (form.produto_comparar_id || termo.length < 2) {
      setProdutosBuscaComparativo([]);
      setLoadingBuscaComparativo(false);
      return undefined;
    }

    let ativo = true;
    const timer = setTimeout(async () => {
      try {
        setLoadingBuscaComparativo(true);
        const racoes = await buscarRacoesNoCadastro(termo);

        if (ativo) {
          setProdutosBuscaComparativo(racoes);
        }
      } catch (error) {
        console.error("Erro ao buscar rações para comparação:", error);
        if (ativo) {
          setProdutosBuscaComparativo([]);
        }
      } finally {
        if (ativo) {
          setLoadingBuscaComparativo(false);
        }
      }
    }, 250);

    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, [form.produto_comparar_nome, form.produto_comparar_id]);

  const buscarProdutoComAptidao = (produtoId) =>
    combinarProdutosComAptidao(
      produtosComAptidao,
      produtosBuscaPrincipalComAptidao,
      produtosBuscaComparativoComAptidao,
    ).find((produto) => String(produto.id) === String(produtoId));

  const resolverRacaoPrincipalDigitada = async () => {
    const texto = String(form.produto_nome || "").trim();

    let produto = escolherRacaoAptaPorTexto(
      texto,
      opcoesRacaoPrincipal,
      produtosComAptidao,
    );

    if (produto) return produto;
    if (texto.length < 2) return null;

    try {
      setLoadingBuscaPrincipal(true);
      const racoes = await buscarRacoesNoCadastro(texto);
      setProdutosBuscaPrincipal(racoes);
      const racoesComAptidao = prepararProdutosComAptidao(racoes);

      produto = escolherRacaoAptaPorTexto(
        texto,
        racoesComAptidao,
        opcoesRacaoPrincipal,
        produtosComAptidao,
      );

      return produto || null;
    } catch (error) {
      console.error("Erro ao resolver racao digitada:", error);
      return null;
    } finally {
      setLoadingBuscaPrincipal(false);
    }
  };

  const validarProdutoApto = (produtoId, contexto = "ração") => {
    const produto = buscarProdutoComAptidao(produtoId);
    if (!produto) {
      toast.error(`Selecione uma ${contexto} apta para análise.`);
      return false;
    }

    if (!produto.aptidao.apta) {
      toast.error(camposIncompletosTexto(produto.aptidao.faltantes));
      return false;
    }

    return true;
  };

  const selecionarRacaoPrincipal = (produto) => {
    if (!produto.aptidao.apta) {
      toast.error(camposIncompletosTexto(produto.aptidao.faltantes));
      return;
    }

    setForm((prev) => ({
      ...prev,
      produto_id: produto.id,
      produto_nome: formatarRacaoLabel(produto),
      categoria_racao: produto.categoria_racao || "",
    }));
  };

  const selecionarRacaoComparativo = (produto) => {
    if (!produto.aptidao.apta) {
      toast.error(camposIncompletosTexto(produto.aptidao.faltantes));
      return;
    }

    setForm((prev) => ({
      ...prev,
      produto_comparar_id: produto.id,
      produto_comparar_nome: formatarRacaoLabel(produto),
      classificacao: "",
    }));
  };

  const alterarBuscaRacaoPrincipal = (valor) => {
    const produtoExato = escolherRacaoAptaPorTexto(valor, opcoesRacaoPrincipal);

    setForm((prev) => ({
      ...prev,
      produto_id: produtoExato?.aptidao.apta ? produtoExato.id : "",
      produto_nome: valor,
      categoria_racao: produtoExato?.aptidao.apta
        ? produtoExato.categoria_racao || ""
        : "",
    }));
  };

  const alterarBuscaRacaoComparativo = (valor) => {
    const produtoExato = escolherRacaoAptaPorTexto(valor, opcoesRacaoComparativo);

    setForm((prev) => ({
      ...prev,
      produto_comparar_id: produtoExato?.aptidao.apta ? produtoExato.id : "",
      produto_comparar_nome: valor,
      classificacao: "",
    }));
  };

  const carregarProdutos = async () => {
    try {
      console.log("🔍 Iniciando carregamento de produtos...");

      const response = await api.get("/produtos/calculadora-racao/opcoes", {
        params: {
          page: 1,
          page_size: 1200,
          _ts: Date.now(),
        },
      });

      console.log("📡 Resposta da API:", {
        status: response.status,
        dataType: typeof response.data,
        isArray: Array.isArray(response.data),
        dataPreview:
          typeof response.data === "string"
            ? response.data.substring(0, 200)
            : "object",
      });

      // Se a resposta for string, tentar parsear
      let data = response.data;
      if (typeof data === "string") {
        console.warn("⚠️ API retornou string, tentando parsear JSON...");
        try {
          data = JSON.parse(data);
        } catch (e) {
          console.error("❌ Erro ao parsear JSON:", e);
          console.error("❌ Conteúdo recebido:", data.substring(0, 500));
          toast.error("Erro: resposta da API inválida");
          return;
        }
      }

      // A API retorna objeto paginado: {items: [], total: X}
      const listaProdutos = extrairListaProdutos(data);
      console.log("📦 Total de produtos recebidos:", listaProdutos.length);
      console.log(
        "📦 Estrutura da resposta:",
        Array.isArray(data)
          ? "Array direto"
          : `Objeto com keys: ${Object.keys(data).join(", ")}`,
      );

      if (listaProdutos.length > 0) {
        console.log("📦 Estrutura do primeiro produto:", listaProdutos[0]);
      }

      // Mostrar rações aptas e incompletas para orientar o cadastro.
      const racoes = listaProdutos.filter((p) => produtoPareceRacao(p));
      const aptas = racoes.filter((p) => avaliarAptidaoRacao(p).apta);
      console.log("🥫 Rações encontradas:", racoes.length);
      console.log("✅ Rações aptas para análise:", aptas.length);
      console.log("📊 Total de produtos:", listaProdutos.length);

      if (racoes.length > 0) {
        console.log(
          "🥫 IDs das rações:",
          racoes.map((r) => `${r.id}-${r.nome}`),
        );
      } else {
        console.log(
          "⚠️ Produtos sem peso_embalagem:",
          listaProdutos.slice(0, 5).map((p) => ({
            id: p.id,
            nome: p.nome,
            peso_embalagem: p.peso_embalagem,
            categoria_racao: p.categoria_racao,
            classificacao_racao: p.classificacao_racao,
          })),
        );
      }

      setProdutos(racoes);

      if (racoes.length === 0 && listaProdutos.length > 0) {
        console.warn("⚠️ Produtos encontrados, mas nenhum parece ser ração");
        toast.error(
          `${listaProdutos.length} produtos encontrados, mas nenhum parece estar marcado como ração. ` +
            'Edite os produtos de ração e preencha a aba "Ração".',
          { duration: 6000 },
        );
      } else if (racoes.length === 0) {
        console.log("ℹ️ Nenhum produto encontrado");
        toast.error("Nenhum produto encontrado. Cadastre produtos primeiro.");
      }
    } catch (error) {
      console.error("❌ Erro ao carregar produtos:", error);
      console.error("❌ Detalhes:", error.response?.data || error.message);
      toast.error(
        `Erro ao carregar produtos: ${error.response?.data?.detail || error.message}`,
      );
    }
  };

  const carregarPets = async () => {
    try {
      const response = await api.get("/clientes/pets/todos");
      const listaPets = Array.isArray(response.data) ? response.data : [];
      setPets(listaPets);
      console.log("🐾 Pets carregados:", listaPets.length);
    } catch (error) {
      console.error("❌ Erro ao carregar pets:", error);
      // Não mostrar erro para não incomodar se não tiver pets
    }
  };

  const handlePetChange = (petId) => {
    const petSelecionado = pets.find((p) => p.id === parseInt(petId));

    if (petSelecionado) {
      // Calcular idade em meses a partir da data de nascimento
      let idadeMeses = "";
      if (petSelecionado.data_nascimento) {
        const nascimento = new Date(petSelecionado.data_nascimento);
        const hoje = new Date();
        const diffTime = Math.abs(hoje - nascimento);
        const diffMonths = Math.floor(diffTime / (1000 * 60 * 60 * 24 * 30.44)); // média de dias por mês
        idadeMeses = diffMonths.toString();
      }

      const especieTexto =
        petSelecionado.especie === "Cachorro"
          ? "dog"
          : petSelecionado.especie === "Gato"
            ? "cat"
            : form.especies;

      setForm({
        ...form,
        pet_id: petId,
        pet_nome: `${petSelecionado.nome} - ${petSelecionado.especie} ${petSelecionado.peso ? `(${petSelecionado.peso}kg)` : ""}`,
        peso_pet_kg: petSelecionado.peso || "",
        idade_meses: idadeMeses,
        especies: especieTexto,
      });

      toast.success(`Pet ${petSelecionado.nome} selecionado!`);
    } else {
      setForm({
        ...form,
        pet_id: "",
        peso_pet_kg: "",
        idade_meses: "",
      });
    }
  };

  const calcular = async () => {
    if (!form.peso_pet_kg) {
      toast.error("Informe o peso do pet");
      return;
    }

    let produtoSelecionado = form.produto_id
      ? buscarProdutoComAptidao(form.produto_id)
      : null;

    if (!produtoSelecionado && form.produto_nome) {
      produtoSelecionado = await resolverRacaoPrincipalDigitada();
    }

    const produtoIdCalculo = produtoSelecionado?.id
      ? parseInt(produtoSelecionado.id)
      : null;
    const categoriaRacaoCalculo =
      produtoSelecionado?.categoria_racao || form.categoria_racao;

    if (!produtoIdCalculo) {
      toast.error("Selecione uma ração apta para análise.");
      return;
    }

    if (!produtoSelecionado.aptidao.apta) {
      toast.error(camposIncompletosTexto(produtoSelecionado.aptidao.faltantes));
      return;
    }

    if (String(form.produto_id) !== String(produtoIdCalculo)) {
      setForm((prev) => ({
        ...prev,
        produto_id: produtoIdCalculo,
        produto_nome: formatarRacaoLabel(produtoSelecionado),
        categoria_racao: categoriaRacaoCalculo || "",
      }));
    }

    // Validar idade obrigatória para ração de filhote
    if (categoriaRacaoCalculo === "filhote" && !form.idade_meses) {
      toast.error("⚠️ Idade é obrigatória para rações de filhote!");
      return;
    }

    try {
      setLoading(true);
      const response = await api.post("/produtos/calculadora-racao", {
        produto_id: produtoIdCalculo,
        peso_pet_kg: parseFloat(form.peso_pet_kg),
        idade_meses: form.idade_meses ? parseInt(form.idade_meses) : null,
        nivel_atividade: form.nivel_atividade,
      });
      setResultado(response.data);
      setComparativo([]);
      toast.success("Cálculo realizado!");
    } catch (error) {
      console.error("Erro:", error);
      toast.error(error.response?.data?.detail || "Erro ao calcular");
    } finally {
      setLoading(false);
    }
  };

  const compararRacoes = async () => {
    if (!form.peso_pet_kg) {
      toast.error("Informe o peso do pet");
      return;
    }

    if (form.produto_id && !validarProdutoApto(form.produto_id)) {
      return;
    }

    if (form.produto_comparar_nome && !form.produto_comparar_id) {
      toast.error("Selecione uma ração de comparação apta ou limpe o campo.");
      return;
    }

    if (
      form.produto_comparar_id &&
      !validarProdutoApto(form.produto_comparar_id, "ração de comparação")
    ) {
      return;
    }

    try {
      setLoading(true);

      // MODO 1x1: Se selecionou uma ração específica para comparar
      if (form.produto_comparar_id) {
        // Calcular SOMENTE para a ração selecionada no comparativo
        const calcResponse = await api.post("/produtos/calculadora-racao", {
          produto_id: parseInt(form.produto_comparar_id),
          peso_pet_kg: parseFloat(form.peso_pet_kg),
          idade_meses: form.idade_meses ? parseInt(form.idade_meses) : null,
          nivel_atividade: form.nivel_atividade,
        });

        const racaoComparar = calcResponse.data;

        // Se também selecionou uma ração principal, calcular ela também
        if (form.produto_id) {
          const calcPrincipal = await api.post(
            "/produtos/calculadora-racao",
            {
              produto_id: parseInt(form.produto_id),
              peso_pet_kg: parseFloat(form.peso_pet_kg),
              idade_meses: form.idade_meses ? parseInt(form.idade_meses) : null,
              nivel_atividade: form.nivel_atividade,
            },
          );

          // Evitar duplicatas: se selecionou a mesma ração
          if (calcPrincipal.data.produto_id === racaoComparar.produto_id) {
            setComparativo([calcPrincipal.data]);
            toast.success(`Mostrando cálculo da ração selecionada`);
          } else {
            // Mostrar SOMENTE essas duas rações: selecionada primeiro, depois a comparada
            const duasRacoes = [calcPrincipal.data, racaoComparar];
            setComparativo(duasRacoes);
            toast.success(`Comparando 2 rações selecionadas!`);
          }
        } else {
          // Se não tem ração principal, mostrar só a do comparativo
          setComparativo([racaoComparar]);
          toast.success(`Mostrando cálculo da ração selecionada`);
        }

        // Mantém o resultado individual visível
      } else {
        // MODO FILTROS: usar filtros de classificação e espécie
        const params = {
          peso_pet_kg: parseFloat(form.peso_pet_kg),
          nivel_atividade: form.nivel_atividade,
        };
        if (form.idade_meses) params.idade_meses = parseInt(form.idade_meses);
        if (form.classificacao) params.classificacao = form.classificacao;
        if (form.especies) params.especies = form.especies;

        const response = await api.post("/produtos/comparar-racoes", null, {
          params,
        });

        let todasRacoes = response.data.racoes || [];

        // Se há uma ração selecionada no campo principal, incluir ela sempre
        if (form.produto_id) {
          // Primeiro, remover a ração principal da lista se já estiver lá
          todasRacoes = todasRacoes.filter(
            (r) => r.produto_id !== parseInt(form.produto_id),
          );

          // Calcular a ração principal
          const calcPrincipal = await api.post(
            "/produtos/calculadora-racao",
            {
              produto_id: parseInt(form.produto_id),
              peso_pet_kg: parseFloat(form.peso_pet_kg),
              idade_meses: form.idade_meses ? parseInt(form.idade_meses) : null,
              nivel_atividade: form.nivel_atividade,
            },
          );

          const racaoPrincipal = calcPrincipal.data;

          // ORDENAR só as outras rações por custo-benefício
          todasRacoes.sort((a, b) => a.custo_por_dia - b.custo_por_dia);

          // Colocar ração principal SEMPRE no topo
          todasRacoes = [racaoPrincipal, ...todasRacoes];
        }

        // LIMITADOR: mostrar no máximo 10 rações
        const racoesLimitadas = todasRacoes.slice(0, 10);

        setComparativo(racoesLimitadas);
        // Mantém o resultado individual visível

        const totalRacoes = todasRacoes.length;
        if (totalRacoes === 0) {
          toast.error(
            "Nenhuma ração encontrada com esses filtros. Tente outros critérios.",
          );
        }
      }
    } catch (error) {
      console.error("Erro:", error);
      toast.error(error.response?.data?.detail || "Erro ao comparar");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="calculadora-racao-container">
      <div className="header">
        <h1>🥫 Calculadora de Ração</h1>
        <p>Calcule duração, custo/dia e compare produtos</p>
      </div>

      <div className="calculadora-grid">
        {/* Formulário */}
        <div className="form-card">
          <h2>📝 Dados do Pet</h2>

          {/* NOVO: Buscar Pet Cadastrado */}
          <div className="form-group">
            <label htmlFor="racao-pet-search">🐾 Buscar Pet Cadastrado</label>
            <input
              id="racao-pet-search"
              name="racao_pet_search"
              type="text"
              list="pets-list"
              value={form.pet_nome || ""}
              onChange={(e) => {
                const nomePet = e.target.value;
                setForm({ ...form, pet_nome: nomePet });

                // Se digitou exatamente o nome de um pet, seleciona ele
                const petEncontrado = pets.find(
                  (p) =>
                    `${p.nome} - ${p.especie} ${p.peso ? `(${p.peso}kg)` : ""}` ===
                    nomePet,
                );
                if (petEncontrado) {
                  handlePetChange(petEncontrado.id);
                }
              }}
              placeholder="Digite ou selecione um pet"
              className="pet-select"
            />
            <datalist id="pets-list">
              {pets.map((pet) => (
                <option
                  key={pet.id}
                  value={`${pet.nome} - ${pet.especie} ${pet.peso ? `(${pet.peso}kg)` : ""}`}
                />
              ))}
            </datalist>
            <small className="form-hint">
              💡 Digite ou selecione um pet para preencher automaticamente peso
              e idade
            </small>
          </div>

          <div className="form-group">
            <label htmlFor="racao-peso-pet">Peso do Pet (kg) *</label>
            <input
              id="racao-peso-pet"
              name="racao_peso_pet_kg"
              type="number"
              step="0.1"
              value={form.peso_pet_kg}
              onChange={(e) =>
                setForm({ ...form, peso_pet_kg: e.target.value })
              }
              placeholder="Ex: 8.5"
            />
          </div>

          <div className="form-group">
            <label htmlFor="racao-idade-meses">
              Idade (meses)
              {form.categoria_racao === "filhote" && (
                <span style={{ color: "#ff6b6b" }}> *</span>
              )}
            </label>
            <input
              id="racao-idade-meses"
              name="racao_idade_meses"
              type="number"
              value={form.idade_meses}
              onChange={(e) =>
                setForm({ ...form, idade_meses: e.target.value })
              }
              placeholder={
                form.categoria_racao === "filhote"
                  ? "Obrigatório para filhotes!"
                  : "Ex: 24 (opcional)"
              }
              required={form.categoria_racao === "filhote"}
              style={
                form.categoria_racao === "filhote"
                  ? { borderColor: "#ff6b6b", borderWidth: "2px" }
                  : {}
              }
            />
          </div>

          <div className="form-group">
            <label htmlFor="racao-nivel-atividade">Nível de Atividade</label>
            <select
              id="racao-nivel-atividade"
              name="racao_nivel_atividade"
              value={form.nivel_atividade}
              onChange={(e) =>
                setForm({ ...form, nivel_atividade: e.target.value })
              }
            >
              <option value="baixo">Baixo</option>
              <option value="normal">Normal</option>
              <option value="alto">Alto</option>
            </select>
          </div>

          <hr />

          <h3>🥫 Ração</h3>

          <div className="form-group">
            <RacaoSearchInput
              id="racao-produto-principal"
              name="racao_produto_principal"
              label="Selecionar Ração"
              value={form.produto_nome || ""}
              onChange={alterarBuscaRacaoPrincipal}
              onSelect={selecionarRacaoPrincipal}
              onClear={() =>
                setForm((prev) => ({
                  ...prev,
                  produto_id: "",
                  produto_nome: "",
                  categoria_racao: "",
                }))
              }
              produtos={opcoesRacaoPrincipal}
              loading={loadingBuscaPrincipal}
              placeholder="Digite ou selecione uma ração"
              hint={`${resumoAptidao.aptas} aptas para análise · ${resumoAptidao.incompletas} com cadastro incompleto`}
            />
            {form.categoria_racao === "filhote" && (
              <small
                className="form-hint"
                style={{ color: "#ff6b6b", fontWeight: "bold" }}
              >
                ⚠️ Ração de filhote - idade é obrigatória!
              </small>
            )}
          </div>

          <div className="button-group">
            <button
              onClick={calcular}
              disabled={loading}
              className="btn-primary"
            >
              {loading ? "Calculando..." : "📊 Calcular"}
            </button>
          </div>

          <hr />

          <h3>🔍 Comparar Rações</h3>

          <div className="info-box">
            <strong>💡 Dica:</strong> Escolha UMA das opções abaixo:
            <br />• Selecione uma ração específica para ver como ela se compara
            <br />• OU use os filtros gerais para ver todas de uma categoria
          </div>

          {/* NOVO: Selecionar uma ração específica para comparar */}
          <div className="form-group">
            <div style={{ display: "flex", gap: "8px" }}>
              <RacaoSearchInput
                id="racao-produto-comparar"
                name="racao_produto_comparar"
                label="⭐ Comparar Ração Específica"
                value={form.produto_comparar_nome || ""}
                onChange={alterarBuscaRacaoComparativo}
                onSelect={selecionarRacaoComparativo}
                onClear={() =>
                  setForm((prev) => ({
                    ...prev,
                    produto_comparar_id: "",
                    produto_comparar_nome: "",
                  }))
                }
                produtos={opcoesRacaoComparativo}
                loading={loadingBuscaComparativo}
                placeholder="Digite ou selecione uma ração"
                disabled={form.classificacao !== ""}
                warning={
                  form.classificacao
                    ? "⚠️ Limpe o filtro de classificação para usar esta opção"
                    : ""
                }
                hint={
                  !form.produto_comparar_id && !form.classificacao
                    ? "💡 Deixe vazio para comparar por classificação abaixo"
                    : ""
                }
              />
            </div>
          </div>

          <div className="divider-text">OU</div>

          <div className="form-group">
            <label htmlFor="racao-filtro-classificacao">📋 Filtro por Classificação</label>
            <div style={{ display: "flex", gap: "8px" }}>
              <select
                id="racao-filtro-classificacao"
                name="racao_filtro_classificacao"
                value={form.classificacao}
                onChange={(e) =>
                  setForm({
                    ...form,
                    classificacao: e.target.value,
                    produto_comparar_id: "",
                    produto_comparar_nome: "",
                  })
                }
                disabled={form.produto_comparar_id !== ""}
                style={{ flex: 1 }}
              >
                <option value="">Todas as classificações</option>
                <option value="super_premium">Super Premium</option>
                <option value="premium">Premium</option>
                <option value="especial">Especial</option>
                <option value="standard">Standard</option>
              </select>
              {form.classificacao && (
                <button
                  type="button"
                  onClick={() => setForm({ ...form, classificacao: "" })}
                  className="btn-clear"
                  title="Limpar filtro"
                >
                  ✕
                </button>
              )}
            </div>
            {form.produto_comparar_id && (
              <small className="form-warning">
                ⚠️ Limpe a ração específica acima para usar este filtro
              </small>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="racao-especie">Espécie</label>
            <select
              id="racao-especie"
              name="racao_especie"
              value={form.especies}
              onChange={(e) => setForm({ ...form, especies: e.target.value })}
            >
              <option value="dog">🐶 Cães</option>
              <option value="cat">🐱 Gatos</option>
              <option value="both">Ambos</option>
            </select>
          </div>

          <div className="button-group">
            <button
              onClick={compararRacoes}
              disabled={loading}
              className="btn-secondary"
            >
              {loading ? "Comparando..." : "🔍 Comparar Todas"}
            </button>
          </div>
        </div>

        <div>
          {/* Resultado Individual */}
          {resultado && (
            <div className="result-card">
              <h2>📊 Resultado do Cálculo</h2>
              <div className="result-header">
                <h3>{resultado.produto_nome}</h3>
                {resultado.classificacao && (
                  <span className={`badge badge-${resultado.classificacao}`}>
                    {resultado.classificacao.replace("_", " ")}
                  </span>
                )}
              </div>

              <div className="result-stats">
                <div className="stat">
                  <span className="label">Peso Embalagem</span>
                  <span className="value">
                    {resultado.peso_embalagem_kg} kg
                  </span>
                </div>
                <div className="stat">
                  <span className="label">Preço</span>
                  <span className="value">R$ {resultado.preco.toFixed(2)}</span>
                </div>
              </div>

              <div className="result-details">
                <div className="detail-item">
                  <span className="icon">⏱️</span>
                  <div>
                    <strong>Duração</strong>
                    <p>
                      {resultado.duracao_dias} dias ({resultado.duracao_meses}{" "}
                      meses)
                    </p>
                  </div>
                </div>
                <div className="detail-item">
                  <span className="icon">🥫</span>
                  <div>
                    <strong>Consumo diário</strong>
                    <p>{resultado.quantidade_diaria_g}g</p>
                  </div>
                </div>
                <div className="detail-item">
                  <span className="icon">💰</span>
                  <div>
                    <strong>Custo/kg</strong>
                    <p>R$ {resultado.custo_por_kg.toFixed(2)}</p>
                  </div>
                </div>
                <div className="detail-item">
                  <span className="icon">📅</span>
                  <div>
                    <strong>Custo/dia</strong>
                    <p>R$ {resultado.custo_por_dia.toFixed(2)}</p>
                  </div>
                </div>
                <div className="detail-item">
                  <span className="icon">📆</span>
                  <div>
                    <strong>Custo mensal</strong>
                    <p>R$ {resultado.custo_mensal.toFixed(2)}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Comparativo - LOGO ABAIXO DO RESULTADO */}
          {comparativo.length > 0 && (
            <div className="comparativo-card">
              <h2>🏆 Comparativo de Rações ({comparativo.length})</h2>
              <p className="subtitle">
                Ordenado por melhor custo-benefício (menor custo diário)
              </p>

              <div className="comparativo-list">
                {(() => {
                  // Encontrar menor custo diário
                  const menorCusto = Math.min(
                    ...comparativo.map((r) => r.custo_por_dia),
                  );

                  return comparativo.map((item, index) => {
                    // ⭐ Ração BASE (do campo "Selecionar Ração")
                    const isSelecionada =
                      form.produto_id &&
                      item.produto_id === parseInt(form.produto_id);
                    // 🏆 Melhor custo-benefício
                    const isMelhor = item.custo_por_dia === menorCusto;

                    return (
                      <div
                        key={item.produto_id}
                        className={`comparativo-item ${isMelhor ? "melhor" : ""} ${isSelecionada ? "selecionada" : ""}`}
                      >
                        {(isSelecionada || isMelhor) && (
                          <div className="comparativo-badges">
                            {isSelecionada && (
                              <span className="badge-selecionada">
                                ⭐ Selecionada
                              </span>
                            )}
                            {isMelhor && (
                              <span className="badge-melhor">
                                🏆 Melhor Custo-Benefício
                              </span>
                            )}
                          </div>
                        )}

                        <div className="item-header">
                          <div>
                            <h4>{item.produto_nome}</h4>
                            <div
                              style={{
                                display: "flex",
                                gap: "8px",
                                alignItems: "center",
                                marginTop: "4px",
                              }}
                            >
                              {item.classificacao && (
                                <span
                                  className={`badge badge-${item.classificacao}`}
                                >
                                  {item.classificacao.replace("_", " ")}
                                </span>
                              )}
                              <span
                                style={{
                                  fontSize: "13px",
                                  color: "#64748b",
                                  backgroundColor: "#f1f5f9",
                                  padding: "2px 8px",
                                  borderRadius: "4px",
                                }}
                              >
                                🍽️ {item.quantidade_diaria_g}g/dia
                              </span>
                            </div>
                          </div>
                          <div className="item-price">
                            R$ {item.preco.toFixed(2)}
                          </div>
                        </div>

                        <div className="item-stats">
                          <div className="stat-small">
                            <span className="label">Peso</span>
                            <span>{item.peso_embalagem_kg}kg</span>
                          </div>
                          <div className="stat-small">
                            <span className="label">Duração</span>
                            <span>{item.duracao_dias}d</span>
                          </div>
                          <div className="stat-small highlight">
                            <span className="label">Custo/dia</span>
                            <span>R$ {item.custo_por_dia.toFixed(2)}</span>
                          </div>
                          <div className="stat-small">
                            <span className="label">Custo/mês</span>
                            <span>R$ {item.custo_mensal.toFixed(2)}</span>
                          </div>
                        </div>

                        {/* Explicação detalhada para o melhor */}
                        {isMelhor && comparativo.length > 1 && (
                          <div
                            style={{
                              marginTop: "12px",
                              padding: "12px",
                              backgroundColor: "#ecfdf5",
                              borderLeft: "3px solid #10b981",
                              borderRadius: "4px",
                            }}
                          >
                            <p
                              style={{
                                margin: "0 0 6px 0",
                                fontSize: "13px",
                                fontWeight: "600",
                                color: "#065f46",
                              }}
                            >
                              ✨ Por que esta é a melhor opção?
                            </p>
                            <p
                              style={{
                                margin: "0",
                                fontSize: "13px",
                                color: "#047857",
                                lineHeight: "1.5",
                              }}
                            >
                              Apesar de{" "}
                              {item.classificacao === "premium" ||
                              item.classificacao === "super_premium"
                                ? `ter um preço mais alto (R$ ${item.preco.toFixed(2)})`
                                : `custar R$ ${item.preco.toFixed(2)}`}
                              , esta ração{" "}
                              {item.classificacao === "super_premium"
                                ? "super premium é muito concentrada em nutrientes"
                                : item.classificacao === "premium"
                                  ? "premium tem melhor densidade nutricional"
                                  : "tem excelente eficiência alimentar"}
                              , então seu pet consome apenas{" "}
                              <strong>
                                {item.quantidade_diaria_g}g por dia
                              </strong>
                              .
                              {comparativo[1] && (
                                <>
                                  {" "}
                                  Em comparação, a segunda opção requer{" "}
                                  <strong>
                                    {comparativo[1].quantidade_diaria_g}g/dia
                                  </strong>
                                  , resultando em um custo diário{" "}
                                  <strong>
                                    R${" "}
                                    {(
                                      comparativo[1].custo_por_dia -
                                      item.custo_por_dia
                                    ).toFixed(2)}{" "}
                                    maior
                                  </strong>
                                  (R$ {item.custo_por_dia.toFixed(2)} vs R${" "}
                                  {comparativo[1].custo_por_dia.toFixed(2)}).
                                </>
                              )}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
