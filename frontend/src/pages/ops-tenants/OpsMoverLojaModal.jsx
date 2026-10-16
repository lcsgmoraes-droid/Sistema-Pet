import { useMemo, useState } from "react";

import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
import platformApi from "../../platformApi";
import { confirmarCorePet } from "../../services/corepetDialog";

function extrairErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

// Ferramenta administrativa provisoria (sem equivalente self-service, de
// proposito) pra corrigir lojas pre-existentes que ficaram no grupo
// comercial errado - "puxa" uma loja de onde ela estiver (outro grupo, ou
// nenhum) pra dentro de um grupo que ja existe. Se o grupo de origem ficar
// sem nenhuma loja, ele e desativado (nao e hard delete). Deve ser
// removida quando nao houver mais lojas legadas pra corrigir.
export default function OpsMoverLojaModal({ items, onClose, onMoved }) {
  const [lojaId, setLojaId] = useState("");
  const [grupoDestinoId, setGrupoDestinoId] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState(null);

  const opcoesLoja = useMemo(
    () =>
      items.map((item) => ({
        value: item.id,
        label: `${item.name}${
          item.grupo_comercial ? ` (hoje: ${item.grupo_comercial.nome})` : " (sem grupo)"
        }`,
      })),
    [items],
  );

  const lojaSelecionada = useMemo(
    () => items.find((item) => item.id === lojaId) || null,
    [items, lojaId],
  );

  const opcoesGrupoDestino = useMemo(() => {
    const grupos = new Map();
    for (const item of items) {
      const grupo = item.grupo_comercial;
      if (!grupo || grupos.has(grupo.id)) continue;
      grupos.set(grupo.id, grupo.nome);
    }
    return Array.from(grupos.entries())
      .filter(([id]) => id !== lojaSelecionada?.grupo_comercial?.id)
      .map(([id, nome]) => ({ value: id, label: nome }));
  }, [items, lojaSelecionada]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!lojaId) {
      setErro("Selecione a loja que vai ser movida.");
      return;
    }
    if (!grupoDestinoId) {
      setErro("Selecione o grupo comercial de destino.");
      return;
    }
    const grupoOrigemNome = lojaSelecionada?.grupo_comercial?.nome;
    const confirmado = await confirmarCorePet(
      grupoOrigemNome
        ? `Mover "${lojaSelecionada?.name}" do grupo "${grupoOrigemNome}" pra este grupo? ` +
            `Se "${grupoOrigemNome}" ficar sem nenhuma loja, ele deixa de existir.`
        : `Mover "${lojaSelecionada?.name}" (hoje sem grupo) pra este grupo comercial?`,
    );
    if (!confirmado) return;

    setErro("");
    setEnviando(true);
    try {
      const { data } = await platformApi.post(
        `/admin/grupos-comerciais/${grupoDestinoId}/mover-loja`,
        { empresa_id: lojaId },
      );
      setResultado(data);
      onMoved?.();
    } catch (error) {
      setErro(extrairErro(error, "Nao foi possivel mover a loja. Tente novamente."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <ModalPadrao
      titulo="Mover loja entre grupos comerciais"
      tamanho="pequena"
      onFechar={onClose}
      rodape={
        resultado ? (
          <BotaoCancelar onClick={onClose}>Fechar</BotaoCancelar>
        ) : (
          <>
            <BotaoCancelar onClick={onClose}>Cancelar</BotaoCancelar>
            <BotaoSalva form="mover-loja-form" loading={enviando}>
              {enviando ? "Movendo..." : "Mover loja"}
            </BotaoSalva>
          </>
        )
      }
    >
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Ferramenta provisória para corrigir lojas pré-existentes que ficaram no grupo comercial
        errado. Sem trilha de desfazer automático — confira antes de confirmar.
      </p>

      {resultado ? (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300">
          <p className="font-semibold">Loja movida para o grupo comercial.</p>
          {resultado.grupo_origem_extinto ? (
            <p className="mt-1">
              O grupo comercial de origem ficou sem nenhuma loja e foi desativado.
            </p>
          ) : null}
        </div>
      ) : (
        <form id="mover-loja-form" onSubmit={handleSubmit} noValidate className="mt-4 space-y-4">
          <InputCombobox
            id="mover-loja-origem"
            label="Loja a mover"
            required
            opcoes={opcoesLoja}
            value={lojaId}
            onChange={(valor) => {
              setLojaId(valor);
              setGrupoDestinoId("");
              setErro("");
            }}
          />
          <InputCombobox
            id="mover-loja-destino"
            label="Grupo comercial de destino"
            required
            disabled={!lojaId}
            opcoes={opcoesGrupoDestino}
            value={grupoDestinoId}
            onChange={(valor) => {
              setGrupoDestinoId(valor);
              setErro("");
            }}
            help={
              opcoesGrupoDestino.length === 0 && lojaId
                ? "Não há outro grupo comercial para receber esta loja."
                : ""
            }
          />

          {erro ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300">
              {erro}
            </div>
          ) : null}
        </form>
      )}
    </ModalPadrao>
  );
}
