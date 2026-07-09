import { createNavigationContainerRef } from "@react-navigation/native";

export const navigationRef = createNavigationContainerRef<Record<string, object | undefined>>();

let pendingNavigation: { name: string; params?: object } | null = null;

export function navigateWhenReady(name: string, params?: object) {
  if (!navigationRef.isReady()) {
    pendingNavigation = { name, params };
    return;
  }
  navigationRef.navigate(name, params);
}

export function flushPendingNavigation() {
  if (!navigationRef.isReady() || !pendingNavigation) return;
  const next = pendingNavigation;
  pendingNavigation = null;
  navigationRef.navigate(next.name, next.params);
}
