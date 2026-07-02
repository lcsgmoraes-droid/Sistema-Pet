export type FoodCalculatorSelectorKind = "principal" | "comparar" | "pet" | null;
export type NivelAtividadeKey = "baixo" | "normal" | "alto";

export const NIVEIS_ATIVIDADE: Array<{ key: NivelAtividadeKey; label: string; emoji: string; descricao: string }> = [
  { key: 'baixo', label: 'Baixo', emoji: '🛋️', descricao: 'Sedentário, pouca brincadeira' },
  { key: 'normal', label: 'Normal', emoji: '🚶', descricao: 'Brincadeiras normais por dia' },
  { key: 'alto', label: 'Alto', emoji: '🏃', descricao: 'Muito ativo, muito exercício' },
];

