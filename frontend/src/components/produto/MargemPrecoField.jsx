import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Settings } from "lucide-react";
import api from "../../api";
import { formatPercent } from "../../utils/formatters";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoLink from "../v2/BotaoLink/BotaoLink";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputTexto from "../v2/InputTexto/InputTexto";
import InputPercentual from "../v2/InputPercentual/InputPercentual";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";
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
  const [margensEmEdicao, setMargensEmEdicao] = useState(MARGENS_PRECO_PADRAO);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    let ativo = true;
    api
      .get("/empresa/config/margens-preco")
      .then(({ data }) => {
        if (ativo) setMargensSugeridas(normalizarMargensPreco(data));
      })
      .catch((error) => console.error("Erro ao carregar margens sugeridas:", error));
    return () => {
      ativo = false;
    };
  }, []);

  const salvarMargensSugeridas = async () => {
    const novasMargens = margensEmEdicao.map(converterMargem);
    if (novasMargens.some((margem) => !Number.isFinite(margem) || margem < 0 || margem >= 100)) {
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
      <div className="flex items-end gap-2">
        <InputTexto
          id="produto-margem"
          label="Margem sobre a venda"
          inputMode="decimal"
          value={camposEmEdicao.margem ? formData.margem || "" : formatPercent(formData.margem)}
          onChange={(value) =>
            handleChange("margem", value.replace(/[^\d.,-]/g, "").replace(",", "."))
          }
          onFocus={(event) => {
            setCamposEmEdicao((prev) => ({ ...prev, margem: true }));
            event.target.select();
          }}
          onBlur={(event) => finalizarEdicaoMargem(event.target.value)}
          placeholder="0,00%"
        />
        <BotaoInteracao
          icon={Settings}
          aria-label="Editar as duas margens sugeridas"
          title="Editar as duas margens sugeridas"
          onClick={() => {
            setMargensEmEdicao([...margensSugeridas]);
            setEditorAberto(true);
          }}
        />
      </div>
      <p className="v2-texto-ajuda mt-1">Preço = custo ÷ (1 − margem).</p>
      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
        {margensSugeridas.map((margem, indice) => (
          <BotaoLink
            key={`${margem}-${indice}`}
            title={`Aplicar margem; divisor ${formatarDivisorMargem(margem)}`}
            onClick={() => handleChange("margem", Number(margem).toFixed(2))}
          >
            Usar {formatPercent(margem)}
          </BotaoLink>
        ))}
      </div>
      {editorAberto ? (
        <ModalPadrao
          titulo="Margens sugeridas"
          tamanho="pequena"
          onFechar={() => {
            if (!salvando) setEditorAberto(false);
          }}
          rodape={
            <>
              <BotaoCancelar onClick={() => setEditorAberto(false)} disabled={salvando} />
              <BotaoSalva type="button" onClick={salvarMargensSugeridas} loading={salvando}>
                Salvar sugestões
              </BotaoSalva>
            </>
          }
        >
          <p className="v2-texto-ajuda mb-4">
            Estas opções ficam disponíveis no cadastro de produtos da empresa.
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {margensEmEdicao.map((margem, indice) => (
              <InputPercentual
                key={indice}
                label={`Sugestão ${indice + 1}`}
                value={margem}
                maxValue={99.99}
                onChange={(value) =>
                  setMargensEmEdicao((atuais) =>
                    atuais.map((atual, index) => (index === indice ? value : atual)),
                  )
                }
              />
            ))}
          </div>
        </ModalPadrao>
      ) : null}
    </div>
  );
}
