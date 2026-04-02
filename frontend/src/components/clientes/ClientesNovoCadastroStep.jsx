import { FiCheck, FiDollarSign } from "react-icons/fi";

const ClientesNovoCadastroStep = ({
  formData,
  setFormData,
  setShowDuplicadoWarning,
  setClienteDuplicado,
}) => {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Informações do cadastro
      </h3>

      {/* Tipo de Cadastro */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Tipo de cadastro *
        </label>
        <div className="flex gap-4">
          <label className="flex items-center cursor-pointer">
            <input
              type="radio"
              value="cliente"
              checked={formData.tipo_cadastro === "cliente"}
              onChange={(e) => {
                // Ao selecionar cliente, volta para PF
                setFormData({
                  ...formData,
                  tipo_cadastro: e.target.value,
                  tipo_pessoa: "PF",
                });
              }}
              className="mr-2"
            />
            <span className="text-sm">Cliente</span>
          </label>
          <label className="flex items-center cursor-pointer">
            <input
              type="radio"
              value="fornecedor"
              checked={formData.tipo_cadastro === "fornecedor"}
              onChange={(e) => {
                // Ao selecionar fornecedor, muda automaticamente para PJ
                setFormData({
                  ...formData,
                  tipo_cadastro: e.target.value,
                  tipo_pessoa: "PJ",
                });
              }}
              className="mr-2"
            />
            <span className="text-sm">Fornecedor</span>
          </label>
          <label className="flex items-center cursor-pointer">
            <input
              type="radio"
              value="veterinario"
              checked={formData.tipo_cadastro === "veterinario"}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  tipo_cadastro: e.target.value,
                })
              }
              className="mr-2"
            />
            <span className="text-sm">Veterinário</span>
          </label>
          <label className="flex items-center cursor-pointer">
            <input
              type="radio"
              value="funcionario"
              checked={formData.tipo_cadastro === "funcionario"}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  tipo_cadastro: e.target.value,
                  tipo_pessoa: "PF",
                })
              }
              className="mr-2"
            />
            <span className="text-sm">Funcionário</span>
          </label>
        </div>
      </div>

      {/* 🚚 Seção de Entrega */}
      {(formData.tipo_cadastro === "funcionario" ||
        formData.tipo_cadastro === "fornecedor") && (
        <div className="bg-blue-50 p-3 rounded border border-blue-200">
          <div className="flex items-center gap-2 mb-1">
            <svg
              className="w-4 h-4 text-blue-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"
              />
            </svg>
            <label className="text-xs font-medium text-gray-700">
              É entregador
            </label>
            <label className="relative inline-flex items-center cursor-pointer ml-auto">
              <input
                type="checkbox"
                checked={formData.is_entregador || false}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    is_entregador: e.target.checked,
                  })
                }
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          {formData.is_entregador && (
            <div className="ml-5 mt-2 space-y-2 border-l-2 border-blue-300 pl-3">
              {/* Entregador Padrão */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.entregador_padrao || false}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      entregador_padrao: e.target.checked,
                    })
                  }
                  className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-xs text-gray-700 font-medium">
                  Entregador padrão
                </span>
                <span className="text-[10px] text-gray-500">
                  (pré-selecionado nas rotas)
                </span>
              </label>

              {/* CONTROLA RH - Só para funcionário */}
              {formData.tipo_cadastro === "funcionario" && (
                <div className="space-y-2">
                  <label className="flex items-start gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.controla_rh || false}
                      onChange={(e) => {
                        const controlaRH = e.target.checked;
                        setFormData({
                          ...formData,
                          controla_rh: controlaRH,
                          // Se controla RH, limpa modelo de custo E força gera_conta_pagar = false
                          modelo_custo_entrega: controlaRH
                            ? ""
                            : formData.modelo_custo_entrega,
                          taxa_fixa_entrega: controlaRH
                            ? ""
                            : formData.taxa_fixa_entrega,
                          valor_por_km_entrega: controlaRH
                            ? ""
                            : formData.valor_por_km_entrega,
                          gera_conta_pagar_custo_entrega: false, // SEMPRE false se controla RH
                        });
                      }}
                      className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-0.5"
                    />
                    <div>
                      <span className="text-xs text-gray-700 font-medium">
                        Controla RH
                      </span>
                      <p className="text-[10px] text-gray-500 mt-0.5">
                        Custo rateado na folha (não gera contas a
                        pagar)
                      </p>
                    </div>
                  </label>

                  {/* MÉDIA DE ENTREGAS POR MÊS - Só aparece se controla RH */}
                  {formData.controla_rh && (
                    <div className="ml-5 pl-3 border-l-2 border-blue-300">
                      <label className="block">
                        <span className="text-xs text-gray-700 font-medium">
                          Média de entregas por mês
                        </span>
                        <p className="text-[10px] text-gray-500 mt-0.5 mb-1">
                          Define o rateio inicial do custo do
                          funcionário por entrega. Será ajustado
                          automaticamente no final do mês.
                        </p>
                        <input
                          type="number"
                          min="1"
                          step="1"
                          value={
                            formData.media_entregas_configurada ||
                            ""
                          }
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              media_entregas_configurada:
                                e.target.value,
                            })
                          }
                          className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                          placeholder="Ex: 100 entregas/mês"
                        />
                        <p className="text-[10px] text-blue-600 mt-1">
                          💡 Exemplo: Se o custo mensal é R$ 3.000 e
                          média é 100 entregas, cada entrega custará
                          R$ 30,00 inicialmente
                        </p>
                      </label>
                    </div>
                  )}

                  {/* GERAR CONTAS A PAGAR - Só aparece se NÃO controla RH */}
                  {!formData.controla_rh && (
                    <label className="flex items-start gap-2 cursor-pointer ml-5 pl-2 border-l border-gray-300">
                      <input
                        type="checkbox"
                        checked={
                          formData.gera_conta_pagar_custo_entrega ||
                          false
                        }
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            gera_conta_pagar_custo_entrega:
                              e.target.checked,
                          })
                        }
                        className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-0.5"
                      />
                      <div>
                        <span className="text-xs text-gray-700 font-medium">
                          Gerar contas a pagar por entrega
                        </span>
                        <p className="text-[10px] text-gray-500 mt-0.5">
                          Marque se este funcionário recebe por KM
                          ou taxa fixa a cada entrega
                        </p>
                      </div>
                    </label>
                  )}
                </div>
              )}

              {/* MODELO DE CUSTO */}
              {(formData.tipo_cadastro === "fornecedor" ||
                (formData.tipo_cadastro === "funcionario" &&
                  !formData.controla_rh)) && (
                <div className="space-y-2">
                  {/* Avisos condicionais */}
                  {formData.tipo_cadastro === "fornecedor" && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded p-1.5 text-[10px] text-yellow-800">
                      ⚠️ <strong>Terceirizado</strong> - Sempre gera
                      contas a pagar
                    </div>
                  )}
                  {formData.tipo_cadastro === "funcionario" &&
                    !formData.controla_rh && (
                      <div className="bg-blue-50 border border-blue-200 rounded p-1.5 text-[10px] text-blue-800">
                        ℹ️ <strong>Funcionário sem RH</strong> -{" "}
                        {formData.gera_conta_pagar_custo_entrega
                          ? "Gera CP por entrega"
                          : "Não gera CP"}
                      </div>
                    )}

                  {/* Taxa Fixa */}
                  <label className="flex items-start gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={
                        formData.modelo_custo_entrega ===
                        "taxa_fixa"
                      }
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          modelo_custo_entrega: e.target.checked
                            ? "taxa_fixa"
                            : "",
                          valor_por_km_entrega: "",
                        })
                      }
                      className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-0.5"
                    />
                    <div className="flex-1">
                      <span className="text-xs text-gray-700 font-medium">
                        Taxa Fixa
                      </span>
                      {formData.modelo_custo_entrega ===
                        "taxa_fixa" && (
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={formData.taxa_fixa_entrega || ""}
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              taxa_fixa_entrega: e.target.value,
                            })
                          }
                          className="w-full px-2 py-1 text-xs border border-gray-300 rounded mt-1 focus:ring-1 focus:ring-blue-500"
                          placeholder="Ex: 15.00"
                        />
                      )}
                    </div>
                  </label>

                  {/* Valor por KM */}
                  <label className="flex items-start gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={
                        formData.modelo_custo_entrega === "por_km"
                      }
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          modelo_custo_entrega: e.target.checked
                            ? "por_km"
                            : "",
                          taxa_fixa_entrega: "",
                        })
                      }
                      className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-0.5"
                    />
                    <div className="flex-1">
                      <span className="text-xs text-gray-700 font-medium">
                        Valor por KM
                      </span>
                      {formData.modelo_custo_entrega ===
                        "por_km" && (
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={
                            formData.valor_por_km_entrega || ""
                          }
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              valor_por_km_entrega: e.target.value,
                            })
                          }
                          className="w-full px-2 py-1 text-xs border border-gray-300 rounded mt-1 focus:ring-1 focus:ring-blue-500"
                          placeholder="Ex: 2.50"
                        />
                      )}
                    </div>
                  </label>
                </div>
              )}

              {/* MOTO PRÓPRIA */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.moto_propria || false}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      moto_propria: e.target.checked,
                    })
                  }
                  className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-xs text-gray-700">
                  {formData.moto_propria
                    ? "✅ Moto própria"
                    : "🏢 Moto da loja"}
                </span>
              </label>

              {/* 📆 Acerto Financeiro */}
              <div className="mt-2 pt-2 border-t border-blue-200">
                <h4 className="text-xs font-semibold text-gray-700 mb-2">
                  📆 Acerto Financeiro
                </h4>
                <div className="space-y-2">
                  <div>
                    <label className="block text-[10px] font-medium text-gray-600 mb-0.5">
                      Periodicidade
                    </label>
                    <select
                      value={formData.tipo_acerto_entrega || ""}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          tipo_acerto_entrega: e.target.value,
                          dia_semana_acerto: "",
                          dia_mes_acerto: "",
                        })
                      }
                      className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                    >
                      <option value="">Selecione</option>
                      <option value="semanal">Semanal</option>
                      <option value="quinzenal">
                        Quinzenal (dias 1 e 15)
                      </option>
                      <option value="mensal">Mensal</option>
                    </select>
                  </div>

                  {formData.tipo_acerto_entrega === "semanal" && (
                    <div>
                      <label className="block text-[10px] font-medium text-gray-600 mb-0.5">
                        Dia da semana
                      </label>
                      <select
                        value={formData.dia_semana_acerto || ""}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            dia_semana_acerto: e.target.value,
                          })
                        }
                        className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                      >
                        <option value="">Selecione</option>
                        <option value="1">Segunda</option>
                        <option value="2">Terça</option>
                        <option value="3">Quarta</option>
                        <option value="4">Quinta</option>
                        <option value="5">Sexta</option>
                        <option value="6">Sábado</option>
                        <option value="7">Domingo</option>
                      </select>
                    </div>
                  )}

                  {formData.tipo_acerto_entrega === "mensal" && (
                    <div>
                      <label className="block text-[10px] font-medium text-gray-600 mb-0.5">
                        Dia do mês (1 a 28)
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="28"
                        value={formData.dia_mes_acerto || ""}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            dia_mes_acerto: e.target.value,
                          })
                        }
                        className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                        placeholder="Ex: 5"
                      />
                    </div>
                  )}

                  {formData.tipo_acerto_entrega === "quinzenal" && (
                    <div className="bg-blue-50 p-1.5 rounded text-[10px] text-blue-700">
                      ℹ️ Acerto nos dias <strong>1</strong> e{" "}
                      <strong>15</strong>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 🤝 Toggle de Parceiro (Sistema de Comissões) */}
      <div className="bg-gradient-to-r from-green-50 to-emerald-50 p-4 rounded-lg border border-green-200">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <FiDollarSign className="text-green-600" size={20} />
            <label className="text-sm font-medium text-gray-700">
              Ativar como parceiro (comissões)
            </label>

            {/* 🟢 Badge indicador de parceiro ativo */}
            {formData.parceiro_ativo && (
              <div className="flex items-center gap-1.5 px-3 py-1 bg-green-600 text-white rounded-full text-xs font-semibold animate-fade-in">
                <FiCheck size={14} className="font-bold" />
                <span>Parceiro habilitado para comissão</span>
              </div>
            )}
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={formData.parceiro_ativo}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  parceiro_ativo: e.target.checked,
                  parceiro_desde:
                    e.target.checked && !formData.parceiro_desde
                      ? new Date().toISOString().split("T")[0]
                      : formData.parceiro_desde || "",
                })
              }
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
          </label>
        </div>
        <p className="text-xs text-gray-500 ml-7">
          Ao ativar, esta pessoa poderá receber comissões de vendas,
          independente do tipo de cadastro
        </p>
        {formData.parceiro_ativo && (
          <div className="mt-3 ml-7">
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Observações do parceiro (opcional)
            </label>
            <textarea
              value={formData.parceiro_observacoes}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  parceiro_observacoes: e.target.value,
                })
              }
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent outline-none"
              placeholder="Ex: Especialista em produtos de higiene..."
              rows="2"
            />
          </div>
        )}
      </div>

      {/* Tipo de Pessoa */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {formData.tipo_pessoa === "PJ"
            ? "Tipo de pessoa jurídica *"
            : "Tipo de pessoa *"}
        </label>
        <div className="flex gap-4">
          <label className="flex items-center cursor-pointer">
            <input
              type="radio"
              value="PF"
              checked={formData.tipo_pessoa === "PF"}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  tipo_pessoa: e.target.value,
                })
              }
              className="mr-2"
            />
            <span className="text-sm">Pessoa Física</span>
          </label>
          <label className="flex items-center cursor-pointer">
            <input
              type="radio"
              value="PJ"
              checked={formData.tipo_pessoa === "PJ"}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  tipo_pessoa: e.target.value,
                })
              }
              className="mr-2"
            />
            <span className="text-sm">Pessoa Jurídica</span>
          </label>
        </div>
      </div>

      {/* Campos Pessoa Física */}
      {formData.tipo_pessoa === "PF" && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome completo *
            </label>
            <input
              type="text"
              value={formData.nome}
              onChange={(e) =>
                setFormData({ ...formData, nome: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="Digite o nome completo"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              CPF
            </label>
            <input
              type="text"
              value={formData.cpf}
              onChange={(e) => {
                setFormData({ ...formData, cpf: e.target.value });
                setShowDuplicadoWarning(false);
                setClienteDuplicado(null);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="000.000.000-00"
              maxLength="14"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Data de nascimento
            </label>
            <input
              type="date"
              value={formData.data_nascimento || ""}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  data_nascimento: e.target.value,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            />
          </div>

          {/* Campo CRMV para Veterinários */}
          {formData.tipo_cadastro === "veterinario" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                CRMV
              </label>
              <input
                type="text"
                value={formData.crmv}
                onChange={(e) => {
                  setFormData({
                    ...formData,
                    crmv: e.target.value,
                  });
                  setShowDuplicadoWarning(false);
                  setClienteDuplicado(null);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                placeholder="CRMV XX 1234"
                maxLength="20"
              />
            </div>
          )}
        </>
      )}

      {/* Campos Pessoa Jurídica */}
      {formData.tipo_pessoa === "PJ" && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Razão Social *
            </label>
            <input
              type="text"
              value={formData.razao_social}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  razao_social: e.target.value,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="Razão social da empresa"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome Fantasia *
            </label>
            <input
              type="text"
              value={formData.nome}
              onChange={(e) =>
                setFormData({ ...formData, nome: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="Nome fantasia da empresa"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                CNPJ *
              </label>
              <input
                type="text"
                value={formData.cnpj}
                onChange={(e) => {
                  setFormData({
                    ...formData,
                    cnpj: e.target.value,
                  });
                  setShowDuplicadoWarning(false);
                  setClienteDuplicado(null);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                placeholder="00.000.000/0000-00"
                maxLength="18"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Inscrição Estadual
              </label>
              <input
                type="text"
                value={formData.inscricao_estadual}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    inscricao_estadual: e.target.value,
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                placeholder="IE"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Responsável / Contato
            </label>
            <input
              type="text"
              value={formData.responsavel}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  responsavel: e.target.value,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="Nome do responsável ou contato"
            />
          </div>
        </>
      )}
    </div>
  );
};

export default ClientesNovoCadastroStep;
