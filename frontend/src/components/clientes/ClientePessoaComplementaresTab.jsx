import InputCheckTexto from "../v2/InputCheckTexto/InputCheckTexto";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputMoeda from "../v2/InputMoeda/InputMoeda";
import InputQuantidade from "../v2/InputQuantidade/InputQuantidade";
import InputRadio from "../v2/InputRadio/InputRadio";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";

const OPCOES_SIM_NAO = [
  { value: "sim", label: "Sim" },
  { value: "nao", label: "Não" },
];

const OPCOES_PERIODICIDADE = [
  { value: "semanal", label: "Semanal" },
  { value: "quinzenal", label: "Quinzenal (dias 1 e 15)" },
  { value: "mensal", label: "Mensal" },
];

const OPCOES_DIA_SEMANA = [
  { value: "1", label: "Segunda" },
  { value: "2", label: "Terça" },
  { value: "3", label: "Quarta" },
  { value: "4", label: "Quinta" },
  { value: "5", label: "Sexta" },
  { value: "6", label: "Sábado" },
  { value: "7", label: "Domingo" },
];

export default function ClientePessoaComplementaresTab({ formData, setFormData }) {
  const mostrarEntrega = formData.is_funcionario || formData.is_fornecedor;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:items-start">
      {mostrarEntrega ? (
        <section className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-500/30 dark:bg-blue-500/10">
          <InputRadio
            name="pessoa-is-entregador"
            label="É entregador?"
            opcoes={OPCOES_SIM_NAO}
            value={formData.is_entregador ? "sim" : "nao"}
            onChange={(valor) => {
              const marcado = valor === "sim";
              setFormData((prev) => {
                const perfis = new Set(prev.app_access_profiles || []);
                if (marcado) perfis.add("entregador");
                else perfis.delete("entregador");
                return { ...prev, is_entregador: marcado, app_access_profiles: Array.from(perfis) };
              });
            }}
          />
          <p className="mt-1 text-xs text-slate-500">
            Ao ativar, esta pessoa poderá ser vinculada a rotas de entrega, com custo e acerto
            financeiro configuráveis abaixo.
          </p>

          {formData.is_entregador ? (
            <div className="mt-3 space-y-3 border-l-2 border-blue-300 pl-3">
              <InputCheckTexto
                id="pessoa-entregador-padrao"
                checked={formData.entregador_padrao || false}
                onChange={(entregador_padrao) =>
                  setFormData((prev) => ({ ...prev, entregador_padrao }))
                }
              >
                <span className="text-sm text-slate-700 dark:text-slate-300">
                  Entregador padrão{" "}
                  <span className="text-xs text-slate-500">(pré-selecionado nas rotas)</span>
                </span>
              </InputCheckTexto>

              {formData.is_funcionario ? (
                <>
                  <InputCheckTexto
                    id="pessoa-controla-rh"
                    checked={formData.controla_rh || false}
                    onChange={(controlaRH) =>
                      setFormData((prev) => ({
                        ...prev,
                        controla_rh: controlaRH,
                        modelo_custo_entrega: controlaRH ? "" : prev.modelo_custo_entrega,
                        taxa_fixa_entrega: controlaRH ? "" : prev.taxa_fixa_entrega,
                        valor_por_km_entrega: controlaRH ? "" : prev.valor_por_km_entrega,
                        gera_conta_pagar_custo_entrega: false,
                      }))
                    }
                  >
                    <span className="text-sm text-slate-700 dark:text-slate-300">
                      Controla RH
                    </span>
                    <span className="mt-0.5 block text-xs text-slate-500">
                      Custo rateado na folha (não gera contas a pagar)
                    </span>
                  </InputCheckTexto>

                  {formData.controla_rh ? (
                    <div className="w-full max-w-[240px] border-l-2 border-blue-300 pl-3">
                      <InputQuantidade
                        id="pessoa-media-entregas"
                        label="Média de entregas por mês"
                        min={1}
                        value={formData.media_entregas_configurada || ""}
                        onChange={(media_entregas_configurada) =>
                          setFormData((prev) => ({ ...prev, media_entregas_configurada }))
                        }
                        help="Ajustado automaticamente no fim do mês."
                      />
                    </div>
                  ) : (
                    <InputCheckTexto
                      id="pessoa-gera-cp-entrega"
                      checked={formData.gera_conta_pagar_custo_entrega || false}
                      onChange={(gera_conta_pagar_custo_entrega) =>
                        setFormData((prev) => ({ ...prev, gera_conta_pagar_custo_entrega }))
                      }
                    >
                      <span className="text-sm text-slate-700 dark:text-slate-300">
                        Gerar contas a pagar por entrega
                      </span>
                      <span className="mt-0.5 block text-xs text-slate-500">
                        Marque se recebe por KM ou taxa fixa a cada entrega
                      </span>
                    </InputCheckTexto>
                  )}
                </>
              ) : null}

              {formData.is_fornecedor ||
              (formData.is_funcionario && !formData.controla_rh) ? (
                <div className="space-y-3">
                  <InputCheckTexto
                    id="pessoa-modelo-taxa-fixa"
                    checked={formData.modelo_custo_entrega === "taxa_fixa"}
                    onChange={(marcado) =>
                      setFormData((prev) => ({
                        ...prev,
                        modelo_custo_entrega: marcado ? "taxa_fixa" : "",
                        valor_por_km_entrega: "",
                      }))
                    }
                  >
                    <span className="text-sm text-slate-700 dark:text-slate-300">Taxa fixa</span>
                  </InputCheckTexto>
                  {formData.modelo_custo_entrega === "taxa_fixa" ? (
                    <div className="w-full max-w-[200px]">
                      <InputMoeda
                        id="pessoa-taxa-fixa-valor"
                        label="Valor da taxa fixa"
                        value={formData.taxa_fixa_entrega || 0}
                        onChange={(taxa_fixa_entrega) =>
                          setFormData((prev) => ({ ...prev, taxa_fixa_entrega }))
                        }
                      />
                    </div>
                  ) : null}

                  <InputCheckTexto
                    id="pessoa-modelo-por-km"
                    checked={formData.modelo_custo_entrega === "por_km"}
                    onChange={(marcado) =>
                      setFormData((prev) => ({
                        ...prev,
                        modelo_custo_entrega: marcado ? "por_km" : "",
                        taxa_fixa_entrega: "",
                      }))
                    }
                  >
                    <span className="text-sm text-slate-700 dark:text-slate-300">Valor por KM</span>
                  </InputCheckTexto>
                  {formData.modelo_custo_entrega === "por_km" ? (
                    <div className="w-full max-w-[200px]">
                      <InputMoeda
                        id="pessoa-valor-km"
                        label="Valor por KM"
                        value={formData.valor_por_km_entrega || 0}
                        onChange={(valor_por_km_entrega) =>
                          setFormData((prev) => ({ ...prev, valor_por_km_entrega }))
                        }
                      />
                    </div>
                  ) : null}
                </div>
              ) : null}

              <InputCheckTexto
                id="pessoa-moto-propria"
                checked={formData.moto_propria || false}
                onChange={(moto_propria) => setFormData((prev) => ({ ...prev, moto_propria }))}
              >
                <span className="text-sm text-slate-700 dark:text-slate-300">
                  {formData.moto_propria ? "Moto própria" : "Moto da loja"}
                </span>
              </InputCheckTexto>

              <div className="border-t border-blue-200 pt-3">
                <h4 className="mb-2 text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Acerto financeiro
                </h4>
                <div className="space-y-3">
                  <div className="flex flex-wrap items-start gap-4">
                    <div className="w-full max-w-[200px]">
                      <InputCombobox
                        id="pessoa-acerto-periodicidade"
                        label="Periodicidade"
                        opcoes={OPCOES_PERIODICIDADE}
                        value={formData.tipo_acerto_entrega || ""}
                        onChange={(tipo_acerto_entrega) =>
                          setFormData((prev) => ({
                            ...prev,
                            tipo_acerto_entrega,
                            dia_semana_acerto: "",
                            dia_mes_acerto: "",
                          }))
                        }
                      />
                    </div>

                    {formData.tipo_acerto_entrega === "semanal" ? (
                      <div className="w-full max-w-[180px]">
                        <InputCombobox
                          id="pessoa-acerto-dia-semana"
                          label="Dia da semana"
                          opcoes={OPCOES_DIA_SEMANA}
                          value={formData.dia_semana_acerto || ""}
                          onChange={(dia_semana_acerto) =>
                            setFormData((prev) => ({ ...prev, dia_semana_acerto }))
                          }
                        />
                      </div>
                    ) : null}

                    {formData.tipo_acerto_entrega === "mensal" ? (
                      <div className="w-full max-w-[160px]">
                        <InputQuantidade
                          id="pessoa-acerto-dia-mes"
                          label="Dia do mês (1 a 28)"
                          min={1}
                          value={formData.dia_mes_acerto || ""}
                          onChange={(dia_mes_acerto) =>
                            setFormData((prev) => ({ ...prev, dia_mes_acerto }))
                          }
                        />
                      </div>
                    ) : null}
                  </div>

                  {formData.tipo_acerto_entrega === "quinzenal" ? (
                    <p className="rounded bg-blue-100 p-2 text-xs text-blue-800 dark:bg-blue-500/15 dark:text-blue-200">
                      Acerto nos dias <strong>1</strong> e <strong>15</strong>
                    </p>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

      <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-500/30 dark:bg-emerald-500/10">
        <InputRadio
          name="pessoa-parceiro-ativo"
          label="Ativar como parceiro (comissões)?"
          opcoes={OPCOES_SIM_NAO}
          value={formData.parceiro_ativo ? "sim" : "nao"}
          onChange={(valor) => {
            const parceiro_ativo = valor === "sim";
            setFormData((prev) => ({
              ...prev,
              parceiro_ativo,
              parceiro_desde:
                parceiro_ativo && !prev.parceiro_desde
                  ? new Date().toISOString().split("T")[0]
                  : prev.parceiro_desde || "",
            }));
          }}
        />
        <p className="mt-1 text-xs text-slate-500">
          Ao ativar, esta pessoa poderá receber comissões de vendas, independente do tipo de
          cadastro.
        </p>
        {formData.parceiro_ativo ? (
          <div className="mt-3">
            <InputTextoLongo
              id="pessoa-parceiro-observacoes"
              label="Observações do parceiro (opcional)"
              linhas={2}
              value={formData.parceiro_observacoes}
              onChange={(parceiro_observacoes) =>
                setFormData((prev) => ({ ...prev, parceiro_observacoes }))
              }
              placeholder="Ex: Especialista em produtos de higiene..."
            />
          </div>
        ) : null}
      </section>
      </div>
    </div>
  );
}
