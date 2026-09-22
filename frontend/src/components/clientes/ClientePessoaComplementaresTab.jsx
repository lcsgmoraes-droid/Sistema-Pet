import { AlertTriangle, Plus, Trash2 } from "lucide-react";
import { FiDollarSign } from "react-icons/fi";
import { buildEmptyClienteAlertaPdv } from "../../utils/clienteAlertasPdv";
import ActionButton from "../ui/ActionButton";
import ClientePessoaAcessoAppCard from "./ClientePessoaAcessoAppCard";
import InputCheckTexto from "../v2/InputCheckTexto/InputCheckTexto";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputMoeda from "../v2/InputMoeda/InputMoeda";
import InputQuantidade from "../v2/InputQuantidade/InputQuantidade";
import InputTexto from "../v2/InputTexto/InputTexto";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";

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

const OPCOES_PRIORIDADE_ALERTA = [
  { value: "aviso", label: "Aviso" },
  { value: "importante", label: "Importante" },
  { value: "info", label: "Info" },
];

export default function ClientePessoaComplementaresTab({
  formData,
  loadingUsuariosAcessoApp,
  rolesAcessoApp,
  setFormData,
  usuariosAcessoApp,
}) {
  const alertasPdv = Array.isArray(formData.alertas_pdv) ? formData.alertas_pdv : [];

  const setAlertasPdv = (alertas) => setFormData((prev) => ({ ...prev, alertas_pdv: alertas }));

  const atualizarAlerta = (index, campo, valor) => {
    setAlertasPdv(
      alertasPdv.map((alerta, alertaIndex) =>
        alertaIndex === index ? { ...alerta, [campo]: valor } : alerta,
      ),
    );
  };

  const mostrarEntrega =
    formData.tipo_cadastro === "funcionario" || formData.tipo_cadastro === "fornecedor";

  return (
    <div className="space-y-6">
      {mostrarEntrega ? (
        <section className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-500/30 dark:bg-blue-500/10">
          <InputCheckTexto
            id="pessoa-is-entregador"
            checked={formData.is_entregador || false}
            onChange={(marcado) => {
              setFormData((prev) => {
                const perfis = new Set(prev.app_access_profiles || []);
                if (marcado) perfis.add("entregador");
                else perfis.delete("entregador");
                return { ...prev, is_entregador: marcado, app_access_profiles: Array.from(perfis) };
              });
            }}
          >
            <span className="text-sm font-medium text-slate-800 dark:text-slate-200">
              É entregador
            </span>
          </InputCheckTexto>

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

              {formData.tipo_cadastro === "funcionario" ? (
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

              {formData.tipo_cadastro === "fornecedor" ||
              (formData.tipo_cadastro === "funcionario" && !formData.controla_rh) ? (
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
        <div className="flex items-center gap-2">
          <FiDollarSign className="text-emerald-700 dark:text-emerald-300" size={18} />
          <InputCheckTexto
            id="pessoa-parceiro-ativo"
            checked={formData.parceiro_ativo || false}
            onChange={(parceiro_ativo) =>
              setFormData((prev) => ({
                ...prev,
                parceiro_ativo,
                parceiro_desde:
                  parceiro_ativo && !prev.parceiro_desde
                    ? new Date().toISOString().split("T")[0]
                    : prev.parceiro_desde || "",
              }))
            }
          >
            <span className="text-sm font-medium text-slate-800 dark:text-slate-200">
              Ativar como parceiro (comissões)
            </span>
            <span className="mt-0.5 block text-xs text-slate-500">
              Ao ativar, esta pessoa poderá receber comissões de vendas, independente do tipo de
              cadastro.
            </span>
          </InputCheckTexto>
        </div>
        {formData.parceiro_ativo ? (
          <div className="mt-3 pl-7">
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

      <section>
        <div className="mb-3 flex items-center justify-between gap-3">
          <h4 className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
            <AlertTriangle className="h-4 w-4 text-amber-600" aria-hidden="true" />
            Alertas do PDV
          </h4>
          <ActionButton
            icon={Plus}
            intent="warning"
            onClick={() => setAlertasPdv([...alertasPdv, buildEmptyClienteAlertaPdv()])}
          >
            Adicionar alerta
          </ActionButton>
        </div>

        {alertasPdv.length > 0 ? (
          <div className="space-y-3">
            {alertasPdv.map((alerta, index) => (
              <div
                key={index}
                className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-500/30 dark:bg-amber-500/10"
              >
                <div className="grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,1fr)_150px_auto] md:items-start">
                  <InputTexto
                    id={`pessoa-alerta-titulo-${index}`}
                    label="Tag"
                    value={alerta.titulo || ""}
                    onChange={(titulo) => atualizarAlerta(index, "titulo", titulo)}
                    placeholder="Preço especial"
                  />
                  <InputCombobox
                    id={`pessoa-alerta-prioridade-${index}`}
                    label="Prioridade"
                    opcoes={OPCOES_PRIORIDADE_ALERTA}
                    permitirLimpar={false}
                    value={alerta.prioridade || "aviso"}
                    onChange={(prioridade) => atualizarAlerta(index, "prioridade", prioridade)}
                  />
                  <ActionButton
                    icon={Trash2}
                    intent="delete"
                    tone="ghost"
                    className="md:mt-6"
                    onClick={() =>
                      setAlertasPdv(alertasPdv.filter((_, alertaIndex) => alertaIndex !== index))
                    }
                  >
                    Remover
                  </ActionButton>
                </div>

                <div className="mt-3">
                  <InputTextoLongo
                    id={`pessoa-alerta-mensagem-${index}`}
                    label="Mensagem"
                    linhas={2}
                    value={alerta.mensagem || ""}
                    onChange={(mensagem) => atualizarAlerta(index, "mensagem", mensagem)}
                    placeholder="Cliente tem preço especial na ração X: fazer por R$ 120,00"
                  />
                </div>

                <div className="mt-2">
                  <InputCheckTexto
                    id={`pessoa-alerta-ativo-${index}`}
                    checked={alerta.ativo !== false}
                    onChange={(ativo) => atualizarAlerta(index, "ativo", ativo)}
                  >
                    <span className="text-sm text-slate-700 dark:text-slate-300">Ativo no PDV</span>
                  </InputCheckTexto>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-amber-200 bg-amber-50 px-4 py-5 text-center text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
            Nenhum alerta cadastrado
          </div>
        )}
      </section>

      <InputTextoLongo
        id="pessoa-observacoes"
        label="Observações"
        linhas={4}
        value={formData.observacoes}
        onChange={(observacoes) => setFormData((prev) => ({ ...prev, observacoes }))}
        placeholder="Informações adicionais sobre a pessoa..."
      />

      <ClientePessoaAcessoAppCard
        formData={formData}
        setFormData={setFormData}
        usuarios={usuariosAcessoApp}
        roles={rolesAcessoApp}
        loadingUsuarios={loadingUsuariosAcessoApp}
      />
    </div>
  );
}
