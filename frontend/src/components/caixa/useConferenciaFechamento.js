import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { conferirItemCaixa, obterAuditoriaCaixa, validarCaixaAtual } from "../../api/caixa";
import { urlConsultaVendaPdv } from "../../utils/conferenciaFechamentoUtils";

const colecoes = { venda: "vendas", pagamento: "pagamentos", movimentacao: "movimentacoes" };
const estados = new Set(["pendente", "ok", "divergencia"]);
const mensagemErro = (erro, padrao) =>
  typeof erro?.response?.data?.detail === "string" ? erro.response.data.detail : padrao;

// O resumo e as assinaturas vêm da mesma leitura. Nenhuma atualização mexe na
// contagem, nas observações ou na expansão dos detalhes do modal pai.
export default function useConferenciaFechamento(caixaId, { onResumo, bloqueado = false }) {
  const opcoes = useRef({ onResumo, bloqueado });
  opcoes.current = { onResumo, bloqueado };
  const contexto = useMemo(() => ({ id: caixaId, ativo: false, envio: false }), [caixaId]);
  const [estado, setEstado] = useState({ contexto, inicial: true, atualizando: true });
  const atual = estado.contexto === contexto ? estado : { inicial: true, atualizando: true };

  const carregar = useCallback(
    async ({ validar = false } = {}) => {
      if (!contexto.ativo) return null;
      if (contexto.leitura) return contexto.leitura;
      const controller = new AbortController();
      contexto.controller = controller;
      setEstado((anterior) => ({
        ...(anterior.contexto === contexto ? anterior : { inicial: true }),
        contexto,
        atualizando: true,
        erro: null,
      }));
      const leitura = (async () => {
        try {
          if (validar) await validarCaixaAtual(caixaId);
          if (!contexto.ativo || controller.signal.aborted) return null;
          const dados = await obterAuditoriaCaixa(caixaId, { signal: controller.signal });
          if (!contexto.ativo || controller.signal.aborted) return null;
          if (!dados?.resumo?.totais) throw new Error("Resumo de conferência indisponível");
          contexto.auditoria = dados;
          contexto.valido = true;
          opcoes.current.onResumo(dados.resumo);
          setEstado((anterior) => ({
            ...anterior,
            contexto,
            auditoria: dados,
            valido: true,
            erro: null,
          }));
          return dados;
        } catch (erro) {
          if (contexto.ativo && contexto.controller === controller && !controller.signal.aborted) {
            contexto.valido = false;
            setEstado((anterior) => ({
              ...anterior,
              contexto,
              valido: false,
              erro: mensagemErro(
                erro,
                "Não foi possível atualizar o caixa. Atualize antes de continuar a conferência.",
              ),
            }));
          }
          return null;
        } finally {
          const leituraAtual = contexto.controller === controller;
          if (leituraAtual) {
            contexto.leitura = null;
            contexto.controller = null;
          }
          if (contexto.ativo && leituraAtual) {
            setEstado((anterior) => ({
              ...anterior,
              contexto,
              inicial: false,
              atualizando: false,
            }));
          }
        }
      })();
      contexto.leitura = leitura;
      return leitura;
    },
    [caixaId, contexto],
  );

  useEffect(() => {
    contexto.ativo = true;
    void carregar({ validar: true });
    return () => {
      contexto.ativo = false;
      contexto.controller?.abort();
      contexto.controller = null;
      contexto.leitura = null;
    };
  }, [contexto, carregar]);

  const atualizar = useCallback(() => {
    if (contexto.envio) return Promise.resolve(null);
    return carregar({ validar: true });
  }, [contexto, carregar]);

  useEffect(() => {
    const aoVoltar = () => {
      if (document.visibilityState === "hidden" || opcoes.current.bloqueado || contexto.envio)
        return;
      void atualizar();
    };
    window.addEventListener("focus", aoVoltar);
    window.addEventListener("online", aoVoltar);
    document.addEventListener("visibilitychange", aoVoltar);
    return () => {
      window.removeEventListener("focus", aoVoltar);
      window.removeEventListener("online", aoVoltar);
      document.removeEventListener("visibilitychange", aoVoltar);
    };
  }, [contexto, atualizar]);

  const salvar = useCallback(
    async (tipo, item, proximoEstado, observacao = "") => {
      if (
        !contexto.ativo ||
        contexto.envio ||
        contexto.leitura ||
        !contexto.valido ||
        opcoes.current.bloqueado ||
        !estados.has(proximoEstado)
      )
        return false;
      const original = contexto.auditoria?.[colecoes[tipo]]?.find((linha) => linha.id === item?.id);
      if (!original || original.assinatura !== item?.assinatura) return false;
      const nota = String(observacao).trim();
      if (proximoEstado === "divergencia" && !nota) return false;
      contexto.envio = true;
      setEstado((anterior) => ({ ...anterior, salvando: true, erro: null }));
      try {
        await conferirItemCaixa(caixaId, {
          tipo_item: tipo,
          item_id: original.id,
          assinatura: original.assinatura,
          estado: proximoEstado,
          conferido: proximoEstado === "ok",
          observacao: nota || null,
        });
        if (!contexto.ativo) return false;
        const dados = await carregar();
        if (!dados && contexto.ativo) {
          setEstado((anterior) => ({
            ...anterior,
            erro: "Conferência salva, mas a atualização falhou. Atualize o caixa para conferir o resultado.",
          }));
        }
        return Boolean(dados);
      } catch (erro) {
        if (!contexto.ativo) return false;
        await carregar();
        if (contexto.ativo) {
          const mudou = [404, 409].includes(erro?.response?.status);
          setEstado((anterior) => ({
            ...anterior,
            erro: mudou
              ? "O lançamento foi atualizado. Confira novamente antes de confirmar."
              : mensagemErro(
                  erro,
                  "Não foi possível confirmar a gravação. Confira o estado atualizado e tente novamente.",
                ),
          }));
        }
        return false;
      } finally {
        contexto.envio = false;
        if (contexto.ativo) setEstado((anterior) => ({ ...anterior, salvando: false }));
      }
    },
    [caixaId, contexto, carregar],
  );

  const abrirVenda = useCallback((vendaId) => {
    const url = urlConsultaVendaPdv(vendaId);
    if (url) window.open(url, "_blank", "noopener,noreferrer");
  }, []);

  return {
    ...atual,
    atualizar,
    salvar,
    abrirVenda,
    ocupado: Boolean(bloqueado || atual.atualizando || atual.salvando),
    bloqueado: Boolean(bloqueado || !atual.valido || atual.atualizando || atual.salvando),
  };
}
