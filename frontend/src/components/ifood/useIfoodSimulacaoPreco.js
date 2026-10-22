import { useEffect, useRef, useState } from "react";
import { getIfoodCatalogo, simularPrecoIfoodProduto } from "../../api/ifood";
import { updateProduto } from "../../api/produtos";
import useIfoodPromotionRefresh from "../../hooks/useIfoodPromotionRefresh";
import { mensagemErroIfood } from "./ifoodPresentation";

function precoEspecifico(item) {
  return item.saved_specific_price === null || item.saved_specific_price === undefined
    ? null
    : Number(item.saved_specific_price);
}

function ofertaMaisRecente(atual, nova) {
  return (Date.parse(nova.evaluated_at) || 0) >= (Date.parse(atual.evaluated_at) || 0)
    ? nova
    : atual;
}

export default function useIfoodSimulacaoPreco(item, { podeEditar, onAplicado }) {
  const [salvo, setSalvo] = useState(item);
  const [modo, setModo] = useState(() =>
    precoEspecifico(item) === null ? "regra_loja" : "especifico",
  );
  const [valor, setValor] = useState(() => precoEspecifico(item) ?? item.regular_price ?? 0);
  const [custosLoja, setCustosLoja] = useState(null);
  const [rascunhoCustos, setRascunhoCustos] = useState(null);
  const [usarCustosTemporarios, setUsarCustosTemporarios] = useState(false);
  const [consulta, setConsulta] = useState({
    chave: null,
    situacao: "carregando",
    resultado: null,
    erro: "",
  });
  const [revisao, setRevisao] = useState(0);
  const [carregandoOferta, setCarregandoOferta] = useState(true);
  const [erroOferta, setErroOferta] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erroSalvar, setErroSalvar] = useState("");
  const [sucesso, setSucesso] = useState("");
  const travaSalvar = useRef(false);
  const confirmacaoPendente = useRef(null);
  const preco = modo === "especifico" ? valor : null;
  const custosAtivos = Boolean(usarCustosTemporarios && custosLoja && rascunhoCustos);
  const chave = JSON.stringify([item.product_id, preco, custosAtivos ? rascunhoCustos : null]);
  // Invalida no mesmo render da virada ou da nova oferta, antes do debounce.
  const pronta =
    consulta.chave === chave &&
    consulta.revisao === revisao &&
    consulta.origem === item.evaluated_at &&
    consulta.situacao === "pronta" &&
    !carregandoOferta &&
    !erroOferta &&
    !salvando;
  const alterado = preco !== precoEspecifico(salvo);
  const resultado = consulta.chave === chave ? consulta.resultado : null;
  // O preco digitado pode tornar uma promocao valida/invalida. A proxima
  // virada da oferta salva OU da simulacao atual deve atualizar ambas.
  const tempo =
    [salvo, resultado]
      .filter((oferta) => oferta?.next_price_change_at)
      .sort(
        (a, b) =>
          Date.parse(a.next_price_change_at) - Date.parse(b.next_price_change_at) ||
          Date.parse(b.evaluated_at) - Date.parse(a.evaluated_at),
      )[0] ||
    resultado ||
    salvo;

  useIfoodPromotionRefresh(tempo, () => setRevisao((atual) => atual + 1), {
    enabled: !salvando && !carregandoOferta && consulta.situacao !== "carregando",
    scopeKey: String(item.product_id),
  });

  useEffect(() => {
    // A oferta recebida da tabela nao altera modo/valor digitados.
    setSalvo((atual) => ofertaMaisRecente(atual, item));
  }, [item]);

  useEffect(() => {
    if (salvando) return undefined;
    let ativo = true;
    const abort = new AbortController();
    setCarregandoOferta(true);
    setErroOferta("");
    (async () => {
      try {
        // Independente do filtro/pagina da central e do preco simulado.
        const { data } = await getIfoodCatalogo(
          { product_id: item.product_id, limit: 1 },
          { signal: abort.signal },
        );
        if (!ativo) return;
        const atual = data.items?.find((produto) => produto.product_id === item.product_id);
        if (!atual) throw new Error("Produto não encontrado nesta loja.");
        setSalvo((anterior) => ofertaMaisRecente(anterior, atual));
        if (confirmacaoPendente.current) {
          confirmacaoPendente.current.onAplicado?.(atual);
          confirmacaoPendente.current = null;
          setErroSalvar("");
          setSucesso("Preço aplicado ao cadastro. As taxas da simulação não foram salvas.");
        }
      } catch (error) {
        if (ativo)
          setErroOferta(
            mensagemErroIfood(error, "Não foi possível atualizar a oferta salva.") +
              " A última oferta exibida foi mantida.",
          );
      } finally {
        if (ativo) setCarregandoOferta(false);
      }
    })();
    return () => {
      ativo = false;
      abort.abort();
    };
  }, [item.product_id, revisao, salvando]);

  useEffect(() => {
    if (salvando) return undefined;
    let ativo = true;
    const abort = new AbortController();
    setConsulta((anterior) => ({
      chave,
      revisao,
      origem: item.evaluated_at,
      situacao: "carregando",
      resultado: anterior.chave === chave ? anterior.resultado : null,
      erro: "",
    }));
    const timer = window.setTimeout(async () => {
      try {
        const response = await simularPrecoIfoodProduto(
          {
            product_id: item.product_id,
            preco_ifood: preco,
            ...(custosAtivos ? { custos_simulados: rascunhoCustos } : {}),
          },
          { signal: abort.signal },
        );
        if (ativo) {
          // Apenas uma resposta com as taxas reais pode atualizar a base do editor.
          // Reconsultas, promoções e troca de modalidade preservam o rascunho.
          if (!response.data.simulation_costs) {
            setCustosLoja(null);
          } else if (!custosAtivos) {
            setCustosLoja((anterior) =>
              JSON.stringify(anterior) === JSON.stringify(response.data.simulation_costs)
                ? anterior
                : response.data.simulation_costs,
            );
          }
          setConsulta({
            chave,
            revisao,
            origem: item.evaluated_at,
            situacao: "pronta",
            resultado: response.data,
            erro: "",
          });
        }
      } catch (error) {
        if (ativo)
          setConsulta((anterior) => ({
            chave,
            revisao,
            origem: item.evaluated_at,
            situacao: "erro",
            resultado: anterior.chave === chave ? anterior.resultado : null,
            erro: mensagemErroIfood(error, "Não foi possível simular este preço. Tente novamente."),
          }));
      }
    }, 350);
    return () => {
      ativo = false;
      abort.abort();
      window.clearTimeout(timer);
    };
  }, [
    item.product_id,
    item.evaluated_at,
    preco,
    chave,
    revisao,
    salvando,
    custosAtivos,
    rascunhoCustos,
  ]);

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

  function alterarModoCustos(novoModo) {
    if (salvando || !custosLoja) return;
    if (novoModo === "temporarios") {
      setRascunhoCustos((anterior) => anterior || { ...custosLoja });
      setUsarCustosTemporarios(true);
    } else {
      setUsarCustosTemporarios(false);
    }
    setSucesso("");
  }

  function alterarCusto(campo, novoValor) {
    if (salvando || !custosAtivos || !Object.hasOwn(custosLoja, campo)) return;
    setRascunhoCustos((anterior) => ({ ...anterior, [campo]: novoValor }));
    setSucesso("");
  }

  function restaurarCustos() {
    if (salvando) return;
    setUsarCustosTemporarios(false);
    setRascunhoCustos(null);
    setSucesso("");
    setRevisao((atual) => atual + 1);
  }

  async function aplicar() {
    if (!podeEditar || !alterado || !pronta || travaSalvar.current) return;
    travaSalvar.current = true;
    setSalvando(true);
    setErroSalvar("");
    setSucesso("");
    let precoFoiSalvo = false;
    try {
      // Usa a mesma persistencia do cadastro. A simulacao nao altera produto,
      // custo, promocao, selecao ou pausa: somente esta acao salva o preco.
      await updateProduto(item.product_id, { preco_ifood: preco });
      precoFoiSalvo = true;
      confirmacaoPendente.current = { onAplicado };
      // Nunca promover a margem hipotética da calculadora a oferta salva.
      const { data } = await getIfoodCatalogo({ product_id: item.product_id, limit: 1 });
      const atualizado = data.items?.find((produto) => produto.product_id === item.product_id);
      if (!atualizado) throw new Error("Produto não encontrado nesta loja.");
      setSalvo((anterior) => ofertaMaisRecente(anterior, atualizado));
      confirmacaoPendente.current = null;
      onAplicado?.(atualizado);
      setSucesso("Preço aplicado ao cadastro. As taxas da simulação não foram salvas.");
    } catch (error) {
      if (precoFoiSalvo) {
        setErroSalvar(
          "Preço salvo, mas não foi possível atualizar a oferta. Tente atualizar novamente.",
        );
        setErroOferta("A oferta salva precisa ser atualizada antes de aplicar outro preço.");
      } else {
        setErroSalvar(mensagemErroIfood(error, "Não foi possível aplicar o preço ao produto."));
      }
    } finally {
      // A promocao pode ter virado durante o PUT; reconsultar antes de aplicar outra vez.
      setRevisao((atual) => atual + 1);
      travaSalvar.current = false;
      setSalvando(false);
    }
  }

  return {
    salvo,
    modo,
    valor,
    custosAtivos,
    custosSimulados: custosAtivos ? rascunhoCustos : custosLoja,
    podeSimularCustos: Boolean(custosLoja),
    alterado,
    pronta,
    salvando,
    carregandoOferta,
    erroOferta,
    erroSalvar,
    sucesso,
    resultado,
    erroSimulacao: consulta.chave === chave && consulta.situacao === "erro" ? consulta.erro : "",
    alterarModo,
    alterarValor,
    restaurar,
    alterarModoCustos,
    alterarCusto,
    restaurarCustos,
    aplicar,
    repetir: () => setRevisao((atual) => atual + 1),
  };
}
