import { createNavigationContainerRef } from "@react-navigation/native";

export const navigationRef = createNavigationContainerRef<Record<string, object | undefined>>();

export function navigateWhenReady(name: string, params?: object) {
  if (!navigationRef.isReady()) return;
  navigationRef.navigate(name, params);
}

