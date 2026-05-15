// Tipos de navegação do stack do entregador
export type EntregadorStackParamList = {
  MinhasRotas: { rotaFinalizadaId?: number; refreshKey?: number } | undefined;
  DetalheEntrega: { rotaId: number; numero: string };
};
