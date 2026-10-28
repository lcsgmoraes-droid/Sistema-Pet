import { useEffect, useRef } from "react";
import { scheduleIfoodPromotionRefresh } from "../utils/ifoodPromotionRefresh";

/** Atualiza leituras de vigência, sem salvar ou substituir campos do usuário. */
export default function useIfoodPromotionRefresh(
  metadata,
  onRefresh,
  { enabled = true, scopeKey = "" } = {},
) {
  const callback = useRef(onRefresh);
  const scope = useRef({ key: scopeKey, activity: {} });
  const evaluatedAt = metadata?.evaluated_at;
  const nextChangeAt = metadata?.next_price_change_at;

  useEffect(() => {
    callback.current = onRefresh;
  }, [onRefresh]);

  useEffect(() => {
    if (scope.current.key !== scopeKey) scope.current = { key: scopeKey, activity: {} };
    return scheduleIfoodPromotionRefresh(
      { evaluated_at: evaluatedAt, next_price_change_at: nextChangeAt },
      () => callback.current(),
      { enabled, activity: scope.current.activity },
    );
  }, [evaluatedAt, nextChangeAt, enabled, scopeKey]);
}
