import { useState } from "react";
import { X } from "lucide-react";
import CurrencyInput from "../CurrencyInput";
import {
  compararPrecosEtiquetaBalanca,
  produtoAceitaEtiquetaBalanca,
} from "../../utils/pdvEtiquetaBalanca";
import { formatMoneyBRL } from "../../utils/formatters";
import { useEscapeToClose } from "../../utils/modalEscape";
import { obterPrecoVendaPDV } from "../../utils/pdvCarrinhoItensUtils";

export default function PDVEtiquetaBalancaModal({ pendencia, onConfirmar, onCancelar }) {
  const [precoEtiqueta, setPrecoEtiqueta] = useState(0);
  const [pesoImpresso, setPesoImpresso] = useState("");
  const { etiqueta: codigoLido, opcoes } = pendencia;
  const exigirEscolha = opcoes.length > 1 || opcoes[0].etiqueta.formato !== "produto6_valor5";
  const [indiceOpcao, setIndiceOpcao] = useState(exigirEscolha ? null : 0);
  const opcao = indiceOpcao === null ? null : opcoes[indiceOpcao];
  const etiqueta = opcao?.etiqueta;
  const produto = opcao?.produto;
  const precoSistema = produto ? obterPrecoVendaPDV(produto) : null;
  const comparacao =
    produto && precoEtiqueta > 0
      ? compararPrecosEtiquetaBalanca(etiqueta, produto, precoEtiqueta, pesoImpresso)
      : null;
  const pesoValido = comparacao && !comparacao.erro;
  const totalEtiqueta = etiqueta ? etiqueta.totalCentavos / 100 : null;

  useEscapeToClose({ onClose: onCancelar });

  const confirmar = (usarPrecoEtiqueta) => {
    if (!pesoValido || (!usarPrecoEtiqueta && comparacao.precoKgSistema === null)) return;
    onConfirmar(
      {
        codigo: etiqueta.codigo,
        quantidade: comparacao.quantidade,
        precoUnitario: usarPrecoEtiqueta ? comparacao.precoKgEtiqueta : comparacao.precoKgSistema,
        subtotal: usarPrecoEtiqueta ? comparacao.totalEtiqueta : comparacao.totalSistema,
      },
      indiceOpcao,
    );
  };

  if (!opcao) {
    return (
      <div
        className="fixed inset-0 z-[70] flex items-center justify-center bg-black/55 p-4"
        role="presentation"
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="titulo-etiqueta-balanca"
          className="max-h-[95vh] w-full max-w-xl overflow-y-auto rounded-xl bg-white p-6 shadow-2xl"
        >
          <h2 id="titulo-etiqueta-balanca" className="text-xl font-bold text-gray-900">
            Conferir produto da etiqueta
          </h2>
          <p className="mt-2 text-sm text-gray-700">
            O código {codigoLido.codigo} admite mais de uma divisão entre produto e valor. Confira o
            nome impresso na etiqueta antes de escolher.
          </p>
          <div className="mt-4 space-y-2">
            {opcoes.map(({ etiqueta: leitura, produto: candidato }, indice) => (
              <button
                key={`${leitura.formato}-${candidato.id}`}
                type="button"
                disabled={!produtoAceitaEtiquetaBalanca(candidato)}
                onClick={() => setIndiceOpcao(indice)}
                className="w-full rounded-lg border border-gray-300 p-4 text-left hover:border-blue-500 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <strong className="block text-gray-900">{candidato.nome}</strong>
                <span className="text-sm text-gray-700">
                  Código cadastrado: {candidato.codigo} · Total:{" "}
                  {formatMoneyBRL(leitura.totalCentavos / 100)}
                </span>
                {!produtoAceitaEtiquetaBalanca(candidato) && (
                  <span className="block text-xs text-red-700">
                    Produto não cadastrado como granel em KG
                  </span>
                )}
              </button>
            ))}
          </div>
          <div className="mt-5 flex justify-end">
            <button
              type="button"
              onClick={onCancelar}
              className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/55 p-4"
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-etiqueta-balanca"
        className="max-h-[95vh] w-full max-w-xl overflow-y-auto rounded-xl bg-white shadow-2xl"
      >
        <div className="flex items-start justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 id="titulo-etiqueta-balanca" className="text-xl font-bold text-gray-900">
              Conferir etiqueta da balança
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              {produto.nome} · código {etiqueta.codigoProdutoSemZeros}
            </p>
          </div>
          <button
            type="button"
            onClick={onCancelar}
            aria-label="Cancelar etiqueta"
            className="rounded p-1 text-gray-500 hover:bg-gray-100"
          >
            <X size={22} />
          </button>
        </div>

        <div className="space-y-4 p-6">
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
            <div className="flex justify-between gap-3">
              <span>Total codificado na etiqueta</span>
              <strong>{formatMoneyBRL(totalEtiqueta)}</strong>
            </div>
            <p className="mt-2 text-xs">
              O código de barras informa o produto e o total. Confira o preço por kg impresso para
              calcular o peso.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="preco-kg-etiqueta"
                className="mb-1 block text-sm font-medium text-gray-800"
              >
                Preço por kg na etiqueta (R$)
              </label>
              <CurrencyInput
                id="preco-kg-etiqueta"
                value={precoEtiqueta}
                onChange={setPrecoEtiqueta}
                autoFocus
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-lg focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <span className="mb-1 block text-sm font-medium text-gray-800">
                Preço por kg no sistema
              </span>
              <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-lg">
                {precoSistema > 0 ? formatMoneyBRL(precoSistema) : "Indisponível"}
              </div>
            </div>
          </div>

          {comparacao?.erro && (
            <p role="alert" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
              {comparacao.erro}
            </p>
          )}
          {precoEtiqueta > 0 && (
            <div>
              <label
                htmlFor="peso-kg-etiqueta"
                className="mb-1 block text-sm font-medium text-gray-800"
              >
                Peso na etiqueta, em kg (se solicitado)
              </label>
              <input
                id="peso-kg-etiqueta"
                type="text"
                inputMode="decimal"
                placeholder="Ex.: 0,310"
                value={pesoImpresso}
                onChange={(event) => setPesoImpresso(event.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
              />
            </div>
          )}

          {pesoValido && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm">
              <p className="font-semibold text-gray-900">
                Peso:{" "}
                {comparacao.quantidade.toLocaleString("pt-BR", {
                  minimumFractionDigits: 3,
                  maximumFractionDigits: 3,
                })}{" "}
                kg
              </p>
              {comparacao.precoKgSistema !== comparacao.precoKgEtiqueta && (
                <p className="mt-2 text-amber-800">
                  Os preços por kg são diferentes. Escolha qual valor será cobrado.
                </p>
              )}
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <div className="rounded border border-gray-200 bg-white p-3">
                  Etiqueta: <strong>{formatMoneyBRL(comparacao.precoKgEtiqueta)}/kg</strong>
                  <br />
                  Total: <strong>{formatMoneyBRL(comparacao.totalEtiqueta)}</strong>
                </div>
                <div className="rounded border border-gray-200 bg-white p-3">
                  Sistema:{" "}
                  <strong>
                    {comparacao.precoKgSistema === null
                      ? "Indisponível"
                      : `${formatMoneyBRL(comparacao.precoKgSistema)}/kg`}
                  </strong>
                  <br />
                  Total:{" "}
                  <strong>
                    {comparacao.totalSistema === null
                      ? "Indisponível"
                      : formatMoneyBRL(comparacao.totalSistema)}
                  </strong>
                </div>
              </div>
            </div>
          )}

          <div className="flex flex-wrap justify-end gap-2 border-t border-gray-200 pt-4">
            {exigirEscolha && (
              <button
                type="button"
                onClick={() => {
                  setPrecoEtiqueta(0);
                  setPesoImpresso("");
                  setIndiceOpcao(null);
                }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50"
              >
                Trocar produto
              </button>
            )}
            <button
              type="button"
              onClick={onCancelar}
              className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={() => confirmar(false)}
              disabled={!pesoValido || comparacao.precoKgSistema === null}
              className="rounded-lg border border-blue-600 px-4 py-2 font-semibold text-blue-700 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Usar preço do sistema
            </button>
            <button
              type="button"
              onClick={() => confirmar(true)}
              disabled={!pesoValido}
              className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Usar preço da etiqueta
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
