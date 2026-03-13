import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import { getMarcas, getProdutos } from "../api/produtos";

const parseNumeroBR = (valor) => {
  if (valor === null || valor === undefined) return Number.NaN;
  const texto = String(valor).trim();
  if (!texto) return Number.NaN;
  return Number.parseFloat(texto.replaceAll(".", "").replace(",", "."));
};

const formatQtd = (valor) => {
  const numero = Number(valor || 0);
  return numero.toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
};

const normalizeSearchText = (value) => {
  if (value === null || value === undefined) return "";
  return String(value)
    .toLowerCase()
    .normalize("NFD")
    .replaceAll(/[\u0300-\u036f]/g, "");
};

export default function ProdutosBalanco() {
  const [produtos, setProdutos] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [fornecedores, setFornecedores] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [submetendo, setSubmetendo] = useState({});
  const [inputs, setInputs] = useState({});
  const [destacados, setDestacados] = useState({});
  const [filtros, setFiltros] = useState({
    busca: "",
    marca_id: "",
    fornecedor_id: "",
  });

  const inputRefs = useRef({});

  const produtosOrdenados = useMemo(() => {
    const termo = normalizeSearchText(filtros.busca);
    if (!termo) return produtos;

    const termos = termo
      .split(" ")
      .map((item) => item.trim())
      .filter(Boolean);

    return produtos.filter((p) => {
      const base = [p.nome, p.codigo, p.codigo_barras, p.marca?.nome]
        .map((item) => normalizeSearchText(item))
        .join(" ");
      return termos.every((t) => base.includes(t));
    });
  }, [produtos, filtros.busca]);

  useEffect(() => {
    carregarDadosComFiltros(filtros);
  }, []);

  useEffect(() => {
    carregarDadosComFiltros(filtros);
  }, [filtros.marca_id, filtros.fornecedor_id]);

  const carregarDadosComFiltros = async (filtrosAtuais) => {
    try {
      setCarregando(true);
      const params = {
        page: 1,
        page_size: 1000,
        include_variations: false,
      };

      if (filtrosAtuais.marca_id) params.marca_id = filtrosAtuais.marca_id;
      if (filtrosAtuais.fornecedor_id) params.fornecedor_id = filtrosAtuais.fornecedor_id;

      const [prodRes, marcasRes, cliRes] = await Promise.all([
        getProdutos(params),
        getMarcas(),
        api.get("/clientes/", {
          params: { tipo_cadastro: "fornecedor", apenas_ativos: true, page_size: 1000 },
        }),
      ]);

      setProdutos(prodRes.data?.items || []);
      setMarcas(marcasRes.data || []);
      setFornecedores(Array.isArray(cliRes.data) ? cliRes.data : (cliRes.data?.items || []));
    } catch (error) {
      console.error("Erro ao carregar balanço:", error);
      toast.error("Erro ao carregar produtos para balanço.");
    } finally {
      setCarregando(false);
    }
  };

  const atualizarFiltro = (campo, valor) => {
    setFiltros((prev) => ({ ...prev, [campo]: valor }));
  };

  const aplicarFiltrosServidor = async () => {
    setDestacados({});
    await carregarDadosComFiltros(filtros);
  };

  const registrarDestaque = (produtoId, tipo) => {
    setDestacados((prev) => ({
      ...prev,
      [produtoId]: { tipo, timestamp: Date.now() },
    }));
  };

  const proximoProdutoId = (produtoId) => {
    const idx = produtosOrdenados.findIndex((p) => p.id === produtoId);
    if (idx < 0 || idx + 1 >= produtosOrdenados.length) return null;
    return produtosOrdenados[idx + 1].id;
  };

  const focarProximoCampo = (produtoId, campo) => {
    const prox = proximoProdutoId(produtoId);
    if (!prox) return;
    const ref = inputRefs.current[`${prox}-${campo}`];
    if (ref) {
      ref.focus();
      ref.select();
    }
  };

  const limparLinhaInputs = (produtoId) => {
    setInputs((prev) => {
      const novo = { ...prev };
      delete novo[produtoId];
      return novo;
    });
  };

  const atualizarEstoqueLocal = (produtoId, novoEstoque) => {
    setProdutos((prev) =>
      prev.map((p) => (p.id === produtoId ? { ...p, estoque_atual: novoEstoque } : p)),
    );
  };

  const registrarMovimento = async (produto, campo, valor) => {
    const qtd = parseNumeroBR(valor);
    if (!Number.isFinite(qtd) || qtd < 0) {
      toast.error("Informe um número válido.");
      return false;
    }

    if (campo !== "balanco" && qtd === 0) {
      toast.error("A quantidade deve ser maior que zero.");
      return false;
    }

    setSubmetendo((prev) => ({ ...prev, [produto.id]: campo }));

    try {
      const estoqueAtual = Number(produto.estoque_atual || 0);

      if (campo === "entrada") {
        await api.post("/estoque/entrada", {
          produto_id: produto.id,
          quantidade: qtd,
          motivo: "balanco",
          observacao: "Lançamento rápido pela tela de Balanço",
        });
        atualizarEstoqueLocal(produto.id, estoqueAtual + qtd);
      }

      if (campo === "saida") {
        if (qtd > estoqueAtual) {
          toast.error("Saída maior que o estoque atual.");
          return false;
        }
        await api.post("/estoque/saida", {
          produto_id: produto.id,
          quantidade: qtd,
          motivo: "balanco",
          observacao: "Lançamento rápido pela tela de Balanço",
        });
        atualizarEstoqueLocal(produto.id, estoqueAtual - qtd);
      }

      if (campo === "balanco") {
        const diferenca = qtd - estoqueAtual;
        if (Math.abs(diferenca) < 0.0001) {
          toast("Sem alteração: estoque já está nesse valor.", { icon: "ℹ️" });
          limparLinhaInputs(produto.id);
          return true;
        }

        const endpoint = diferenca > 0 ? "/estoque/entrada" : "/estoque/saida";
        await api.post(endpoint, {
          produto_id: produto.id,
          quantidade: Math.abs(diferenca),
          motivo: "balanco",
          observacao: `Balanço rápido: estoque ajustado para ${qtd}`,
        });

        atualizarEstoqueLocal(produto.id, qtd);
      }

      registrarDestaque(produto.id, campo);
      limparLinhaInputs(produto.id);
      toast.success("Lançamento registrado com origem Balanço.");
      return true;
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Erro ao registrar lançamento.");
      return false;
    } finally {
      setSubmetendo((prev) => {
        const novo = { ...prev };
        delete novo[produto.id];
        return novo;
      });
    }
  };

  const onInputKeyDown = async (event, produto, campo) => {
    if (event.key !== "Enter" && event.key !== "Tab") return;
    event.preventDefault();

    const valor = inputs?.[produto.id]?.[campo] ?? "";
    if (!String(valor).trim()) {
      focarProximoCampo(produto.id, campo);
      return;
    }

    const ok = await registrarMovimento(produto, campo, valor);
    if (ok) {
      focarProximoCampo(produto.id, campo);
    }
  };

  const atualizarInput = (produtoId, campo, valor) => {
    setInputs((prev) => ({
      ...prev,
      [produtoId]: {
        ...prev[produtoId],
        [campo]: valor,
      },
    }));
  };

  if (carregando) {
    return (
      <div className="p-6">
        <div className="text-gray-500">Carregando tela de balanço...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Balanço de Estoque</h1>
        <p className="text-sm text-blue-800 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2 mt-2 inline-block leading-relaxed">
          Nesta tela, digite os valores em Entrada, Saída ou Balanço e pressione{" "}
          <span className="mx-1 inline-flex items-center rounded-md border border-blue-300 bg-white px-2 py-0.5 text-xs font-semibold text-blue-700 align-middle">
            TAB
          </span>{" "}
          para lançar automaticamente e ir para o próximo produto. O destaque verde mostra os itens já lançados e permanece na tela até você clicar em Atualizar lista.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input
            type="text"
            value={filtros.busca}
            onChange={(e) => atualizarFiltro("busca", e.target.value)}
            placeholder="Buscar por nome, código, código de barras..."
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />

          <select
            value={filtros.marca_id}
            onChange={(e) => atualizarFiltro("marca_id", e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">Todas as marcas</option>
            {marcas.map((marca) => (
              <option key={marca.id} value={marca.id}>
                {marca.nome}
              </option>
            ))}
          </select>

          <select
            value={filtros.fornecedor_id}
            onChange={(e) => atualizarFiltro("fornecedor_id", e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">Todos os fornecedores</option>
            {fornecedores.map((fornecedor) => (
              <option key={fornecedor.id} value={fornecedor.id}>
                {fornecedor.nome}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={aplicarFiltrosServidor}
            className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-3 py-2 text-sm font-medium"
          >
            Atualizar lista
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-auto">
        <table className="w-full min-w-[1100px]">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Imagem</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Descrição</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Código</th>
              <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">Unidade</th>
              <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">Estoque Atual</th>
              <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">Entrada</th>
              <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">Saída</th>
              <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">Balanço</th>
            </tr>
          </thead>
          <tbody>
            {produtosOrdenados.map((produto) => {
              const destaque = destacados[produto.id];
              const corDestaque = destaque
                ? "bg-emerald-50 border-l-4 border-emerald-500"
                : "";

              return (
                <tr key={produto.id} className={`border-b border-gray-100 ${corDestaque}`}>
                  <td className="px-3 py-3">
                    <div className="w-10 h-10 rounded bg-gray-100 overflow-hidden border border-gray-200 flex items-center justify-center">
                      {produto.imagem_principal ? (
                        <img
                          src={
                            produto.imagem_principal.startsWith("http")
                              ? produto.imagem_principal
                              : `${globalThis.location.origin}${produto.imagem_principal}`
                          }
                          alt={produto.nome}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <span className="text-xs text-gray-400">IMG</span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    <div className="text-sm font-medium text-gray-900">{produto.nome}</div>
                    <div className="text-xs text-gray-500">{produto.marca?.nome || "Sem marca"}</div>
                  </td>
                  <td className="px-3 py-3">
                    <div className="text-sm text-gray-900 font-mono">{produto.codigo || "-"}</div>
                    <div className="text-xs text-gray-500 font-mono">{produto.codigo_barras || "-"}</div>
                  </td>
                  <td className="px-3 py-3 text-center text-sm text-gray-700">{produto.unidade || "UN"}</td>
                  <td className="px-3 py-3 text-right text-sm font-semibold text-gray-900">{formatQtd(produto.estoque_atual)}</td>
                  {[
                    { campo: "entrada", placeholder: "0" },
                    { campo: "saida", placeholder: "0" },
                    { campo: "balanco", placeholder: "Novo estoque" },
                  ].map((coluna) => (
                    <td key={coluna.campo} className="px-3 py-3 text-right">
                      <input
                        ref={(el) => {
                          inputRefs.current[`${produto.id}-${coluna.campo}`] = el;
                        }}
                        type="text"
                        inputMode="decimal"
                        value={inputs?.[produto.id]?.[coluna.campo] ?? ""}
                        onChange={(e) => atualizarInput(produto.id, coluna.campo, e.target.value)}
                        onKeyDown={(e) => onInputKeyDown(e, produto, coluna.campo)}
                        placeholder={coluna.placeholder}
                        disabled={Boolean(submetendo[produto.id])}
                        className="w-28 border border-gray-300 rounded-lg px-2 py-1.5 text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-300"
                      />
                    </td>
                  ))}
                </tr>
              );
            })}

            {produtosOrdenados.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-sm text-gray-500">
                  Nenhum produto encontrado com os filtros atuais.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
