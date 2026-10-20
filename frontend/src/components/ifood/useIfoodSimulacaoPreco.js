import { useEffect, useRef, useState } from "react";
import { simularPrecoIfoodProduto } from "../../api/ifood";
import { updateProduto } from "../../api/produtos";
import { mensagemErroIfood } from "./ifoodPresentation";

function precoEspecifico(item) {
  return item.saved_specific_price === null || item.saved_specific_price === undefined
    ? null
    : Number(item.saved_specific_price);
}

export default function useIfoodSimulacaoPreco(item, { podeEditar, onAplicado }) {
  const [salvo, setSalvo] = useState(item);
  const [modo, setModo] = useState(() =>
    precoEspecifico(item) === null ? "regra_loja" : "especifico",
  );
  const [valor, setValor] = useState(() => precoEspecifico(item) ?? item.regular_price ?? 0);
  const [consulta, setConsulta] = useState({
    chave: null,
    situacao: "carregando",
    resultado: null,
    erro: "",
  });
  const [revisao, setRevisao] = useState(0);
  const [salvando, setSalvando] = useState(false);
  const [erroSalvar, setErroSalvar] = useState("");
  const [sucesso, setSucesso] = useState("");
  const travaSalvar = useRef(false);
  const preco = modo === "especifico" ? valor : null;
  const chave = `${item.product_id}:${preco === null ? "regra_loja" : preco}`;
  // A chave muda no mesmo render da digitacao: nunca habilitar aplicar com
  // resultado do preco anterior, nem mesmo durante o debounce.
  const pronta = consulta.chave === chave && consulta.situacao === "pronta";
  const alterado = preco !== precoEspecifico(salvo);

  useEffect(() => {
    let ativo = true;
    const abort = new AbortController();
    setConsulta({ chave, situacao: "carregando", resultado: null, erro: "" });
    const timer = window.setTimeout(async () => {
      try {
        const response = await simularPrecoIfoodProduto(
          { product_id: item.product_id, preco_ifood: preco },
          { signal: abort.signal },
        );
        if (ativo) setConsulta({ chave, situacao: "pronta", resultado: response.data, erro: "" });
      } catch (error) {
        if (ativo)
          setConsulta({
            chave,
            situacao: "erro",
            resultado: null,
            erro: mensagemErroIfood(error, "Não foi possível simular este preço. Tente novamente."),
          });
      }
    }, 350);
    return () => {
      ativo = false;
      abort.abort();
      window.clearTimeout(timer);
    };
  }, [item.product_id, preco, chave, revisao]);

  function alterarModo(novoModo) {
    setModo(novoModo);
    setErroSalvar("");
    setSucesso("");
  }

  function alterarValor(novoValor) {
    setValor(novoValor);
    setErroSalvar("");
    setSucesso("");
  }

  function restaurar() {
    setModo(precoEspecifico(salvo) === null ? "regra_loja" : "especifico");
    setValor(precoEspecifico(salvo) ?? salvo.regular_price ?? 0);
    setErroSalvar("");
    setSucesso("");
    setRevisao((atual) => atual + 1);
  }

  async function aplicar() {
    if (!podeEditar || !alterado || !pronta || travaSalvar.current) return;
    travaSalvar.current = true;
    setSalvando(true);
    setErroSalvar("");
    setSucesso("");
    const resultadoAplicado = { ...consulta.resultado, saved_specific_price: preco };
    try {
      // Usa a mesma persistencia do cadastro. A simulacao nao altera produto,
      // custo, promocao, selecao ou pausa: somente esta acao salva o preco.
      await updateProduto(item.product_id, { preco_ifood: preco });
      setSalvo(resultadoAplicado);
      setConsulta({ chave, situacao: "pronta", resultado: resultadoAplicado, erro: "" });
      setSucesso(
        "Preço aplicado ao cadastro do produto. A central e o cadastro usam o mesmo valor.",
      );
      onAplicado?.(resultadoAplicado);
    } catch (error) {
      setErroSalvar(mensagemErroIfood(error, "Não foi possível aplicar o preço ao produto."));
    } finally {
      travaSalvar.current = false;
      setSalvando(false);
    }
  }

  return {
    salvo,
    modo,
    valor,
    alterado,
    pronta,
    salvando,
    erroSalvar,
    sucesso,
    resultado: pronta ? consulta.resultado : null,
    erroSimulacao: consulta.chave === chave && consulta.situacao === "erro" ? consulta.erro : "",
    alterarModo,
    alterarValor,
    restaurar,
    aplicar,
    repetir: () => setRevisao((atual) => atual + 1),
  };
}
