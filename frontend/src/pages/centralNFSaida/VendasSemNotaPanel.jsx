import { useEffect, useState } from "react";
import api from "../../api";
import { confirmarCorePet } from "../../services/corepetDialog";
import { formatMoneyBRL } from "../../utils/formatters";
import { emitirNotaFiscalAssistida, extrairMensagemNFe } from "../../utils/nfeFiscalAssistida";
import {
  selecionarPaginaCompativel,
  vendaCompativelNfeNfce,
  vendasSelecionadasParaEmissao,
} from "./vendasSemNotaUtils";

function dataLocal(date) {
  const ano = date.getFullYear();
  const mes = String(date.getMonth() + 1).padStart(2, "0");
  const dia = String(date.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

export default function VendasSemNotaPanel({ onEmissaoConcluida }) {
  const hoje = new Date();
  const [dataInicial, setDataInicial] = useState(
    dataLocal(new Date(hoje.getFullYear(), hoje.getMonth(), 1)),
  );
  const [dataFinal, setDataFinal] = useState(dataLocal(hoje));
  const [filtros, setFiltros] = useState({ dataInicial, dataFinal });
  const [tipoNota, setTipoNota] = useState("nfce");
  const [pagina, setPagina] = useState(1);
  const [versao, setVersao] = useState(0);
  const [vendas, setVendas] = useState([]);
  const [total, setTotal] = useState(0);
  const [selecionados, setSelecionados] = useState(new Set());
  const [carregando, setCarregando] = useState(false);
  const [emitindo, setEmitindo] = useState(false);
  const [progresso, setProgresso] = useState("");
  const [erro, setErro] = useState("");
  const [resultados, setResultados] = useState([]);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setErro("");
    api
      .get("/nfe/vendas-sem-nota", {
        params: {
          data_inicial: filtros.dataInicial,
          data_final: filtros.dataFinal,
          pagina,
          por_pagina: 20,
        },
      })
      .then(({ data }) => {
        if (!ativo) return;
        if (pagina > 1 && (pagina - 1) * 20 >= (data.total || 0)) {
          setPagina(Math.max(1, Math.ceil((data.total || 0) / 20)));
          return;
        }
        setVendas(data.vendas || []);
        setTotal(data.total || 0);
        setSelecionados(new Set());
      })
      .catch((error) => {
        if (ativo) {
          setErro(extrairMensagemNFe(error));
          setVendas([]);
          setTotal(0);
          setSelecionados(new Set());
        }
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [filtros, pagina, versao]);

  const pesquisar = (event) => {
    event.preventDefault();
    if (!dataInicial || !dataFinal || dataFinal < dataInicial) {
      setErro("Informe um período válido.");
      return;
    }
    setPagina(1);
    setFiltros({ dataInicial, dataFinal });
    setVersao((atual) => atual + 1);
  };

  const alternarVenda = (id) => {
    if (!vendas.some((venda) => venda.id === id && vendaCompativelNfeNfce(venda))) return;
    setSelecionados((atual) => {
      const proximo = new Set(atual);
      if (proximo.has(id)) proximo.delete(id);
      else proximo.add(id);
      return proximo;
    });
  };

  const vendasCompativeis = vendas.filter(vendaCompativelNfeNfce);
  const todasSelecionadas =
    vendasCompativeis.length > 0 && vendasCompativeis.every((venda) => selecionados.has(venda.id));
  const alternarPagina = () => {
    setSelecionados((atual) => selecionarPaginaCompativel(vendas, atual));
  };

  const emitirSelecionadas = async () => {
    const lote = vendasSelecionadasParaEmissao(vendas, selecionados);
    if (!lote.length) return;
    const modelo = tipoNota === "nfe" ? "NF-e" : "NFC-e";
    const confirmado = await confirmarCorePet(
      `Emitir ${modelo} para ${lote.length} venda(s) selecionada(s)? Cada nota será transmitida ao ambiente fiscal configurado.`,
    );
    if (!confirmado) return;

    setEmitindo(true);
    setResultados([]);
    const concluidos = [];
    try {
      for (const [indice, venda] of lote.entries()) {
        setProgresso(`Emitindo ${indice + 1} de ${lote.length}: ${venda.numero_venda}`);
        try {
          const resposta = await emitirNotaFiscalAssistida({
            vendaId: venda.id,
            tipoNota,
            semInteracao: true,
          });
          const situacao =
            resposta.data?.processando || resposta.data?.transmissao?.success === false
              ? "Em processamento; confira em NF de Saída antes de tentar novamente."
              : "Autorizada";
          concluidos.push({ id: venda.id, numero: venda.numero_venda, situacao, sucesso: true });
        } catch (error) {
          concluidos.push({
            id: venda.id,
            numero: venda.numero_venda,
            situacao: extrairMensagemNFe(error),
            sucesso: false,
          });
        }
        setResultados([...concluidos]);
      }
    } finally {
      setEmitindo(false);
      setProgresso("");
      setSelecionados(new Set());
      setVersao((atual) => atual + 1);
      if (concluidos.some((resultado) => resultado.sucesso)) onEmissaoConcluida?.();
    }
  };

  return (
    <section
      className="mb-6 rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
      aria-label="Vendas sem nota fiscal"
    >
      <h2 className="text-lg font-semibold text-gray-800">Vendas sem nota fiscal</h2>
      <p className="mt-1 text-sm text-gray-600">
        Vendas finalizadas sem tentativa de emissão. Notas rejeitadas ou em processamento são
        tratadas na lista de notas abaixo. Vendas com serviços ficam visíveis para revisão e não
        podem ser selecionadas neste fluxo de NF-e/NFC-e.
      </p>

      <form onSubmit={pesquisar} className="mt-4 flex flex-wrap items-end gap-3">
        <label className="text-sm text-gray-700">
          De
          <input
            type="date"
            value={dataInicial}
            onChange={(event) => setDataInicial(event.target.value)}
            disabled={emitindo}
            className="mt-1 block rounded border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="text-sm text-gray-700">
          Até
          <input
            type="date"
            value={dataFinal}
            onChange={(event) => setDataFinal(event.target.value)}
            disabled={emitindo}
            className="mt-1 block rounded border border-gray-300 px-3 py-2"
          />
        </label>
        <button
          type="submit"
          disabled={emitindo || carregando}
          className="rounded bg-gray-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Filtrar
        </button>
        <label className="text-sm text-gray-700">
          Emitir como
          <select
            value={tipoNota}
            onChange={(event) => setTipoNota(event.target.value)}
            disabled={emitindo}
            className="mt-1 block rounded border border-gray-300 px-3 py-2"
          >
            <option value="nfce">NFC-e</option>
            <option value="nfe">NF-e</option>
          </select>
        </label>
        <button
          type="button"
          onClick={emitirSelecionadas}
          disabled={emitindo || carregando || selecionados.size === 0}
          className="rounded bg-purple-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Emitir selecionadas ({selecionados.size})
        </button>
      </form>

      {erro && (
        <p className="mt-3 text-sm text-red-700" role="alert">
          {erro}
        </p>
      )}
      {progresso && (
        <p className="mt-3 text-sm text-blue-700" role="status">
          {progresso}
        </p>
      )}
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b bg-gray-50 text-gray-700">
            <tr>
              <th className="px-3 py-2">
                <input
                  type="checkbox"
                  aria-label="Selecionar vendas desta página"
                  checked={todasSelecionadas}
                  onChange={alternarPagina}
                  disabled={emitindo || carregando || !vendasCompativeis.length}
                />
              </th>
              <th className="px-3 py-2">Venda</th>
              <th className="px-3 py-2">Data</th>
              <th className="px-3 py-2">Cliente</th>
              <th className="px-3 py-2">Emissão NF-e/NFC-e</th>
              <th className="px-3 py-2 text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {!carregando &&
              vendas.map((venda) => (
                <tr key={venda.id} className="border-b">
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      aria-label={`Selecionar venda ${venda.numero_venda}`}
                      checked={selecionados.has(venda.id)}
                      onChange={() => alternarVenda(venda.id)}
                      disabled={emitindo || !vendaCompativelNfeNfce(venda)}
                    />
                  </td>
                  <td className="px-3 py-2">{venda.numero_venda}</td>
                  <td className="px-3 py-2">
                    {new Date(venda.data_venda).toLocaleString("pt-BR")}
                  </td>
                  <td className="px-3 py-2">{venda.cliente_nome || "Consumidor"}</td>
                  <td className="max-w-sm px-3 py-2">
                    {vendaCompativelNfeNfce(venda) ? (
                      <span className="text-gray-600">
                        Dados fiscais serão conferidos na emissão.
                      </span>
                    ) : (
                      <span className="text-amber-800">
                        {venda.bloqueios_modelo?.map((bloqueio) => bloqueio.mensagem).join(" ") ||
                          "Composição da venda precisa de revisão antes de emitir NF-e/NFC-e."}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right">{formatMoneyBRL(venda.total)}</td>
                </tr>
              ))}
            {!carregando && !vendas.length && (
              <tr>
                <td colSpan="6" className="px-3 py-5 text-center text-gray-500">
                  Nenhuma venda sem nota neste período.
                </td>
              </tr>
            )}
            {carregando && (
              <tr>
                <td colSpan="6" className="px-3 py-5 text-center text-gray-500">
                  Carregando vendas...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center justify-between text-sm text-gray-600">
        <span>
          {total} venda(s) sem nota · página {pagina}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setPagina((atual) => atual - 1)}
            disabled={emitindo || carregando || pagina === 1}
            className="rounded border px-3 py-1 disabled:opacity-50"
          >
            Anterior
          </button>
          <button
            type="button"
            onClick={() => setPagina((atual) => atual + 1)}
            disabled={emitindo || carregando || pagina * 20 >= total}
            className="rounded border px-3 py-1 disabled:opacity-50"
          >
            Próxima
          </button>
        </div>
      </div>

      {resultados.length > 0 && (
        <div className="mt-4 rounded border border-gray-200 p-3" role="status">
          <h3 className="font-medium text-gray-800">Resultado da emissão</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {resultados.map((resultado) => (
              <li
                key={resultado.id}
                className={resultado.sucesso ? "text-green-800" : "text-red-700"}
              >
                {resultado.numero}: {resultado.situacao}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
