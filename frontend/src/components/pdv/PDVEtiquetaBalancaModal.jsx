import { useState } from "react";
import { X } from "lucide-react";
import CurrencyInput from "../CurrencyInput";
import { compararPrecosEtiquetaBalanca } from "../../utils/pdvEtiquetaBalanca";
import { formatMoneyBRL } from "../../utils/formatters";
import { useEscapeToClose } from "../../utils/modalEscape";
import { obterPrecoVendaPDV } from "../../utils/pdvCarrinhoItensUtils";

export default function PDVEtiquetaBalancaModal({
  pendencia,
  onConfirmar,
  onCancelar,
  podeEditarPreco,
}) {
  const [precoEtiqueta, setPrecoEtiqueta] = useState(0);
  const [pesoImpresso, setPesoImpresso] = useState("");
  const [perguntarAtualizacao, setPerguntarAtualizacao] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erroSalvar, setErroSalvar] = useState("");
  const { etiqueta, produto } = pendencia;
  const precoSistema = obterPrecoVendaPDV(produto);
  const comparacao =
    precoEtiqueta > 0
      ? compararPrecosEtiquetaBalanca(etiqueta, produto, precoEtiqueta, pesoImpresso)
      : null;
  const pesoValido = comparacao && !comparacao.erro;
  const precosDiferentes = pesoValido && comparacao.precoKgSistema !== comparacao.precoKgEtiqueta;
  const totalEtiqueta = etiqueta.totalCentavos / 100;

  useEscapeToClose({ onClose: onCancelar, disabled: salvando });

  const confirmar = async (usarPrecoEtiqueta, atualizarCadastro = false) => {
    if (!pesoValido || salvando || (!usarPrecoEtiqueta && comparacao.precoKgSistema === null))
      return;
    setSalvando(true);
    setErroSalvar("");
    try {
      const adicionou = await onConfirmar(
        {
          codigo: etiqueta.codigo,
          quantidade: comparacao.quantidade,
          precoUnitario: usarPrecoEtiqueta ? comparacao.precoKgEtiqueta : comparacao.precoKgSistema,
          subtotal: usarPrecoEtiqueta ? comparacao.totalEtiqueta : comparacao.totalSistema,
        },
        { atualizarCadastro },
      );
      if (!adicionou) {
        setErroSalvar(
          atualizarCadastro
            ? "O item não foi adicionado à venda. O cadastro pode já ter sido atualizado; confira antes de tentar novamente."
            : "Não foi possível adicionar o produto à venda.",
        );
      }
    } catch (error) {
      const detalhe = error?.response?.data?.detail;
      setErroSalvar(
        typeof detalhe === "string"
          ? `O item não foi adicionado. ${detalhe}`
          : `O item não foi adicionado. ${error?.message || "Não foi possível atualizar o cadastro. Tente novamente ou use apenas nesta venda."}`,
      );
    } finally {
      setSalvando(false);
    }
  };

  const escolherPrecoEtiqueta = () => {
    if (!pesoValido || salvando) return;
    if (precosDiferentes) {
      setPerguntarAtualizacao(true);
      setErroSalvar("");
    } else {
      void confirmar(true);
    }
  };

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
            disabled={salvando}
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
                disabled={perguntarAtualizacao || salvando}
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
                disabled={perguntarAtualizacao || salvando}
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
              {precosDiferentes && (
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

          {perguntarAtualizacao && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <p className="font-semibold">Corrigir também o preço no cadastro?</p>
              <p className="mt-1">
                O preço padrão deste produto passará de {formatMoneyBRL(comparacao.precoKgSistema)}{" "}
                para {formatMoneyBRL(comparacao.precoKgEtiqueta)}/kg nas próximas vendas. Outros
                canais que usam o preço padrão também podem ser afetados.
              </p>
              {produto.promocao_pdv_ativa && (
                <p className="mt-2 font-medium">
                  Há uma promoção ativa. Ajuste o preço promocional no cadastro; esta venda pode
                  seguir com o preço da etiqueta.
                </p>
              )}
              {!podeEditarPreco && !produto.promocao_pdv_ativa && (
                <p className="mt-2 font-medium">
                  Sua conta não tem permissão para editar produtos. Esta venda pode seguir com o
                  preço da etiqueta.
                </p>
              )}
            </div>
          )}

          {erroSalvar && (
            <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {erroSalvar}
            </p>
          )}

          <div className="flex flex-wrap justify-end gap-2 border-t border-gray-200 pt-4">
            {perguntarAtualizacao ? (
              <>
                <button
                  type="button"
                  onClick={() => {
                    setPerguntarAtualizacao(false);
                    setErroSalvar("");
                  }}
                  disabled={salvando}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Voltar
                </button>
                <button
                  type="button"
                  onClick={() => void confirmar(true)}
                  disabled={salvando}
                  className="rounded-lg border border-blue-600 px-4 py-2 font-semibold text-blue-700 hover:bg-blue-50 disabled:opacity-50"
                >
                  Só nesta venda
                </button>
                {!produto.promocao_pdv_ativa && podeEditarPreco && (
                  <button
                    type="button"
                    onClick={() => void confirmar(true, true)}
                    disabled={salvando}
                    className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {salvando ? "Atualizando..." : "Atualizar cadastro e adicionar"}
                  </button>
                )}
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={onCancelar}
                  disabled={salvando}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={() => void confirmar(false)}
                  disabled={!pesoValido || comparacao.precoKgSistema === null || salvando}
                  className="rounded-lg border border-blue-600 px-4 py-2 font-semibold text-blue-700 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Usar preço do sistema
                </button>
                <button
                  type="button"
                  onClick={escolherPrecoEtiqueta}
                  disabled={!pesoValido || salvando}
                  className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Usar preço da etiqueta
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
