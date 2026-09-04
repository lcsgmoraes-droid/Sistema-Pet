import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  horizontalListSortingStrategy,
  sortableKeyboardCoordinates,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useRef } from "react";
import { Link } from "react-router-dom";

import { createFavoriteDragClickGuard } from "./menuFavorites";

const POINTER_DRAG_DISTANCE_PX = 6;

// A lista e atualizada depois do drop e pode remontar a barra inteira antes
// do clique sintetico do navegador. Este guard de modulo sobrevive a essa
// remontagem e bloqueia exatamente o clique herdado do gesto de arraste.
const favoriteDragClickGuard = createFavoriteDragClickGuard();

function FavoriteShortcut({ favorite, active, onClick }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: favorite.path,
  });
  const Icon = favorite.icon;

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.72 : 1,
    zIndex: isDragging ? 20 : undefined,
  };

  const handleClickCapture = (event) => {
    // Enquanto o item ainda esta sendo arrastado, o Link nao pode receber o
    // clique sintetico do navegador. Depois do drop, o guard do Layout cobre
    // o pequeno intervalo em que o dnd-kit ja removeu `isDragging`.
    if (isDragging || favoriteDragClickGuard.consumeClick()) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    onClick?.(event);
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="shrink-0 touch-none cursor-grab active:cursor-grabbing"
      {...attributes}
      {...listeners}
    >
      <Link
        to={favorite.path}
        draggable={false}
        onClickCapture={handleClickCapture}
        onDragStart={(event) => event.preventDefault()}
        className={`inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs font-semibold shadow-sm transition-colors ${
          active
            ? "border-[#0f8b8d] bg-[#d8eee9] text-[#0f5f63]"
            : "border-gray-200 bg-white text-gray-700 hover:border-[#b9ddd8] hover:bg-[#f4fbfa]"
        } ${isDragging ? "ring-2 ring-[#b9ddd8]" : ""}`}
        title="Arraste para reordenar"
      >
        {Icon ? <Icon className="h-3.5 w-3.5 shrink-0" /> : null}
        <span className="whitespace-nowrap">{favorite.label}</span>
      </Link>
    </div>
  );
}

export default function LayoutFavoritesBar({
  favorites = [],
  isActive,
  onShortcutClick,
  onDragStart,
  onDragEnd,
  onDragCancel,
}) {
  const pointerGestureRef = useRef({
    startX: null,
    startY: null,
    moved: false,
  });
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const handlePointerDownCapture = (event) => {
    const gesture = pointerGestureRef.current;
    // Se o drag anterior nao gerou clique sintetico, um novo pointerdown
    // representa uma intencao real e libera a navegacao normalmente.
    favoriteDragClickGuard.pointerIntentStarted();
    gesture.startX = event.clientX;
    gesture.startY = event.clientY;
    // Um clique real posterior sempre comeca com um novo pointerdown. Por isso,
    // podemos liberar aqui o bloqueio deixado pelo gesto anterior sem depender
    // de um prazo arbitrario.
    gesture.moved = false;
  };

  const handlePointerMoveCapture = (event) => {
    const gesture = pointerGestureRef.current;
    if (gesture.startX == null || gesture.startY == null || gesture.moved) return;

    const distance = Math.hypot(event.clientX - gesture.startX, event.clientY - gesture.startY);
    if (distance >= POINTER_DRAG_DISTANCE_PX) gesture.moved = true;
  };

  const handlePointerUpCapture = () => {
    const gesture = pointerGestureRef.current;
    gesture.startX = null;
    gesture.startY = null;
    // `moved` permanece ativo ate o clique sintetico deste mesmo gesto. Se nao
    // houver clique, o proximo pointerdown real o limpa acima.
  };

  const handlePointerCancelCapture = () => {
    const gesture = pointerGestureRef.current;
    gesture.startX = null;
    gesture.startY = null;
    gesture.moved = false;
  };

  const handleDndDragStart = (event) => {
    // O callback do dnd-kit e a fonte mais confiavel para distinguir um drag
    // de um clique. Em alguns navegadores, o DOM e reordenado antes do clique
    // sintetico e os pointermove deixam de chegar ao container React.
    favoriteDragClickGuard.dragStarted();
    pointerGestureRef.current.moved = true;
    onDragStart?.(event);
  };

  const handleDndDragEnd = (event) => {
    // Reafirma o bloqueio depois do drop, pois a reordenacao pode remontar o
    // atalho arrastado antes de o navegador disparar o clique final.
    favoriteDragClickGuard.dragFinished();
    pointerGestureRef.current.moved = true;
    onDragEnd?.(event);
  };

  const handleDndDragCancel = (event) => {
    favoriteDragClickGuard.dragFinished();
    pointerGestureRef.current.moved = true;
    onDragCancel?.(event);
  };

  const handleBarClickCapture = (event) => {
    const gesture = pointerGestureRef.current;
    if (!gesture.moved && !favoriteDragClickGuard.consumeClick()) return;

    event.preventDefault();
    event.stopPropagation();
    gesture.moved = false;
  };

  if (favorites.length === 0) return null;

  return (
    <div
      className="shrink-0 border-b border-gray-200 bg-white/95 px-3 py-2 md:px-6 dark:border-slate-800 dark:bg-slate-950/95"
      onPointerDownCapture={handlePointerDownCapture}
      onPointerMoveCapture={handlePointerMoveCapture}
      onPointerUpCapture={handlePointerUpCapture}
      onPointerCancelCapture={handlePointerCancelCapture}
      onClickCapture={handleBarClickCapture}
    >
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDndDragStart}
        onDragEnd={handleDndDragEnd}
        onDragCancel={handleDndDragCancel}
      >
        <SortableContext
          items={favorites.map((favorite) => favorite.path)}
          strategy={horizontalListSortingStrategy}
        >
          <div className="flex items-center gap-2 overflow-x-auto">
            {favorites.map((favorite) => (
              <FavoriteShortcut
                key={favorite.path}
                favorite={favorite}
                active={isActive(favorite.path)}
                onClick={onShortcutClick}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}
