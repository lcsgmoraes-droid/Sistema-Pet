import { useState } from "react";
import toast from "react-hot-toast";
import {
  deleteProduto,
  getProdutoVariacoes,
  toggleProdutoAtivo,
} from "../api/produtos";

export default function useProdutosExclusao({
  carregarDados,
  corrigirTextoQuebrado,
  montarMensagemConflitoExclusao,
  produtosBrutos,
  setSelecionados,
}) {
  const [modalConflitoExclusao, setModalConflitoExclusao] = useState(false);
  const [bloqueiosExclusao, setBloqueiosExclusao] = useState([]);
  const [variacoesSelecionadasConflito, setVariacoesSelecionadasConflito] =
    useState([]);
  const [resolvendoConflitoExclusao, setResolvendoConflitoExclusao] =
    useState(false);
  const [autoSelecionarConflito, setAutoSelecionarConflito] = useState(true);
  const [pularConfirmacaoConflito, setPularConfirmacaoConflito] =
    useState(false);

  const obterNomeProduto = (id) => {
    const produto = produtosBrutos.find((item) => item.id === id);
    return corrigirTextoQuebrado(produto?.nome || `Produto #${id}`);
  };

  const extrairErroExclusao = (error) => {
    const statusCode = error?.response?.status;
    const detalheServidor = corrigirTextoQuebrado(error?.response?.data?.detail);

    if (statusCode === 409) {
      return {
        statusCode,
        mensagem:
          detalheServidor ||
          "Nao foi possivel excluir porque este produto possui vinculos ativos.",
      };
    }

    if (statusCode === 404) {
      return {
        statusCode,
        mensagem: "Produto nao encontrado. Atualize a tela e tente novamente.",
      };
    }

    return {
      statusCode,
      mensagem:
        detalheServidor ||
        "Erro ao excluir produto. Tente novamente em instantes.",
    };
  };

  const abrirModalConflitoExclusao = async (falhas) => {
    const falhasConflito = falhas.filter((falha) => falha.statusCode === 409);

    if (falhasConflito.length === 0) {
      return false;
    }

    const paisComConflito = [...new Set(falhasConflito.map((falha) => falha.id))];
    const bloqueios = [];

    for (const parentId of paisComConflito) {
      const falhaPai = falhasConflito.find((falha) => falha.id === parentId);
      const parentNome = obterNomeProduto(parentId);
      let variacoes = [];

      try {
        const response = await getProdutoVariacoes(parentId);
        variacoes = (response?.data || []).filter((item) => item.ativo !== false);
      } catch (error) {
        console.error(
          `Erro ao buscar variacoes do produto ${parentId} para resolver conflito:`,
          error,
        );
      }

      bloqueios.push({
        parentId,
        parentNome,
        mensagem: montarMensagemConflitoExclusao(parentNome, falhaPai?.mensagem),
        variacoes,
      });
    }

    setBloqueiosExclusao(bloqueios);
    const todasVariacoes = bloqueios.flatMap((bloqueio) =>
      bloqueio.variacoes.map((variacao) => variacao.id),
    );
    setVariacoesSelecionadasConflito(autoSelecionarConflito ? todasVariacoes : []);
    setModalConflitoExclusao(true);
    return true;
  };

  const handleSelecionarVariacaoConflito = (variacaoId, checked) => {
    setVariacoesSelecionadasConflito((prev) => {
      if (checked) {
        if (prev.includes(variacaoId)) return prev;
        return [...prev, variacaoId];
      }

      return prev.filter((id) => id !== variacaoId);
    });
  };

  const handleSelecionarTodasVariacoesDoPai = (parentId, checked) => {
    const idsDoPai = (bloqueiosExclusao.find((item) => item.parentId === parentId)
      ?.variacoes || []
    ).map((variacao) => variacao.id);

    setVariacoesSelecionadasConflito((prev) => {
      if (checked) {
        const conjunto = new Set([...prev, ...idsDoPai]);
        return Array.from(conjunto);
      }

      return prev.filter((id) => !idsDoPai.includes(id));
    });
  };

  const handleResolverConflitosExclusao = async () => {
    if (bloqueiosExclusao.length === 0) {
      setModalConflitoExclusao(false);
      return;
    }

    if (!pularConfirmacaoConflito) {
      const confirma = confirm(
        "Confirmar resolucao rapida? O sistema vai desativar as variacoes selecionadas e tentar excluir os produtos pai automaticamente.",
      );
      if (!confirma) return;
    }

    setResolvendoConflitoExclusao(true);

    const paisExcluidos = [];
    const paisComFalha = [];

    for (const bloqueio of bloqueiosExclusao) {
      const variacoesSelecionadas = bloqueio.variacoes.filter((variacao) =>
        variacoesSelecionadasConflito.includes(variacao.id),
      );

      const resultadosVariacoes = await Promise.allSettled(
        variacoesSelecionadas.map((variacao) => deleteProduto(variacao.id)),
      );

      const falhasVariacao = resultadosVariacoes
        .filter((resultado) => resultado.status === "rejected")
        .map((resultado) => extrairErroExclusao(resultado.reason));

      try {
        await deleteProduto(bloqueio.parentId);
        paisExcluidos.push(bloqueio);
      } catch (error) {
        const erroPai = extrairErroExclusao(error);
        paisComFalha.push({
          ...bloqueio,
          mensagem:
            falhasVariacao[0]?.mensagem || erroPai.mensagem || bloqueio.mensagem,
        });
      }
    }

    setResolvendoConflitoExclusao(false);
    setModalConflitoExclusao(false);

    if (paisExcluidos.length > 0) {
      toast.success(
        `${paisExcluidos.length} produto(s) pai excluido(s) apos resolver variacoes.`,
      );
    }

    if (paisComFalha.length > 0) {
      const detalhes = paisComFalha
        .slice(0, 3)
        .map((item) => `${item.parentNome}: ${item.mensagem}`)
        .join("\n");
      const sufixo =
        paisComFalha.length > 3
          ? "\n...e outros produtos continuam bloqueados."
          : "";

      alert(
        `Ainda nao foi possivel excluir ${paisComFalha.length} produto(s):\n\n${detalhes}${sufixo}`,
      );
      setSelecionados(paisComFalha.map((item) => item.parentId));
    } else {
      setSelecionados([]);
    }

    setBloqueiosExclusao([]);
    await carregarDados();
  };

  const handleExcluir = async (id) => {
    if (!confirm("Deseja realmente excluir este produto?")) return;

    try {
      await deleteProduto(id);
      toast.success("Produto excluido com sucesso!");
      carregarDados();
    } catch (error) {
      console.error("Erro ao excluir produto:", error);
      const erro = extrairErroExclusao(error);

      if (erro.statusCode === 409) {
        const abriuModal = await abrirModalConflitoExclusao([{ id, ...erro }]);
        if (abriuModal) {
          return;
        }
      }

      alert(erro.mensagem);
    }
  };

  const handleExcluirSelecionados = async (selecionados) => {
    if (!confirm(`Deseja realmente excluir ${selecionados.length} produtos?`)) {
      return;
    }

    const resultados = await Promise.allSettled(
      selecionados.map((id) => deleteProduto(id)),
    );

    const idsExcluidos = [];
    const falhas = [];

    resultados.forEach((resultado, index) => {
      const id = selecionados[index];

      if (resultado.status === "fulfilled") {
        idsExcluidos.push(id);
        return;
      }

      const erro = extrairErroExclusao(resultado.reason);
      falhas.push({ id, ...erro });
      console.error(`Erro ao excluir produto ${id}:`, resultado.reason);
    });

    if (idsExcluidos.length > 0) {
      toast.success(
        `${idsExcluidos.length} produto(s) excluido(s) com sucesso!`,
      );
      carregarDados();
    }

    if (falhas.length > 0) {
      const abriuModal = await abrirModalConflitoExclusao(falhas);
      if (abriuModal) {
        setSelecionados(falhas.map((falha) => falha.id));
        return;
      }

      const mensagens = falhas
        .slice(0, 3)
        .map((falha) => `ID ${falha.id}: ${falha.mensagem}`);
      const sufixo = falhas.length > 3 ? "\n...e outros produtos com erro." : "";

      alert(
        `Nao foi possivel excluir ${falhas.length} produto(s):\n\n${mensagens.join("\n")}${sufixo}`,
      );

      setSelecionados(falhas.map((falha) => falha.id));
      return;
    }

    setSelecionados([]);
  };

  const handleToggleAtivo = async (produto) => {
    const proximoAtivo = produto.ativo === false;
    const acao = proximoAtivo ? "ativar" : "desativar";

    if (!confirm(`Deseja realmente ${acao} o produto "${produto.nome}"?`)) {
      return;
    }

    try {
      await toggleProdutoAtivo(produto.id, proximoAtivo);
      toast.success(`Produto ${proximoAtivo ? "ativado" : "desativado"} com sucesso!`);
      carregarDados();
    } catch (error) {
      console.error(`Erro ao ${acao} produto:`, error);
      alert(`Erro ao ${acao} produto`);
    }
  };

  return {
    autoSelecionarConflito,
    bloqueiosExclusao,
    handleExcluir,
    handleExcluirSelecionados,
    handleResolverConflitosExclusao,
    handleSelecionarTodasVariacoesDoPai,
    handleSelecionarVariacaoConflito,
    handleToggleAtivo,
    modalConflitoExclusao,
    onCloseModalConflito: () => {
      if (resolvendoConflitoExclusao) return;
      setModalConflitoExclusao(false);
    },
    onToggleAutoSelecionarConflito: (checked) => {
      setAutoSelecionarConflito(checked);
      if (checked) {
        setVariacoesSelecionadasConflito(
          bloqueiosExclusao.flatMap((bloqueio) =>
            bloqueio.variacoes.map((variacao) => variacao.id),
          ),
        );
      }
    },
    pularConfirmacaoConflito,
    resolvendoConflitoExclusao,
    setPularConfirmacaoConflito,
    variacoesSelecionadasConflito,
  };
}
