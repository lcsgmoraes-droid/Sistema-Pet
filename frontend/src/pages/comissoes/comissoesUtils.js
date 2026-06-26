import { DEFAULT_COMMISSION_RULES } from "./comissoesConstants";

export function getCommissionItemKey(tipo, id) {
  return `${tipo}-${id}`;
}

export function parseCommissionNumber(value, fallback = 0) {
  const parsed = parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function parseCommissionInteger(value) {
  const parsed = parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

export function mapConfiguracoesPorItem(configuracoes = []) {
  return configuracoes.reduce((acc, config) => {
    acc[getCommissionItemKey(config.tipo, config.referencia_id)] = config;
    return acc;
  }, {});
}

export function buildRulesFromConfig(config) {
  if (!config) {
    return { ...DEFAULT_COMMISSION_RULES };
  }

  return {
    desconta_taxa_cartao: config.desconta_taxa_cartao ?? true,
    desconta_impostos: config.desconta_impostos ?? true,
    desconta_taxa_entrega: config.desconta_custo_entrega ?? false,
    comissao_venda_parcial: config.comissao_venda_parcial ?? true,
  };
}

export function hasRuleChanges(regras, regrasOriginais) {
  return (
    Boolean(regrasOriginais) &&
    (regras.desconta_taxa_cartao !== regrasOriginais.desconta_taxa_cartao ||
      regras.desconta_impostos !== regrasOriginais.desconta_impostos ||
      regras.desconta_taxa_entrega !== regrasOriginais.desconta_taxa_entrega ||
      regras.comissao_venda_parcial !== regrasOriginais.comissao_venda_parcial)
  );
}

export function createSelectedCommissionItem(tipo, id, nome, configExistente) {
  return {
    tipo,
    id,
    nome,
    tipo_calculo: configExistente?.tipo_calculo || "percentual",
    percentual: configExistente?.percentual || 10,
    percentual_loja: configExistente?.percentual_loja || 50,
    permite_edicao_venda: configExistente?.permite_edicao_venda || false,
    observacoes: configExistente?.observacoes || "",
  };
}

export function isSameCommissionTarget(config, item) {
  return config.tipo === item.tipo && config.referencia_id === item.id;
}

export function buildPendingConfiguration(itemSelecionado) {
  return {
    tipo: itemSelecionado.tipo,
    referencia_id: itemSelecionado.id,
    nome: itemSelecionado.nome,
    tipo_calculo: itemSelecionado.tipo_calculo,
    percentual: parseCommissionNumber(itemSelecionado.percentual),
    percentual_loja:
      itemSelecionado.tipo_calculo === "lucro"
        ? parseCommissionNumber(itemSelecionado.percentual_loja)
        : null,
    permite_edicao_venda: itemSelecionado.permite_edicao_venda || false,
    observacoes: itemSelecionado.observacoes || "",
  };
}

export function buildCommissionPayloadBase(funcionarioId, regras) {
  return {
    funcionario_id: parseCommissionInteger(funcionarioId),
    desconta_taxa_cartao: regras.desconta_taxa_cartao,
    desconta_impostos: regras.desconta_impostos,
    desconta_custo_entrega: regras.desconta_taxa_entrega,
    comissao_venda_parcial: regras.comissao_venda_parcial,
  };
}

export function buildBatchPayload(configuracoesParaSalvar, funcionarioId, regras) {
  return configuracoesParaSalvar.map((config) => ({
    ...buildCommissionPayloadBase(funcionarioId, regras),
    tipo: config.tipo,
    referencia_id: config.referencia_id,
    tipo_calculo: config.tipo_calculo,
    percentual: parseFloat(config.percentual),
    percentual_loja: config.percentual_loja ? parseCommissionNumber(config.percentual_loja) : null,
    permite_edicao_venda: config.permite_edicao_venda || false,
    observacoes: config.observacoes || "",
  }));
}

export function buildExistingRulesPayload(config, funcionarioId, regras) {
  return {
    ...buildCommissionPayloadBase(funcionarioId, regras),
    tipo: config.tipo,
    referencia_id: config.referencia_id,
    tipo_calculo: config.tipo_calculo,
    percentual: parseCommissionNumber(config.percentual),
    percentual_loja: config.percentual_loja ? parseCommissionNumber(config.percentual_loja) : null,
    permite_edicao_venda: config.permite_edicao_venda,
    observacoes: config.observacoes || "",
  };
}

export function buildSelectedItemPayload(itemSelecionado, funcionarioId, regras) {
  return {
    ...buildCommissionPayloadBase(funcionarioId, regras),
    tipo: itemSelecionado.tipo,
    referencia_id: itemSelecionado.id,
    tipo_calculo: itemSelecionado.tipo_calculo,
    percentual: parseFloat(itemSelecionado.percentual),
    percentual_loja:
      itemSelecionado.tipo_calculo === "lucro" ? parseFloat(itemSelecionado.percentual_loja) : null,
    permite_edicao_venda: itemSelecionado.permite_edicao_venda,
    observacoes: itemSelecionado.observacoes,
  };
}
