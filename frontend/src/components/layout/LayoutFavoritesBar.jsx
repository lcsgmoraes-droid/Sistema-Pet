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
import { Link } from "react-router-dom";

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
        onClick={onClick}
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
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  if (favorites.length === 0) return null;

  return (
    <div className="shrink-0 border-b border-gray-200 bg-white/95 px-3 py-2 md:px-6 dark:border-slate-800 dark:bg-slate-950/95">
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
