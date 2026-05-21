import { useEffect, useRef } from "react";

export function shouldCloseModalWithKeyboardEvent(event) {
  if (!event || event.defaultPrevented) return false;
  if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return false;
  return event.key === "Escape" || event.key === "Esc";
}

export function createEscapeCloseRegistry() {
  const entries = [];

  function register({ onClose, disabled = false } = {}) {
    if (typeof onClose !== "function") {
      return () => {};
    }

    const entry = { onClose, disabled };
    entries.push(entry);

    return () => {
      const index = entries.indexOf(entry);
      if (index >= 0) entries.splice(index, 1);
    };
  }

  function getActiveEntry() {
    for (let index = entries.length - 1; index >= 0; index -= 1) {
      const entry = entries[index];
      const disabled = typeof entry.disabled === "function" ? entry.disabled() : entry.disabled;
      if (!disabled) return entry;
    }

    return null;
  }

  function handleKeyDown(event) {
    if (!shouldCloseModalWithKeyboardEvent(event)) return;

    const entry = getActiveEntry();
    if (!entry) return;

    event.preventDefault?.();
    event.stopPropagation?.();
    event.stopImmediatePropagation?.();
    entry.onClose();
  }

  function size() {
    return entries.length;
  }

  return {
    handleKeyDown,
    register,
    size,
  };
}

const escapeCloseRegistry = createEscapeCloseRegistry();
let listenerCount = 0;
let isListening = false;

function ensureGlobalListener() {
  if (isListening || typeof window === "undefined") return;
  window.addEventListener("keydown", escapeCloseRegistry.handleKeyDown, true);
  isListening = true;
}

function releaseGlobalListener() {
  if (listenerCount > 0 || !isListening || typeof window === "undefined") return;
  window.removeEventListener("keydown", escapeCloseRegistry.handleKeyDown, true);
  isListening = false;
}

export function registerEscapeClose(options) {
  ensureGlobalListener();
  listenerCount += 1;
  const unregister = escapeCloseRegistry.register(options);

  return () => {
    unregister();
    listenerCount = Math.max(0, listenerCount - 1);
    releaseGlobalListener();
  };
}

export function useEscapeToClose({ isOpen = true, onClose, disabled = false } = {}) {
  const onCloseRef = useRef(onClose);
  const disabledRef = useRef(disabled);

  useEffect(() => {
    onCloseRef.current = onClose;
    disabledRef.current = disabled;
  }, [onClose, disabled]);

  useEffect(() => {
    if (!isOpen || typeof onClose !== "function" || typeof window === "undefined") {
      return undefined;
    }

    return registerEscapeClose({
      onClose: () => onCloseRef.current?.(),
      disabled: () => {
        const currentDisabled = disabledRef.current;
        return typeof currentDisabled === "function" ? currentDisabled() : currentDisabled;
      },
    });
  }, [isOpen, onClose]);
}

function isElementVisible(element) {
  const style = window.getComputedStyle(element);
  const rect = element.getBoundingClientRect();

  return (
    style.display !== "none" &&
    style.visibility !== "hidden" &&
    style.opacity !== "0" &&
    rect.width > 0 &&
    rect.height > 0
  );
}

function getZIndex(element) {
  const zIndex = Number.parseInt(window.getComputedStyle(element).zIndex || "0", 10);
  return Number.isFinite(zIndex) ? zIndex : 0;
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

function isCloseControl(element) {
  if (!element || element.disabled || element.getAttribute("aria-disabled") === "true") {
    return false;
  }

  if (element.hasAttribute("data-modal-close")) return true;

  const label = normalizeText(
    [
      element.getAttribute("aria-label"),
      element.getAttribute("title"),
      element.textContent,
    ].filter(Boolean).join(" "),
  );

  if (!label) return false;
  return /\b(fechar|close|cancelar)\b/.test(label);
}

function isLikelyHeaderCloseIcon(element, root) {
  if (!element || element.disabled || element.getAttribute("aria-disabled") === "true") {
    return false;
  }

  const label = normalizeText(
    [
      element.getAttribute("aria-label"),
      element.getAttribute("title"),
      element.textContent,
    ].filter(Boolean).join(" "),
  );

  if (label || !element.querySelector("svg")) return false;

  const elementRect = element.getBoundingClientRect();
  const rootRect = root.getBoundingClientRect();
  const headerLimit = rootRect.top + Math.max(96, rootRect.height * 0.18);
  const rightSideStart = rootRect.left + rootRect.width * 0.55;

  return elementRect.top <= headerLimit && elementRect.left >= rightSideStart;
}

function findCloseControl(root) {
  const preferredSelectors = [
    "button[data-modal-close]",
    '[role="button"][data-modal-close]',
    'button[aria-label*="fechar" i]',
    'button[aria-label*="close" i]',
    'button[title*="fechar" i]',
    'button[title*="close" i]',
    '[role="button"][aria-label*="fechar" i]',
    '[role="button"][aria-label*="close" i]',
  ];

  for (const selector of preferredSelectors) {
    const control = root.querySelector(selector);
    if (control && isCloseControl(control)) return control;
  }

  const controls = Array.from(root.querySelectorAll("button, [role='button']"));
  return (
    controls.find(isCloseControl) ||
    controls.find((control) => isLikelyHeaderCloseIcon(control, root)) ||
    null
  );
}

function findVisibleModalCandidates() {
  const candidates = Array.from(
    document.querySelectorAll('[role="dialog"], [aria-modal="true"], .fixed.inset-0'),
  );

  return candidates
    .filter((element) => {
      const className = typeof element.className === "string" ? element.className : "";

      if (element.getAttribute("data-overlay-neutralizado") === "true") return false;
      if (className.includes("erp-mobile-sidebar-backdrop")) return false;
      if (className.includes("bg-transparent")) return false;
      if (!isElementVisible(element)) return false;

      const hasDialogShape =
        element.matches('[role="dialog"], [aria-modal="true"]') ||
        Boolean(
          element.querySelector(
            '[role="dialog"], [aria-modal="true"], .bg-white, .rounded-lg, .rounded-xl, .rounded-2xl, .shadow-xl, .shadow-2xl',
          ),
        );

      return hasDialogShape;
    })
    .sort((a, b) => {
      const byZIndex = getZIndex(a) - getZIndex(b);
      if (byZIndex !== 0) return byZIndex;
      if (a === b) return 0;
      return a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
    });
}

export function closeTopVisibleModalFromDom() {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return false;
  }

  const candidates = findVisibleModalCandidates();

  for (let index = candidates.length - 1; index >= 0; index -= 1) {
    const candidate = candidates[index];
    const closeControl = findCloseControl(candidate);

    if (closeControl) {
      closeControl.click();
      return true;
    }

    if (candidate.matches(".fixed.inset-0")) {
      candidate.click();
      return true;
    }
  }

  return false;
}

export function useEscapeFallbackForVisibleModals() {
  useEffect(() => {
    if (typeof window === "undefined") return undefined;

    const handleKeyDown = (event) => {
      if (!shouldCloseModalWithKeyboardEvent(event)) return;

      if (closeTopVisibleModalFromDom()) {
        event.preventDefault?.();
        event.stopPropagation?.();
        event.stopImmediatePropagation?.();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);
}
