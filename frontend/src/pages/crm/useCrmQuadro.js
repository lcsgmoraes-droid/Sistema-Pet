import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import { exigenciasDaMovimentacao, unificarQuadros } from "./crmUtils";

const CHAVE_LOJAS = "crm.lojasSelecionadas";

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

function lerLojasSalvas() {
  try {
    const salvo = JSON.parse(localStorage.getItem(CHAVE_LOJAS) || "[]");
    return Array.isArray(salvo) ? salvo : [];
  } catch {
    return [];
  }
}

function salvarLojas(ids) {
  try {
    localStorage.setItem(CHAVE_LOJAS, JSON.stringify(ids));
  } catch {
    // Sem armazenamento local a tela segue funcionando, só não lembra a escolha.
  }
}

function montarQuery(lojas, busca) {
  const query = new URLSearchParams();
  lojas.forEach((id) => query.append("lojas", id));
  if (busca.trim()) query.set("busca", busca.trim());
  const texto = query.toString();
  return texto ? `?${texto}` : "";
}

export default function useCrmQuadro() {
  // Um único loading do início até os dados aparecerem (regra de telas assíncronas).
  const [carregando, setCarregando] = useState(true);
  const [atualizando, setAtualizando] = useState(false);
  const [erro, setErro] = useState("");
  const [lojasDisponiveis, setLojasDisponiveis] = useState([]);
  const [lojasEscolhidas, setLojasEscolhidas] = useState(lerLojasSalvas);
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [lojasDoQuadro, setLojasDoQuadro] = useState([]);
  const [pendencia, setPendencia] = useState(null);
  const [movendoId, setMovendoId] = useState(null);
  const [versao, setVersao] = useState(0);
  const [lojasProntas, setLojasProntas] = useState(false);

  const recarregar = useCallback(() => setVersao((atual) => atual + 1), []);

  // Só vale a escolha salva que ainda é permitida; vazio = todas as lojas permitidas.
  const idsValidos = useMemo(() => {
    const permitidos = new Set(lojasDisponiveis.map((loja) => loja.id));
    return lojasEscolhidas.filter((id) => permitidos.has(id));
  }, [lojasEscolhidas, lojasDisponiveis]);

  useEffect(() => {
    const termo = busca;
    const espera = setTimeout(() => setBuscaAplicada(termo), 300);
    return () => clearTimeout(espera);
  }, [busca]);

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const { data } = await api.get("/crm/lojas");
        if (ativo) setLojasDisponiveis(data.lojas || []);
      } catch (error) {
        if (ativo) setErro(mensagemDeErro(error, "Não foi possível carregar as lojas do CRM."));
      } finally {
        if (ativo) setLojasProntas(true);
      }
    })();
    return () => {
      ativo = false;
    };
  }, []);

  useEffect(() => {
    if (!lojasProntas) return undefined;
    let ativo = true;
    (async () => {
      setAtualizando(true);
      try {
        const { data } = await api.get(`/crm/quadro${montarQuery(idsValidos, buscaAplicada)}`);
        if (!ativo) return;
        setLojasDoQuadro(data.lojas || []);
        setErro("");
      } catch (error) {
        if (ativo) setErro(mensagemDeErro(error, "Não foi possível carregar o quadro."));
      } finally {
        if (ativo) {
          setCarregando(false);
          setAtualizando(false);
        }
      }
    })();
    return () => {
      ativo = false;
    };
  }, [lojasProntas, idsValidos, buscaAplicada, versao]);

  const colunas = useMemo(() => unificarQuadros(lojasDoQuadro), [lojasDoQuadro]);
  const multiLoja = lojasDoQuadro.length > 1;

  const escolherLojas = useCallback((ids) => {
    setLojasEscolhidas(ids);
    salvarLojas(ids);
  }, []);

  const executarMovimentacao = useCallback(
    async (card, colunaDestino, extras = {}) => {
      const colunaId = colunaDestino.idPorLoja[card.loja_id];
      if (!colunaId) {
        toast.error(`A loja ${card.loja_nome} não tem a coluna “${colunaDestino.nome}”.`);
        return false;
      }
      setMovendoId(`${card.loja_id}:${card.id}`);
      try {
        await api.post(`/crm/leads/${card.id}/mover`, {
          loja_id: card.loja_id,
          coluna_id: colunaId,
          nota: extras.nota || null,
          motivo_perda: extras.motivoPerda || null,
          resultados: extras.resultados || [],
        });
        toast.success(`Card movido para “${colunaDestino.nome}”.`);
        recarregar();
        return true;
      } catch (error) {
        toast.error(mensagemDeErro(error, "Não foi possível mover o card."));
        return false;
      } finally {
        setMovendoId(null);
      }
    },
    [recarregar],
  );

  const moverCard = useCallback(
    (card, colunaDestino) => {
      const colunaOrigem = colunas.find(
        (coluna) => coluna.idPorLoja[card.loja_id] === card.coluna_id,
      );
      if (!colunaOrigem || colunaOrigem.chave === colunaDestino.chave) return;
      const exigencias = exigenciasDaMovimentacao(card, colunaDestino, colunaOrigem);
      if (exigencias.exigeModal) {
        setPendencia({ card, colunaDestino, ...exigencias });
        return;
      }
      executarMovimentacao(card, colunaDestino);
    },
    [colunas, executarMovimentacao],
  );

  const confirmarPendencia = useCallback(
    async (extras) => {
      if (!pendencia) return false;
      const ok = await executarMovimentacao(pendencia.card, pendencia.colunaDestino, extras);
      if (ok) setPendencia(null);
      return ok;
    },
    [pendencia, executarMovimentacao],
  );

  return {
    atualizando,
    busca,
    carregando,
    colunas,
    confirmarPendencia,
    erro,
    escolherLojas,
    idsValidos,
    lojasDisponiveis,
    movendoId,
    moverCard,
    multiLoja,
    pendencia,
    recarregar,
    cancelarPendencia: () => setPendencia(null),
    setBusca,
  };
}
