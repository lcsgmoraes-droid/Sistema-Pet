import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { ChevronDown, Settings, X } from "lucide-react";
import api from "../../api";
import { formatPercent } from "../../utils/formatters";
import {
  MARGENS_PRECO_PADRAO,
  formatarDivisorMargem,
  normalizarMargensPreco,
} from "../../utils/produtoMargem";

const converterMargem = (valor) => Number(String(valor).replace(",", "."));

export default function MargemPrecoField({
  camposEmEdicao,
  formData,
  handleChange,
  setCamposEmEdicao,
}) {
  const [margensSugeridas, setMargensSugeridas] = useState(MARGENS_PRECO_PADRAO);
  const [editorAberto, setEditorAberto] = useState(false);
  const [sugestoesAbertas, setSugestoesAbertas] = useState(false);
  const [margensEmEdicao, setMargensEmEdicao] = useState(MARGENS_PRECO_PADRAO.map(String));
  const [salvando, setSalvando] = useState(false);
  const sugestoesRef = useRef(null);

  useEffect(() => {
    let ativo = true;

    api
      .get("/empresa/config/margens-preco")
      .then(({ data }) => {
        if (ativo) setMargensSugeridas(normalizarMargensPreco(data));
      })
      .catch((error) => {
        console.error("Erro ao carregar margens sugeridas:", error);
      });

    return () => {
      ativo = false;
    };
  }, []);

  useEffect(() => {
    if (!sugestoesAbertas) return undefined;

    const fecharAoClicarFora = (event) => {
      if (!sugestoesRef.current?.contains(event.target)) {
        setSugestoesAbertas(false);
      }
    };

    document.addEventListener("mousedown", fecharAoClicarFora);
    return () => document.removeEventListener("mousedown", fecharAoClicarFora);
  }, [sugestoesAbertas]);

  const abrirEditor = () => {
    setMargensEmEdicao(margensSugeridas.map((margem) => String(margem).replace(".", ",")));
    setEditorAberto(true);
  };

  const salvarMargensSugeridas = async () => {
    const novasMargens = margensEmEdicao.map(converterMargem);
    const margensInvalidas = novasMargens.some(
      (margem) => !Number.isFinite(margem) || margem < 0 || margem >= 100,
    );

    if (margensInvalidas) {
      toast.error("Informe duas margens entre 0% e 99,99%.");
      return;
    }

    if (novasMargens[0] === novasMargens[1]) {
      toast.error("As duas sugestões precisam ser diferentes.");
      return;
    }

    try {
      setSalvando(true);
      const { data } = await api.put("/empresa/config/margens-preco", {
        margem_preco_sugestao_1: novasMargens[0],
        margem_preco_sugestao_2: novasMargens[1],
      });
      setMargensSugeridas(normalizarMargensPreco(data));
      setEditorAberto(false);
      toast.success("Sugestões de margem atualizadas.");
    } catch (error) {
      console.error("Erro ao salvar margens sugeridas:", error);
      toast.error(error?.response?.data?.detail || "Não foi possível salvar as sugestões.");
    } finally {
      setSalvando(false);
    }
  };

  const finalizarEdicaoMargem = (valorDigitado) => {
    setCamposEmEdicao((prev) => ({ ...prev, margem: false }));
    const margemTexto = String(valorDigitado ?? "").trim();
    if (!margemTexto || margemTexto === "-") {
      handleChange("margem", "");
      return;
    }

    const margem = converterMargem(margemTexto);

    if (!Number.isFinite(margem) || margem >= 100) {
      toast.error("A margem precisa ser menor que 100%.");
      handleChange("margem", "");
      return;
    }

    handleChange("margem", margem.toFixed(2));
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">Margem sobre a venda</label>
      <div className="flex gap-2">
        <input
          type="text"
          inputMode="decimal"
          value={camposEmEdicao.margem ? formData.margem || "" : formatPercent(formData.margem)}
          onChange={(e) => {
            const value = e.target.value.replace(/[^\d.,-]/g, "").replace(",", ".");
            handleChange("margem", value);
          }}
          onFocus={(e) => {
            setCamposEmEdicao((prev) => ({ ...prev, margem: true }));
            e.target.select();
          }}
          onBlur={(e) => finalizarEdicaoMargem(e.target.value)}
          className="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
          placeholder="0,00%"
          aria-label="Margem sobre o preço de venda"
        />

        <div ref={sugestoesRef} className="relative shrink-0">
          <button
            type="button"
            onClick={() => setSugestoesAbertas((aberto) => !aberto)}
            className="inline-flex h-[42px] w-[42px] items-center justify-center rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 hover:text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            title="Abrir margens sugeridas"
            aria-label="Abrir margens sugeridas"
            aria-expanded={sugestoesAbertas}
          >
            <ChevronDown size={18} />
          </button>

          {sugestoesAbertas && (
            <div className="absolute right-0 z-20 mt-2 w-52 overflow-hidden rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
              {margensSugeridas.map((margem, indice) => (
                <button
                  key={`${margem}-${indice}`}
                  type="button"
                  onClick={() => {
                    handleChange("margem", Number(margem).toFixed(2));
                    setSugestoesAbertas(false);
                  }}
                  className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700"
                >
                  <span>{formatPercent(margem)}</span>
                  <span className="text-xs text-gray-500">
                    divisor {formatarDivisorMargem(margem)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={abrirEditor}
          className="inline-flex h-[42px] w-[42px] shrink-0 items-center justify-center rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 hover:text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
          title="Editar as duas margens sugeridas"
          aria-label="Editar as duas margens sugeridas"
        >
          <Settings size={18} />
        </button>
      </div>
      <p className="mt-1 text-xs text-gray-500">Preço = custo ÷ (1 − margem).</p>

      {editorAberto && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="titulo-margens-sugeridas"
        >
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="titulo-margens-sugeridas" className="text-lg font-semibold text-gray-900">
                  Margens sugeridas
                </h2>
                <p className="mt-1 text-sm text-gray-600">
                  Estas opções ficarão disponíveis no cadastro de produtos da empresa.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setEditorAberto(false)}
                className="rounded-lg p-1 text-gray-500 hover:bg-gray-100"
                aria-label="Fechar edição de margens"
              >
                <X size={20} />
              </button>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
              {margensEmEdicao.map((margem, indice) => (
                <div key={indice}>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Sugestão {indice + 1} (%)
                  </label>
                  <input
                    type="text"
                    inputMode="decimal"
                    value={margem}
                    onChange={(e) => {
                      const atualizadas = [...margensEmEdicao];
                      atualizadas[indice] = e.target.value.replace(/[^\d,.]/g, "");
                      setMargensEmEdicao(atualizadas);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        salvarMargensSugeridas();
                      }
                    }}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setEditorAberto(false)}
                disabled={salvando}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={salvarMargensSugeridas}
                disabled={salvando}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {salvando ? "Salvando..." : "Salvar sugestões"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
