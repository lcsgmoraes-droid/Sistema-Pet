import api from "../../api";

export {
  RECENT_EVENTS_LIMIT,
  friendlyErrorMessage,
  splitEventBuckets,
} from "./BlingFlowMonitorCards";

const MONITOR_BASES = ["/bling/monitor", "/integracoes/bling/monitor"];

export async function monitorRequest(method, path, config) {
  let ultimoErro = null;

  for (const base of MONITOR_BASES) {
    try {
      if (method === "get") return await api.get(`${base}${path}`, config);
      return await api.post(`${base}${path}`, config?.data, config);
    } catch (error) {
      ultimoErro = error;
      if (error?.response?.status !== 404) {
        throw error;
      }
    }
  }

  throw ultimoErro;
}
