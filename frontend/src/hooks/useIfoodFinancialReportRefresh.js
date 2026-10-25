import { useEffect, useRef } from "react";
import { scheduleIfoodFinancialReportRefresh } from "../utils/ifoodFinancialRefresh.js";

export default function useIfoodFinancialReportRefresh({ enabled, refresh }) {
  const latestRefresh = useRef(refresh);
  useEffect(() => {
    latestRefresh.current = refresh;
  }, [refresh]);
  useEffect(
    () => scheduleIfoodFinancialReportRefresh(() => latestRefresh.current(), { enabled }),
    [enabled],
  );
}
