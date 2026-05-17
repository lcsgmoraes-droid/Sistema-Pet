export function shouldCloseModalWithKeyboardEvent(event) {
  if (!event) return false;
  if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return false;
  return event.key === "Escape" || event.key === "Esc";
}
