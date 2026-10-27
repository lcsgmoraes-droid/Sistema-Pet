import { useEffect, useRef, useState } from "react";
import { normalizarBusca, ordenarSugestoesEntidade } from "../../../utils/buscaEntidades";

// Adaptador interno de campos que ja recebem um catalogo restrito por permissao
// ou regra operacional. A celula visual continua BuscaPessoa/BuscaProduto.
export default function useBuscaEntidadeLocal({ itens = [], valueId, onChangeId, tipo }) {
  const selecionado = itens.find((item) => String(item.id) === String(valueId));
  const nomeSelecionado = selecionado?.nome || selecionado?.produto_nome || "";
  const [termo, setTermo] = useState(nomeSelecionado);
  const digitando = useRef(false);
  useEffect(() => {
    if (!digitando.current) setTermo(nomeSelecionado);
    digitando.current = false;
  }, [valueId, nomeSelecionado]);

  const palavras = normalizarBusca(termo).split(" ").filter(Boolean);
  const filtrados = itens.filter((item) => {
    const texto = normalizarBusca(
      [
        item.nome,
        item.produto_nome,
        item.codigo,
        item.sku,
        item.codigo_barras,
        item.cpf,
        item.cnpj,
        item.telefone,
        item.celular,
      ]
        .filter(Boolean)
        .join(" "),
    );
    return palavras.every((palavra) => texto.includes(palavra));
  });
  return {
    value: termo,
    onChange: (valor) => {
      setTermo(valor);
      if (valueId) {
        digitando.current = true;
        onChangeId("");
      }
    },
    suggestions: ordenarSugestoesEntidade(filtrados, termo, tipo).slice(0, 40),
    showSuggestions: !valueId,
    onSelect: (item) => {
      digitando.current = false;
      setTermo(item.nome || item.produto_nome || "");
      onChangeId(String(item.id));
    },
  };
}
