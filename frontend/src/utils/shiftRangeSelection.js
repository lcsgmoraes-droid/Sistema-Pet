const defaultGetItemId = (item) => (item && typeof item === "object" ? item.id : item);

function normalizeSelection(currentSelection) {
  if (currentSelection instanceof Set) {
    return {
      selectedIds: new Set(currentSelection),
      restore: (selectedIds) => selectedIds,
    };
  }

  return {
    selectedIds: new Set(Array.isArray(currentSelection) ? currentSelection : []),
    restore: (selectedIds) => Array.from(selectedIds),
  };
}

export function applyShiftRangeSelection({
  anchorId,
  checked,
  currentSelection,
  getItemId = defaultGetItemId,
  isItemSelectable = () => true,
  itemId,
  items = [],
  shiftKey = false,
}) {
  const { selectedIds, restore } = normalizeSelection(currentSelection);
  const selectableIds = items.filter(isItemSelectable).map(getItemId);
  const anchorIndex = selectableIds.findIndex((id) => Object.is(id, anchorId));
  const itemIndex = selectableIds.findIndex((id) => Object.is(id, itemId));

  let affectedIds = [itemId];

  if (shiftKey && anchorIndex !== -1 && itemIndex !== -1) {
    const start = Math.min(anchorIndex, itemIndex);
    const end = Math.max(anchorIndex, itemIndex);
    affectedIds = selectableIds.slice(start, end + 1);
  }

  affectedIds.forEach((id) => {
    if (checked) selectedIds.add(id);
    else selectedIds.delete(id);
  });

  return restore(selectedIds);
}

export function getShiftSelectionEvent(eventOrChecked) {
  if (typeof eventOrChecked === "boolean") {
    return { checked: eventOrChecked, shiftKey: false };
  }

  const nativeEvent = eventOrChecked?.nativeEvent || eventOrChecked;

  return {
    checked: Boolean(eventOrChecked?.target?.checked ?? nativeEvent?.target?.checked),
    shiftKey: Boolean(eventOrChecked?.shiftKey ?? nativeEvent?.shiftKey),
  };
}
