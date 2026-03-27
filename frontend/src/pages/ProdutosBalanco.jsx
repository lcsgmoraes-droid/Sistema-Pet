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
  const [paginaAtual, setPaginaAtual] = useState(1);
  const itensPorPagina = 20;
  const [totalItensServidor, setTotalItensServidor] = useState(0);
  const [totalPaginasServidor, setTotalPaginasServidor] = useState(1);
  const [filtros, setFiltros] = useState({
    busca: "",
    marca_id: "",
    fornecedor_id: "",
  });

  const inputRefs = useRef({});

  const produtosPaginados = produtos;
  const totalItens = totalItensServidor;
  const totalPaginas = Math.max(totalPaginasServidor, 1);
  const inicioItem = totalItens === 0 ? 0 : (paginaAtual - 1) * itensPorPagina + 1;
  const fimItem = totalItens === 0 ? 0 : Math.min(paginaAtual * itensPorPagina, totalItens);

  useEffect(() => {
    carregarDadosComFiltros(filtros, paginaAtual);
  }, [paginaAtual]);

  const carregarDadosComFiltros = async (filtrosAtuais, pagina = 1) => {
    try {
      setCarregando(true);
      const params = {
        page: pagina,
        page_size: itensPorPagina,
        include_variations: false,
      };

      if (filtrosAtuais.busca) params.busca = filtrosAtuais.busca;

      if (filtrosAtuais.marca_id) params.marca_id = filtrosAtuais.marca_id;
      if (filtrosAtuais.fornecedor_id) params.fornecedor_id = filtrosAtuais.fornecedor_id;

      const [prodRes, marcasRes, cliRes] = await Promise.all([
        getProdutos(params),
        getMarcas(),
        api.get("/clientes/", {
          params: { tipo_cadastro: "fornecedor", apenas_ativos: true, page_size: 1000 },
        }),
      ]);

      const items = prodRes.data?.items || [];
      const total = prodRes.data?.total || items.length;
      const pages = prodRes.data?.pages || 1;

      setProdutos(items);
      setTotalItensServidor(total);
      setTotalPaginasServidor(Math.max(pages, 1));
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
    setPaginaAtual(1);
    await carregarDadosComFiltros(filtros, 1);
  };

  const registrarDestaque = (produtoId, tipo) => {
    setDestacados((prev) => ({
      ...prev,
      [produtoId]: { tipo, timestamp: Date.now() },
    }));
  };

  const proximoProdutoId = (produtoId) => {
    const idx = produtosPaginados.findIndex((p) => p.id === produtoId);
    if (idx < 0 || idx + 1 >= produtosPaginados.length) return null;
    return produtosPaginados[idx + 1].id;
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
      const numeroLote = String(inputs?.[produto.id]?.lote || "").trim();
      const dataValidade = String(inputs?.[produto.id]?.validade || "").trim();

      if (campo === "entrada") {
        await api.post("/estoque/entrada", {
          produto_id: produto.id,
          quantidade: qtd,
          motivo: "balanco",
          observacao: "Lançamento rápido pela tela de Balanço",
          numero_lote: numeroLote || undefined,
          data_validade: dataValidade || undefined,
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
        const payload = {
          produto_id: produto.id,
          quantidade: Math.abs(diferenca),
          motivo: "balanco",
          observacao: `Balanço rápido: estoque ajustado para ${qtd}`,
        };

        if (diferenca > 0) {
          payload.numero_lote = numeroLote || undefined;
          payload.data_validade = dataValidade || undefined;
        }

        await api.post(endpoint, payload);

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
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                aplicarFiltrosServidor();
              }
            }}
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

      <div className="flex items-center justify-between text-sm text-gray-500 px-1">
        <span>
          Mostrando {inicioItem} a {fimItem} de {totalItens} produtos
        </span>
        <span>20 por página</span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-auto">
        <table className="w-full min-w-[1300px]">
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
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lote</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validade</th>
            </tr>
          </thead>
          <tbody>
            {produtosPaginados.map((produto) => {
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

                  <td className="px-3 py-3">
                    <input
                      ref={(el) => {
                        inputRefs.current[`${produto.id}-lote`] = el;
                      }}
                      type="text"
                      value={inputs?.[produto.id]?.lote ?? ""}
                      onChange={(e) => atualizarInput(produto.id, "lote", e.target.value)}
                      placeholder="Ex: LOTE-001"
                      disabled={Boolean(submetendo[produto.id])}
                      className="w-40 border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                    />
                  </td>

                  <td className="px-3 py-3">
                    <input
                      ref={(el) => {
                        inputRefs.current[`${produto.id}-validade`] = el;
                      }}
                      type="date"
                      value={inputs?.[produto.id]?.validade ?? ""}
                      onChange={(e) => atualizarInput(produto.id, "validade", e.target.value)}
                      disabled={Boolean(submetendo[produto.id])}
                      className="w-40 border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                    />
                  </td>
                </tr>
              );
            })}

            {produtosPaginados.length === 0 && (
              <tr>
                <td colSpan={10} className="px-3 py-8 text-center text-sm text-gray-500">
                  Nenhum produto encontrado com os filtros atuais.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => setPaginaAtual((prev) => Math.max(1, prev - 1))}
          disabled={paginaAtual <= 1}
          className="px-3 py-2 rounded-lg border border-gray-300 bg-white text-sm text-gray-700 disabled:opacity-50"
        >
          Anterior
        </button>
        <span className="text-sm text-gray-500">
          Página {Math.min(paginaAtual, totalPaginas)} de {totalPaginas}
        </span>
        <button
          type="button"
          onClick={() => setPaginaAtual((prev) => Math.min(totalPaginas, prev + 1))}
          disabled={paginaAtual >= totalPaginas}
          className="px-3 py-2 rounded-lg border border-gray-300 bg-white text-sm text-gray-700 disabled:opacity-50"
        >
          Próxima
        </button>
      </div>
    </div>
  );
}
