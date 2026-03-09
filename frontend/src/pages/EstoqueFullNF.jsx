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

export default function EstoqueFullNF() {
  const [numeroNF, setNumeroNF] = useState("");
  const [plataforma, setPlataforma] = useState("mercado_livre");
  const [observacao, setObservacao] = useState("");
  const [itens, setItens] = useState([criarLinha()]);

  const [tarifaEnvio, setTarifaEnvio] = useState(0);
  const [dataVencimentoTarifa, setDataVencimentoTarifa] = useState("");
  const [categoriaTarifaId, setCategoriaTarifaId] = useState("");
  const [categoriasDespesa, setCategoriasDespesa] = useState([]);

  const [resultado, setResultado] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [arquivoXml, setArquivoXml] = useState(null);
  const [lendoXml, setLendoXml] = useState(false);

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

  const atualizarLinha = (linhaId, campo, valor) => {
    setItens((prev) =>
      prev.map((item) => (item.id === linhaId ? { ...item, [campo]: valor } : item)),
    );
  };

  const adicionarLinha = () => {
    setItens((prev) => [...prev, criarLinha()]);
  };

  const removerLinha = (linhaId) => {
    setItens((prev) => (prev.length > 1 ? prev.filter((item) => item.id !== linhaId) : prev));
  };

  const limparFormulario = () => {
    setItens([criarLinha()]);
    setObservacao("");
    setResultado(null);
    setArquivoXml(null);
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
      toast.success(`XML lido com sucesso: NF ${numeroNfXml} com ${linhas.length} item(ns)`);
    } catch (error) {
      console.error("Erro ao ler XML FULL NF:", error);
      const detalhe = error?.response?.data?.detail || "Erro ao ler XML";
      toast.error(detalhe);
    } finally {
      setLendoXml(false);
    }
  };

  const registrarTarifaEnvio = async () => {
    if (!tarifaEnvio || tarifaEnvio <= 0) return;

    await api.post("/contas-pagar/", {
      descricao: `Tarifa envio FULL NF ${numeroNF}`,
      categoria_id: categoriaTarifaId ? Number(categoriaTarifaId) : null,
      dre_subcategoria_id: 2,
      canal: "loja_fisica",
      valor_original: Number(tarifaEnvio),
      data_emissao: hojeISO,
      data_vencimento: dataVencimentoTarifa || hojeISO,
      documento: numeroNF,
      observacoes: `Tarifa da operacao FULL (${plataforma}). Gerado na baixa de estoque por NF.`,
    });
  };

  const processar = async () => {
    if (!numeroNF.trim()) {
      toast.error("Informe o numero da NF");
      return;
    }

    const itensValidos = itens
      .map((item) => ({
        sku: item.sku.trim(),
        quantidade: toNumber(item.quantidade),
      }))
      .filter((item) => item.sku && item.quantidade > 0);

    if (!itensValidos.length) {
      toast.error("Informe ao menos um item com SKU e quantidade");
      return;
    }

    try {
      setSalvando(true);
      setResultado(null);

      const payload = {
        numero_nf: numeroNF.trim(),
        plataforma,
        observacao: observacao.trim() || null,
        itens: itensValidos,
      };

      const response = await api.post("/estoque/saida-full-nf", payload);

      await registrarTarifaEnvio();

      setResultado(response.data);
      toast.success("Baixa de estoque por NF concluida");
      if (tarifaEnvio > 0) {
        toast.success("Tarifa de envio lancada em Contas a Pagar");
      }

      limparFormulario();
    } catch (error) {
      console.error("Erro ao processar FULL por NF:", error);
      const detalhe = error?.response?.data?.detail || "Erro ao processar baixa por NF";
      toast.error(detalhe);
    } finally {
      setSalvando(false);
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
            <div className="block text-sm font-medium text-gray-700 mb-1">Plataforma</div>
            <select
              id="plataforma-full"
              aria-label="Plataforma"
              value={plataforma}
              onChange={(e) => setPlataforma(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="mercado_livre">Mercado Livre</option>
              <option value="shopee">Shopee</option>
              <option value="amazon">Amazon</option>
              <option value="full">FULL (geral)</option>
            </select>
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

        <div className="space-y-2">
          {itens.map((item) => (
            <div key={item.id} className="grid grid-cols-1 md:grid-cols-12 gap-2">
              <div className="md:col-span-7">
                <input
                  id={`sku-${item.id}`}
                  aria-label={`SKU ${item.id}`}
                  type="text"
                  value={item.sku}
                  onChange={(e) => atualizarLinha(item.id, "sku", e.target.value)}
                  placeholder="SKU do produto"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
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
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                />
              </div>
              <div className="md:col-span-2">
                <button
                  type="button"
                  onClick={() => removerLinha(item.id)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
                >
                  Remover
                </button>
              </div>
            </div>
          ))}
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
            <div className="block text-sm font-medium text-gray-700 mb-1">Categoria de despesa (opcional)</div>
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
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={processar}
          disabled={salvando}
          className="px-5 py-2.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60"
        >
          {salvando ? "Processando..." : "Confirmar baixa por NF"}
        </button>
      </div>

      {resultado && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 md:p-5">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Resumo processado</h3>
          <p className="text-sm text-gray-700 mb-3">
            NF {resultado.numero_nf} | Itens processados: {resultado.total_itens}
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-600 border-b">
                  <th className="py-2">SKU</th>
                  <th className="py-2">Produto</th>
                  <th className="py-2">Qtd</th>
                  <th className="py-2">Antes</th>
                  <th className="py-2">Depois</th>
                </tr>
              </thead>
              <tbody>
                {(resultado.itens || []).map((item) => (
                  <tr key={`${item.produto_id}-${item.sku}`} className="border-b last:border-0">
                    <td className="py-2">{item.sku || "-"}</td>
                    <td className="py-2">{item.nome}</td>
                    <td className="py-2">{item.quantidade}</td>
                    <td className="py-2">{item.estoque_anterior}</td>
                    <td className="py-2">{item.estoque_novo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {tarifaEnvio > 0 && (
            <p className="text-sm text-gray-700 mt-3">
              Tarifa registrada: <strong>{formatMoneyBRL(tarifaEnvio)}</strong>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
