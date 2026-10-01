import { DndContext, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from "@dnd-kit/core";
import { GripVertical } from "lucide-react";
import { useEffect, useState } from "react";
import api from "../../api";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";

const COLUNA_DISPONIVEIS = "col-disponiveis";
const COLUNA_ASSOCIADAS = "col-associadas";

function LojaChip({ loja, pendente }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: loja.tenant_id,
    disabled: pendente,
  });
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={[
        "flex items-center gap-2 rounded-lg border bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors",
        "dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
        isDragging ? "relative z-10 border-blue-400 opacity-60" : "border-slate-200",
        pendente ? "opacity-50" : "cursor-grab touch-none active:cursor-grabbing",
      ].join(" ")}
    >
      <GripVertical className="h-4 w-4 flex-none text-slate-400" aria-hidden="true" />
      <span className="min-w-0 flex-1 truncate">
        {loja.nome}
        {loja.atual ? <span className="text-xs text-slate-400"> (loja atual)</span> : null}
      </span>
    </div>
  );
}

function Coluna({ id, titulo, lojas, pendentes, vazio }) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      className={[
        "flex min-h-[220px] flex-col gap-2 rounded-lg border-2 border-dashed p-3 transition-colors",
        isOver
          ? "border-blue-400 bg-blue-50 dark:border-cyan-500 dark:bg-cyan-500/10"
          : "border-slate-200 dark:border-slate-700",
      ].join(" ")}
    >
      <span className="text-xs font-bold uppercase tracking-wide text-slate-500">{titulo}</span>
      {lojas.length === 0 ? (
        <p className="text-xs text-slate-400">{vazio}</p>
      ) : (
        lojas.map((loja) => (
          <LojaChip key={loja.tenant_id} loja={loja} pendente={pendentes.has(loja.tenant_id)} />
        ))
      )}
    </div>
  );
}

export default function UsuarioVincularLojaModal({ onAlterado, onClose, usuario }) {
  const [lojas, setLojas] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [pendentes, setPendentes] = useState(() => new Set());

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  useEffect(() => {
    let ativo = true;
    api
      .get(`/usuarios/${usuario.user_id}/lojas-grupo`)
      .then(({ data }) => {
        if (ativo) setLojas(data?.lojas || []);
      })
      .catch(() => {
        if (ativo) setErro("Não foi possível carregar as lojas do grupo comercial.");
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [usuario.user_id]);

  const disponiveis = lojas.filter((loja) => !loja.vinculado);
  const associadas = lojas.filter((loja) => loja.vinculado);

  async function mover(tenantId, colunaDestino) {
    const lojaAtual = lojas.find((loja) => loja.tenant_id === tenantId);
    if (!lojaAtual) return;
    const vinculadoDestino = colunaDestino === COLUNA_ASSOCIADAS;
    if (lojaAtual.vinculado === vinculadoDestino) return;

    setErro("");
    setPendentes((atual) => new Set(atual).add(tenantId));
    setLojas((atual) =>
      atual.map((loja) =>
        loja.tenant_id === tenantId ? { ...loja, vinculado: vinculadoDestino } : loja,
      ),
    );

    try {
      if (vinculadoDestino) {
        await api.post(`/usuarios/${usuario.user_id}/lojas-grupo/${tenantId}`);
      } else {
        await api.delete(`/usuarios/${usuario.user_id}/lojas-grupo/${tenantId}`);
      }
      onAlterado?.();
    } catch (error) {
      setLojas((atual) =>
        atual.map((loja) =>
          loja.tenant_id === tenantId ? { ...loja, vinculado: !vinculadoDestino } : loja,
        ),
      );
      setErro(error.response?.data?.detail || "Não foi possível salvar essa alteração.");
    } finally {
      setPendentes((atual) => {
        const proximo = new Set(atual);
        proximo.delete(tenantId);
        return proximo;
      });
    }
  }

  function handleDragEnd(event) {
    const { active, over } = event;
    if (!over) return;
    mover(active.id, over.id);
  }

  return (
    <ModalPadrao
      titulo={`Lojas de ${usuario.nome || usuario.username || usuario.email || usuario.login_phone}`}
      tamanho="normal"
      onFechar={onClose}
      rodape={<BotaoCancelar onClick={onClose}>Fechar</BotaoCancelar>}
    >
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Arraste uma loja de um lado para o outro — a mudança já é salva na hora, sem precisar
        confirmar nada. O usuário sempre precisa continuar com acesso a pelo menos uma loja.
      </p>

      {erro ? (
        <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300">
          {erro}
        </div>
      ) : null}

      {carregando ? (
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">Carregando lojas...</p>
      ) : (
        <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Coluna
              id={COLUNA_DISPONIVEIS}
              titulo="Lojas disponíveis"
              lojas={disponiveis}
              pendentes={pendentes}
              vazio="Nenhuma outra loja no grupo comercial."
            />
            <Coluna
              id={COLUNA_ASSOCIADAS}
              titulo="Lojas associadas"
              lojas={associadas}
              pendentes={pendentes}
              vazio="Nenhuma loja associada."
            />
          </div>
        </DndContext>
      )}
    </ModalPadrao>
  );
}
