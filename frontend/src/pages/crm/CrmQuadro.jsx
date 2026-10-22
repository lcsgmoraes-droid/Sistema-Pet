import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  closestCorners,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import CrmColuna from "./CrmColuna";

// Arrastar com mouse, toque (segurar um instante, para não atrapalhar a rolagem) e teclado.
export default function CrmQuadro({ colunas, movendoId, multiLoja, onAbrir, onMover }) {
  const sensores = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 250, tolerance: 8 } }),
    useSensor(KeyboardSensor),
  );

  const aoSoltar = ({ active, over }) => {
    if (!over) return;
    const card = active.data.current?.card;
    const destino = colunas.find((coluna) => coluna.chave === over.id);
    if (card && destino) onMover(card, destino);
  };

  return (
    <DndContext sensors={sensores} collisionDetection={closestCorners} onDragEnd={aoSoltar}>
      <div className="flex items-start gap-3 overflow-x-auto pb-4">
        {colunas.map((coluna) => (
          <CrmColuna
            key={coluna.chave}
            coluna={coluna}
            mostrarLoja={multiLoja}
            movendoId={movendoId}
            onAbrir={onAbrir}
          />
        ))}
      </div>
    </DndContext>
  );
}
