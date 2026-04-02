export const ICONES_DISPONIVEIS = [
  "💳",
  "🏦",
  "💰",
  "💵",
  "💸",
  "🏧",
  "💼",
  "🎯",
  "⚡",
  "🔒",
  "✨",
  "🌟",
  "📊",
  "💎",
  "🎁",
  "🔑",
  "⭐",
  "🚀",
];

export function getIconeOperadora(icone) {
  if (!icone) return "💳";
  if (typeof icone !== "string") return "💳";
  if (icone.startsWith("Fi") || icone.startsWith("Bi")) return "💳";
  return icone;
}
