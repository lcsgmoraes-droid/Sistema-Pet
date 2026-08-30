export async function copyTextToClipboard(
  value,
  { navigatorObject = globalThis.navigator, documentObject = globalThis.document } = {},
) {
  const text = String(value ?? "");

  if (navigatorObject?.clipboard?.writeText) {
    try {
      await navigatorObject.clipboard.writeText(text);
      return true;
    } catch {
      // Alguns navegadores bloqueiam a API moderna mesmo em uma acao do usuario.
    }
  }

  if (!documentObject?.body || typeof documentObject.createElement !== "function") {
    throw new Error("Area de transferencia indisponivel");
  }

  const textarea = documentObject.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  documentObject.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange?.(0, text.length);

  try {
    if (typeof documentObject.execCommand !== "function" || !documentObject.execCommand("copy")) {
      throw new Error("Nao foi possivel copiar");
    }
    return true;
  } finally {
    textarea.remove();
  }
}
