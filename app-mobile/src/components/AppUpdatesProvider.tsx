import React, { createContext, useContext } from "react";
import { useAppUpdates } from "../hooks/useAppUpdates";

const AppUpdatesContext = createContext<ReturnType<typeof useAppUpdates> | null>(null);

export default function AppUpdatesProvider({ children }: { children: React.ReactNode }) {
  const update = useAppUpdates();
  return <AppUpdatesContext.Provider value={update}>{children}</AppUpdatesContext.Provider>;
}

export function useAppUpdatesContext() {
  const update = useContext(AppUpdatesContext);
  if (!update) throw new Error("AppUpdatesProvider ausente");
  return update;
}
