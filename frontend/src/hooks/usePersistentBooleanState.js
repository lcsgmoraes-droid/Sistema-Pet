import { useEffect, useState } from "react";

export function usePersistentBooleanState(storageKey, defaultValue = false) {
  const [value, setValue] = useState(() => {
    if (typeof window === "undefined") {
      return defaultValue;
    }

    const savedValue = window.localStorage.getItem(storageKey);
    if (savedValue === null) {
      return defaultValue;
    }

    try {
      const parsedValue = JSON.parse(savedValue);
      return typeof parsedValue === "boolean" ? parsedValue : defaultValue;
    } catch {
      if (savedValue === "true") {
        return true;
      }
      if (savedValue === "false") {
        return false;
      }
      return defaultValue;
    }
  });

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(storageKey, JSON.stringify(value));
  }, [storageKey, value]);

  return [value, setValue];
}
