import { useEffect, useState } from "react";
import { X } from "lucide-react";
import toast from "react-hot-toast";
import { createProduto, gerarSKU } from "../../api/produtos";
import { calcularMargemSobreVenda, calcularPrecoVendaPorMargem } from "../../utils/produtoMargem";
import CurrencyInput from "../CurrencyInput";

const campoClasses =
  "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500";

function mensagemErro(error) {
  const detalhe = error?.response?.data?.detail;
  if (typeof detalhe === "string") return detalhe;
  if (Array.isArray(detalhe))
    return detalhe
      .map((item) => item.msg)
      .filter(Boolean)
      .join("; ");
  return "Não foi possível cadastrar o produto. Tente novamente.";
}

export default function PDVProdutoRapidoModal({ onClose, onCreated }) {
  const [codigo, setCodigo] = useState("");
  const [nome, setNome] = useState("");
  const [custo, setCusto] = useState(null);
  const [margem, setMargem] = useState("");
  const [precoVenda, setPrecoVenda] = useState(0);
  const [ean, setEan] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [gerandoSku, setGerandoSku] = useState(false);

  useEffect(() => {
    const fecharComEscape = (event) => {
      if (event.key === "Escape" && !salvando) onClose();
    };
    document.addEventListener("keydown", fecharComEscape);
    return () => document.removeEventListener("keydown", fecharComEscape);
  }, [onClose, salvando]);

  function atualizarCusto(valor) {
    const novoCusto = valor > 0 ? valor : null;
    setCusto(novoCusto);
    const novaMargem =
      novoCusto && precoVenda > 0 ? calcularMargemSobreVenda(novoCusto, precoVenda) : null;
    setMargem(novaMargem === null ? "" : novaMargem.toFixed(2).replace(".", ","));
  }

  function atualizarPrecoVenda(valor) {
    setPrecoVenda(valor);
    const novaMargem = custo && valor > 0 ? calcularMargemSobreVenda(custo, valor) : null;
    setMargem(novaMargem === null ? "" : novaMargem.toFixed(2).replace(".", ","));
  }

  function atualizarMargem(valor) {
    const texto = valor.replace(/[^\d,.-]/g, "");
    setMargem(texto);
    const percentual = Number(texto.replace(",", "."));
    if (!texto || !Number.isFinite(percentual) || percentual >= 100 || !custo) return;
    const precoCalculado = calcularPrecoVendaPorMargem(custo, percentual);
    if (precoCalculado !== null) setPrecoVenda(Math.round(precoCalculado * 100) / 100);
  }

  async function handleGerarSKU() {
    if (gerandoSku || salvando) return;
    try {
      setGerandoSku(true);
      const { data } = await gerarSKU("PROD");
      setCodigo(data.sku);
      toast.success("SKU gerado com sucesso.");
    } catch (error) {
      console.error("Erro ao gerar SKU:", error);
      toast.error("Não foi possível gerar o SKU. Tente novamente.");
    } finally {
      setGerandoSku(false);
    }
  }

  async function salvar(event) {
    event.preventDefault();
    if (salvando || gerandoSku) return;

    const codigoLimpo = codigo.trim().toUpperCase();
    const nomeLimpo = nome.trim();
    const eanLimpo = ean.trim();
    if (!codigoLimpo || !nomeLimpo || precoVenda <= 0) {
      toast.error("Informe código, descrição e preço de venda maior que zero.");
      return;
    }
    if (eanLimpo && !/^\d{8,14}$/.test(eanLimpo)) {
      toast.error("O EAN deve ter de 8 a 14 dígitos.");
      return;
    }
    if (custo && margem) {
      const percentual = Number(margem.replace(",", "."));
      if (!Number.isFinite(percentual) || percentual >= 100) {
        toast.error("A margem deve ser menor que 100%.");
        return;
      }
    }

    let produtoCriado;
    try {
      setSalvando(true);
      const { data } = await createProduto({
        codigo: codigoLimpo,
        nome: nomeLimpo,
        preco_venda: precoVenda,
        anunciar_ecommerce: false,
        anunciar_app: false,
        ...(custo ? { preco_custo: custo } : {}),
        ...(eanLimpo ? { codigo_barras: eanLimpo, gtin_ean: eanLimpo } : {}),
      });
      produtoCriado = data;
    } catch (error) {
      toast.error(mensagemErro(error));
    } finally {
      setSalvando(false);
    }

    if (!produtoCriado) return;
    onClose();
    try {
      onCreated(produtoCriado);
      toast.success("Produto cadastrado.");
    } catch {
      toast("Produto cadastrado. Busque-o pelo código para adicionar à venda.");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="presentation"
    >
      <form
        onSubmit={salvar}
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-produto-rapido"
        className="w-full max-w-lg space-y-4 rounded-xl bg-white p-5 shadow-xl sm:p-6"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="titulo-produto-rapido" className="text-lg font-semibold text-gray-900">
              Novo produto
            </h2>
            <p className="mt-1 text-sm text-gray-500">Cadastro rápido para usar no PDV.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={salvando}
            aria-label="Fechar cadastro"
            className="rounded-lg p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-50"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="pdv-produto-sku" className="block text-sm font-medium text-gray-700">
              Código (SKU) *
            </label>
            <div className="mt-1 flex gap-2">
              <input
                id="pdv-produto-sku"
                className={`${campoClasses} min-w-0 flex-1`}
                value={codigo}
                onChange={(event) => setCodigo(event.target.value)}
                maxLength={50}
                autoFocus
                required
              />
              <button
                type="button"
                onClick={handleGerarSKU}
                disabled={gerandoSku || salvando}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                {gerandoSku ? "Gerando..." : "Gerar"}
              </button>
            </div>
          </div>
          <label className="block text-sm font-medium text-gray-700">
            EAN (opcional)
            <input
              className={`${campoClasses} mt-1`}
              value={ean}
              onChange={(event) => setEan(event.target.value.replace(/\D/g, ""))}
              inputMode="numeric"
              maxLength={14}
              placeholder="Código de barras"
            />
          </label>
        </div>

        <label className="block text-sm font-medium text-gray-700">
          Descrição *
          <input
            className={`${campoClasses} mt-1`}
            value={nome}
            onChange={(event) => setNome(event.target.value)}
            maxLength={200}
            required
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-3">
          <label className="block text-sm font-medium text-gray-700">
            Custo (opcional)
            <CurrencyInput
              className={`${campoClasses} mt-1`}
              value={custo}
              onChange={atualizarCusto}
              aria-label="Custo em reais"
            />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Margem (%)
            <input
              className={`${campoClasses} mt-1 disabled:bg-gray-50`}
              value={margem}
              onChange={(event) => atualizarMargem(event.target.value)}
              onBlur={() => {
                const percentual = Number(margem.replace(",", "."));
                if (margem && Number.isFinite(percentual) && percentual < 100)
                  setMargem(percentual.toFixed(2).replace(".", ","));
              }}
              inputMode="decimal"
              disabled={!custo}
              placeholder="—"
              aria-label="Margem sobre o preço de venda"
            />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Preço de venda *
            <CurrencyInput
              className={`${campoClasses} mt-1`}
              value={precoVenda}
              onChange={atualizarPrecoVenda}
              aria-label="Preço de venda em reais"
            />
          </label>
        </div>
        <p className="text-xs text-gray-500">
          {custo
            ? "Margem sobre a venda: preço = custo ÷ (1 − margem)."
            : "Informe o custo para calcular a margem; ele pode ficar vazio."}
        </p>
        <p className="text-xs text-amber-700">
          O produto começa sem estoque. Se a loja bloqueia estoque negativo, registre uma entrada
          antes de concluir a venda.
        </p>

        <div className="flex justify-end gap-2 border-t border-gray-100 pt-4">
          <button
            type="button"
            onClick={onClose}
            disabled={salvando}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={salvando || gerandoSku}
            className="rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
          >
            {salvando ? "Salvando..." : "Cadastrar produto"}
          </button>
        </div>
      </form>
    </div>
  );
}
