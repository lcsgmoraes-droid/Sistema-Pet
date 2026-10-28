import { useEffect, useRef, useState } from "react";
import { getIfoodVendasCandidatas, vincularIfoodVenda } from "../../api/ifood";
import { mensagemErroIfood } from "./ifoodPresentation";

const VAZIO = {
  busca: "",
  vendaId: "",
  sourceNote: "",
  confirmado: false,
  sales: [],
  erro: "",
  sucesso: "",
};

export default function useIfoodVinculoVenda({ enabled, orderId, canEdit, onVinculado }) {
  const [rascunhos, setRascunhos] = useState({});
  const [ocupado, setOcupado] = useState(false);
  const controller = useRef(null);
  const trava = useRef(false);
  const geracao = useRef(0);
  const atual = rascunhos[orderId] || VAZIO;

  useEffect(() => {
    setOcupado(false);
    return () => {
      geracao.current++;
      controller.current?.abort();
      trava.current = false;
    };
  }, [enabled, orderId, canEdit]);

  function registrar(id, patch) {
    setRascunhos((prev) => ({ ...prev, [id]: { ...VAZIO, ...prev[id], ...patch } }));
  }

  async function buscar() {
    if (!enabled || !orderId || !canEdit || trava.current || !atual.busca.trim()) return;
    trava.current = true;
    setOcupado(true);
    const versao = geracao.current;
    const id = orderId;
    const abort = new AbortController();
    controller.current = abort;
    registrar(id, { erro: "", sucesso: "" });
    try {
      const response = await getIfoodVendasCandidatas(
        id,
        { busca: atual.busca.trim() },
        { signal: abort.signal },
      );
      if (versao === geracao.current)
        registrar(id, { sales: response.data.sales || [], vendaId: "", confirmado: false });
    } catch (error) {
      if (versao === geracao.current)
        registrar(id, {
          erro: mensagemErroIfood(
            error,
            "Não foi possível buscar as vendas. Seu rascunho foi mantido.",
          ),
        });
    } finally {
      if (versao === geracao.current) {
        trava.current = false;
        setOcupado(false);
      }
    }
  }

  async function confirmar() {
    const venda = atual.sales.find((sale) => String(sale.venda_id) === String(atual.vendaId));
    if (!enabled || !orderId || !canEdit || trava.current) return;
    if (
      !venda?.linkable ||
      !atual.confirmado ||
      atual.sourceNote.trim().length < 5 ||
      atual.sourceNote.trim().length > 1000
    ) {
      registrar(orderId, {
        erro: "Selecione uma venda apta, confirme a correspondência e informe a justificativa com 5 a 1.000 caracteres.",
      });
      return;
    }
    trava.current = true;
    setOcupado(true);
    const versao = geracao.current;
    const id = orderId;
    const abort = new AbortController();
    controller.current = abort;
    registrar(id, { erro: "", sucesso: "" });
    try {
      const response = await vincularIfoodVenda(
        id,
        { venda_id: venda.venda_id, source_note: atual.sourceNote.trim() },
        { signal: abort.signal },
      );
      if (versao === geracao.current) {
        onVinculado(response.data);
        registrar(id, {
          confirmado: false,
          sucesso: "Vínculo confirmado. O CMV passa a ser consultado no histórico desta venda.",
        });
      }
    } catch (error) {
      if (versao === geracao.current)
        registrar(id, {
          erro: mensagemErroIfood(
            error,
            "Não foi possível confirmar o vínculo. Seu rascunho foi mantido.",
          ),
        });
    } finally {
      if (versao === geracao.current) {
        trava.current = false;
        setOcupado(false);
      }
    }
  }

  return {
    ...atual,
    ocupado,
    podeEditar: Boolean(enabled && canEdit),
    alterar: (campo, value) =>
      registrar(orderId, {
        [campo]: value,
        erro: "",
        sucesso: "",
        ...(campo === "vendaId" || campo === "busca" ? { confirmado: false } : {}),
      }),
    buscar,
    confirmar,
  };
}
