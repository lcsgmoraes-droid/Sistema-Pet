import { useCallback, useRef } from "react";

import { applyShiftRangeSelection, getShiftSelectionEvent } from "../utils/shiftRangeSelection";

export default function useShiftRangeSelection({
  getItemId,
  isItemSelectable,
  items,
  setSelectedIds,
}) {
  const anchorIdRef = useRef(null);

  return useCallback(
    (itemId, eventOrChecked) => {
      const { checked, shiftKey } = getShiftSelectionEvent(eventOrChecked);

      setSelectedIds((currentSelection) =>
        applyShiftRangeSelection({
          anchorId: anchorIdRef.current,
          checked,
          currentSelection,
          getItemId,
          isItemSelectable,
          itemId,
          items,
          shiftKey,
        }),
      );

      anchorIdRef.current = itemId;
    },
    [getItemId, isItemSelectable, items, setSelectedIds],
  );
}
