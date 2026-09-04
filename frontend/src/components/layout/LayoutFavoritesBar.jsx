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

const POINTER_DRAG_DISTANCE_PX = 6;
const POINTER_CLICK_RESET_DELAY_MS = 1000;

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
    if (isDragging) {
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
    resetTimer: null,
  });
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const handlePointerDownCapture = (event) => {
    const gesture = pointerGestureRef.current;
    if (gesture.resetTimer) window.clearTimeout(gesture.resetTimer);
    gesture.startX = event.clientX;
    gesture.startY = event.clientY;
    gesture.moved = false;
    gesture.resetTimer = null;
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
    gesture.resetTimer = window.setTimeout(() => {
      gesture.moved = false;
      gesture.resetTimer = null;
    }, POINTER_CLICK_RESET_DELAY_MS);
  };

  const handleBarClickCapture = (event) => {
    const gesture = pointerGestureRef.current;
    if (!gesture.moved) return;

    event.preventDefault();
    event.stopPropagation();
    gesture.moved = false;
    if (gesture.resetTimer) window.clearTimeout(gesture.resetTimer);
    gesture.resetTimer = null;
  };

  if (favorites.length === 0) return null;

  return (
    <div
      className="shrink-0 border-b border-gray-200 bg-white/95 px-3 py-2 md:px-6 dark:border-slate-800 dark:bg-slate-950/95"
      onPointerDownCapture={handlePointerDownCapture}
      onPointerMoveCapture={handlePointerMoveCapture}
      onPointerUpCapture={handlePointerUpCapture}
      onPointerCancelCapture={handlePointerUpCapture}
      onClickCapture={handleBarClickCapture}
    >
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
        onDragCancel={onDragCancel}
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
