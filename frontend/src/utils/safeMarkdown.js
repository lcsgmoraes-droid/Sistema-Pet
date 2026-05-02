const HTML_ENTITY_MAP = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
  nbsp: " ",
};

function decodeHtmlEntities(value) {
  const text = String(value || "");

  if (typeof document !== "undefined") {
    const textarea = document.createElement("textarea");
    textarea.innerHTML = text;
    return textarea.value;
  }

  return text.replace(/&(#\d+|#x[\da-f]+|[a-z]+);/gi, (match, entity) => {
    const key = String(entity || "").toLowerCase();
    if (key.startsWith("#x")) {
      return String.fromCodePoint(parseInt(key.slice(2), 16));
    }
    if (key.startsWith("#")) {
      return String.fromCodePoint(parseInt(key.slice(1), 10));
    }
    return HTML_ENTITY_MAP[key] ?? match;
  });
}

export function normalizeMarkdownContent(value) {
  if (value === null || value === undefined) return "";

  let text = String(value)
    .replace(/\r\n?/g, "\n")
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?>[\s\S]*?<\/style>/gi, "");

  const hasHtml = /<\/?[a-z][\s\S]*>/i.test(text);

  if (hasHtml) {
    text = text
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/(p|div|section|article|header|footer|h[1-6]|tr)>/gi, "\n")
      .replace(/<li[^>]*>/gi, "- ")
      .replace(/<\/li>/gi, "\n")
      .replace(/<\/?(ul|ol|table|tbody|thead|span|strong|b|em|i|font)[^>]*>/gi, "")
      .replace(/<[^>]+>/g, "");
  }

  return decodeHtmlEntities(text)
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function markdownToPlainText(value) {
  return normalizeMarkdownContent(value)
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/(^|\s)([*_~`>]+)/g, "$1")
    .replace(/[*_~`]+(\s|$)/g, "$1")
    .replace(/\n{2,}/g, " ")
    .replace(/\s{2,}/g, " ")
    .trim();
}
