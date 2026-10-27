import { useEffect, useState } from "react";
import { buscarClientes } from "../../api/clientes";
import BuscaPessoa from "../v2/BuscaPessoa/BuscaPessoa";
import InputTexto from "../v2/InputTexto/InputTexto";
import InputData from "../v2/InputData/InputData";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import { Printer, X } from "lucide-react";
import { safeArray } from "../../utils/safeArray";
import { calcularSaldoFinanceiro } from "../../utils/financeiroStatus";
import { obterCodigoPessoaPublico } from "../../utils/codigosPublicos";
import RecebimentoCampos from "../v2/RecebimentoCampos/RecebimentoCampos";
import InputCheck from "../v2/InputCheck/InputCheck";
import InputMoeda from "../v2/InputMoeda/InputMoeda";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import ActionButton from "../ui/ActionButton";
import CustomerIdentity from "../ui/CustomerIdentity";
import DataTable from "../ui/DataTable";
import FilterBar from "../ui/FilterBar";
import MoneyCell from "../ui/MoneyCell";
import StatusBadge from "../ui/StatusBadge";

export function ContasReceberFilters({
  aplicarFiltros,
  aplicarPeriodoRapido,
  busca,
  clientes,
  filtros,
  handleFiltrosSubmit,
  setBusca,
  setFiltros,
}) {
  const [termoPessoa, setTermoPessoa] = useState("");
  const [sugestoes, setSugestoes] = useState([]);
  const [buscandoPessoa, setBuscandoPessoa] = useState(false);
  useEffect(() => {
    if (!filtros.cliente_id) return;
    const pessoa = safeArray(clientes).find((p) => String(p.id) === String(filtros.cliente_id));
    if (pessoa) setTermoPessoa([pessoa.codigo, pessoa.nome].filter(Boolean).join(" · "));
  }, [filtros.cliente_id, clientes]);
  useEffect(() => {
    let ativo = true;
    const controller = new AbortController();
    if (!termoPessoa.trim() || filtros.cliente_id) {
      setSugestoes([]);
      return;
    }
    setBuscandoPessoa(true);
    const timer = setTimeout(
      () =>
        buscarClientes({ search: termoPessoa.trim(), limit: 20 }, { signal: controller.signal })
          .then((pessoas) => {
            if (ativo) setSugestoes(safeArray(pessoas));
          })
          .catch(() => {
            if (ativo) setSugestoes([]);
          })
          .finally(() => {
            if (ativo) setBuscandoPessoa(false);
          }),
      300,
    );
    return () => {
      ativo = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [termoPessoa, filtros.cliente_id]);
  return (
    <FilterBar className="mb-6" onSubmit={handleFiltrosSubmit}>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {[
          ["todos", "Todos os períodos"],
          ["vencidas", "Vencidas"],
          ["a_vencer", "A vencer"],
        ].map(([id, texto]) => (
          <BotaoInteracao key={id} tamanho="pequeno" onClick={() => aplicarPeriodoRapido(id)}>
            {texto}
          </BotaoInteracao>
        ))}
      </div>
      <InputTexto
        label="Buscar conta ou documento"
        value={busca}
        onChange={setBusca}
        placeholder="Descrição, venda ou documento"
      />
      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-4">
        <InputCombobox
          id="receber-filtro-status"
          label="Status"
          value={filtros.status}
          permitirLimpar={false}
          opcoes={[
            ["todos", "Todos"],
            ["em_aberto", "Em aberto"],
            ["pendente", "Pendente"],
            ["parcial", "Parcial"],
            ["recebido", "Recebido"],
            ["vencido", "Vencido"],
            ["cancelado", "Cancelado"],
          ].map(([value, label]) => ({ value, label }))}
          onChange={(status) => setFiltros((atual) => ({ ...atual, status }))}
        />
        <BuscaPessoa
          label="Cliente"
          value={termoPessoa}
          loading={buscandoPessoa}
          suggestions={sugestoes}
          showSuggestions
          onChange={(termo) => {
            setTermoPessoa(termo);
            setFiltros((atual) => ({ ...atual, cliente_id: null }));
          }}
          onSelect={(pessoa) => {
            setTermoPessoa([pessoa.codigo, pessoa.nome].filter(Boolean).join(" · "));
            setSugestoes([]);
            setFiltros((atual) => ({ ...atual, cliente_id: pessoa.id }));
          }}
        />
        <InputData
          label="Data inicial"
          value={filtros.data_inicio}
          onChange={(data_inicio) => setFiltros((atual) => ({ ...atual, data_inicio }))}
        />
        <InputData
          label="Data final"
          value={filtros.data_fim}
          onChange={(data_fim) => setFiltros((atual) => ({ ...atual, data_fim }))}
        />
      </div>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <InputCheck
          id="receber-so-vencidas"
          label="Só vencidas"
          checked={filtros.apenas_vencidas}
          onChange={(checked) =>
            setFiltros((atual) => ({ ...atual, apenas_vencidas: checked, apenas_vencer: false }))
          }
        />
        <InputCheck
          id="receber-a-vencer"
          label="A vencer"
          checked={filtros.apenas_vencer}
          onChange={(checked) =>
            setFiltros((atual) => ({ ...atual, apenas_vencer: checked, apenas_vencidas: false }))
          }
        />
        <BotaoInteracao onClick={aplicarFiltros}>Filtrar</BotaoInteracao>
      </div>
    </FilterBar>
  );
}

export function ContasReceberRecebimentoModal({
  calculoEncargos,
  contaSelecionada,
  dadosRecebimento,
  formasPagamento,
  formatarMoeda,
  mostrarModalRecebimento,
  registrarRecebimento,
  setDadosRecebimento,
  setMostrarModalRecebimento,
  onDataRecebimentoChange,
  processando = false,
}) {
  if (!mostrarModalRecebimento || !contaSelecionada) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <section
        role="dialog"
        aria-modal="true"
        aria-label="Registrar recebimento"
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900"
      >
        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
          Registrar recebimento
        </h2>
        <p className="my-3 text-sm text-slate-700 dark:text-slate-300">
          {contaSelecionada.descricao} · Saldo:{" "}
          {formatarMoeda(calcularSaldoFinanceiro(contaSelecionada, "valor_recebido"))}
        </p>
        {calculoEncargos?.eh_crediario && (
          <div className="mb-4">
            <InputCheck
              id="recebimento-encargos"
              label="Aplicar encargos automáticos"
              checked={Boolean(dadosRecebimento.aplicar_encargos_automaticos)}
              disabled={!calculoEncargos.encargos_automaticos_ativos || processando}
              onChange={(checked) =>
                setDadosRecebimento((atual) => ({
                  ...atual,
                  aplicar_encargos_automaticos: checked,
                  valor_recebido: Number(
                    checked ? calculoEncargos.saldo_atualizado : calculoEncargos.saldo_atual,
                  ),
                }))
              }
            />
          </div>
        )}
        <RecebimentoCampos
          value={dadosRecebimento}
          onChange={setDadosRecebimento}
          onDataChange={onDataRecebimentoChange}
          formas={formasPagamento}
          disabled={processando}
        />
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {[
            ["valor_juros", "Juros"],
            ["valor_multa", "Multa"],
            ["valor_desconto", "Desconto"],
          ].map(([campo, label]) => (
            <InputMoeda
              key={campo}
              label={label}
              value={dadosRecebimento[campo] || 0}
              disabled={
                processando ||
                (campo !== "valor_desconto" && dadosRecebimento.aplicar_encargos_automaticos)
              }
              onChange={(valor) => setDadosRecebimento((atual) => ({ ...atual, [campo]: valor }))}
            />
          ))}
        </div>
        <div className="my-4">
          <InputCheck
            id="recebimento-quitar"
            label="Quitar o saldo inteiro"
            checked={Boolean(dadosRecebimento.quitar)}
            disabled={processando}
            onChange={(checked) =>
              setDadosRecebimento((atual) => ({
                ...atual,
                quitar: checked,
                valor_recebido: checked
                  ? Number(
                      atual.aplicar_encargos_automaticos
                        ? calculoEncargos?.saldo_atualizado
                        : calculoEncargos?.saldo_atual,
                    )
                  : atual.valor_recebido,
              }))
            }
          />
        </div>
        <div className="mt-5 flex justify-end gap-3">
          <BotaoCancelar onClick={() => setMostrarModalRecebimento(false)} disabled={processando}>
            Cancelar
          </BotaoCancelar>
          <BotaoSalva
            onClick={registrarRecebimento}
            loading={processando}
            disabled={!dadosRecebimento.caixa_id || !dadosRecebimento.forma_pagamento_id}
          >
            Confirmar recebimento
          </BotaoSalva>
        </div>
      </section>
    </div>
  );
}

export function ContasReceberRecebimentoLoteModal({
  contasSelecionadas,
  dadosRecebimento,
  formasPagamento,
  formatarMoeda,
  mostrar,
  onConfirmar,
  onFechar,
  setDadosRecebimento,
  processando = false,
}) {
  if (!mostrar) return null;
  const saldo = safeArray(contasSelecionadas).reduce(
    (total, conta) =>
      total +
      Number(
        dadosRecebimento.aplicar_encargos_automaticos
          ? conta.saldo_atualizado
          : Number(conta.valor_final || 0) - Number(conta.valor_recebido || 0),
      ),
    0,
  );
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <section
        role="dialog"
        aria-modal="true"
        aria-label="Receber contas selecionadas"
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900"
      >
        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
          Receber contas selecionadas
        </h2>
        <p className="my-3 text-sm text-slate-700 dark:text-slate-300">
          {safeArray(contasSelecionadas).length} conta(s) · Total: {formatarMoeda(saldo)}
        </p>
        <RecebimentoCampos
          value={{ ...dadosRecebimento, valor_recebido: saldo }}
          onChange={setDadosRecebimento}
          formas={formasPagamento}
          mostrarValor={false}
          disabled={processando}
        />
        <div className="mt-4">
          <InputCheck
            id="recebimento-lote-encargos"
            label="Aplicar encargos automáticos do crediário"
            checked={Boolean(dadosRecebimento.aplicar_encargos_automaticos)}
            disabled={processando}
            onChange={(checked) =>
              setDadosRecebimento((atual) => ({ ...atual, aplicar_encargos_automaticos: checked }))
            }
          />
        </div>
        <div className="mt-5 flex justify-end gap-3">
          <BotaoCancelar onClick={onFechar} disabled={processando}>
            Cancelar
          </BotaoCancelar>
          <BotaoSalva
            onClick={onConfirmar}
            loading={processando}
            disabled={!dadosRecebimento.caixa_id || !dadosRecebimento.forma_pagamento_id}
          >
            Confirmar recebimento
          </BotaoSalva>
        </div>
      </section>
    </div>
  );
}

export function ContasReceberDetalhesModal({
  abrirFluxoDeCaixa,
  abrirVenda,
  contaSelecionada,
  detalhesCompletos,
  formatarData,
  formatarMoeda,
  mostrarDetalhes,
  onEmitirComprovante,
  setMostrarDetalhes,
}) {
  return (
    <>
      {/* Modal Detalhes */}
      {mostrarDetalhes && contaSelecionada && detalhesCompletos && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="bg-blue-600 text-white px-6 py-4 flex justify-between items-center sticky top-0">
              <h3 className="text-xl font-semibold">Detalhes da Conta</h3>
              <ActionButton
                onClick={() => setMostrarDetalhes(false)}
                intent="neutral"
                tone="ghost"
                size="sm"
                icon={X}
                className="text-white hover:bg-blue-700"
                aria-label="Fechar detalhes"
              />
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Numero da Conta</label>
                  <p className="mt-1 text-lg">{contaSelecionada.numero_documento || "N/A"}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Cliente</label>
                  <p className="mt-1 text-lg">
                    <CustomerIdentity
                      code={obterCodigoPessoaPublico(detalhesCompletos) || "—"}
                      customer={detalhesCompletos.cliente}
                      fallback="N/A"
                    />
                  </p>
                </div>
              </div>

              {/* Numero do Pedido - Clicavel */}
              {detalhesCompletos.venda && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Pedido/Venda
                  </label>
                  <div className="flex gap-2">
                    <ActionButton
                      onClick={() => abrirVenda(detalhesCompletos.venda.id)}
                      intent="edit"
                      tone="soft"
                      size="md"
                      className="flex-1"
                    >
                      <span className="text-xl">Venda</span>
                      <span className="font-semibold">{detalhesCompletos.venda.numero_venda}</span>
                    </ActionButton>
                    <ActionButton
                      onClick={() => abrirFluxoDeCaixa(contaSelecionada)}
                      intent="create"
                      tone="soft"
                      size="md"
                      title="Ver no Fluxo de Caixa"
                    >
                      <span className="text-xl">Fluxo</span>
                      <span className="text-sm">Fluxo</span>
                    </ActionButton>
                  </div>
                </div>
              )}

              {!detalhesCompletos.venda && (
                <div>
                  <ActionButton
                    onClick={() => abrirFluxoDeCaixa(contaSelecionada)}
                    intent="create"
                    tone="soft"
                    size="md"
                    className="w-full"
                  >
                    <span className="text-xl">Fluxo</span>
                    <span className="font-medium">Ver no Fluxo de Caixa</span>
                  </ActionButton>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Data de Emissao</label>
                  <p className="mt-1">{formatarData(detalhesCompletos.datas.emissao)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Data de Vencimento
                  </label>
                  <p className="mt-1">{formatarData(detalhesCompletos.datas.vencimento)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Valor Original</label>
                  <p className="mt-1 text-lg font-semibold text-blue-600">
                    {formatarMoeda(detalhesCompletos.valores.final)}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Valor Recebido</label>
                  <p className="mt-1 text-lg font-semibold text-green-600">
                    {formatarMoeda(detalhesCompletos.valores.recebido)}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Saldo Restante</label>
                  <p className="mt-1 text-lg font-semibold text-red-600">
                    {formatarMoeda(
                      calcularSaldoFinanceiro(
                        {
                          status: detalhesCompletos.status,
                          valor_final: detalhesCompletos.valores.final,
                          valor_recebido: detalhesCompletos.valores.recebido,
                        },
                        "valor_recebido",
                      ),
                    )}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Status</label>
                  <p className="mt-1">
                    <StatusBadge status={detalhesCompletos.status} />
                  </p>
                </div>
              </div>

              {/* Recebimentos com Conta Bancaria */}
              {detalhesCompletos.recebimentos && detalhesCompletos.recebimentos.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Historico de Recebimentos
                  </label>
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <DataTable
                      columns={[
                        {
                          key: "data",
                          header: "Data",
                          render: (recebimento) => formatarData(recebimento.data),
                        },
                        {
                          key: "valor",
                          header: "Valor",
                          align: "right",
                          className: "font-semibold text-green-600",
                          render: (recebimento) => (
                            <MoneyCell value={recebimento.valor} zeroAsDash />
                          ),
                        },
                        {
                          key: "conta",
                          header: "Conta Bancaria",
                          render: (recebimento) =>
                            recebimento.conta_bancaria_nome ? (
                              <span className="rounded bg-blue-50 px-2 py-1 text-xs text-blue-700">
                                {recebimento.conta_bancaria_nome}
                              </span>
                            ) : (
                              <span className="text-xs text-gray-400">Nao informada</span>
                            ),
                        },
                        {
                          key: "observacoes",
                          header: "Observações",
                          render: (recebimento) => recebimento.observacoes || "—",
                        },
                        {
                          key: "comprovante",
                          header: "Comprovante",
                          align: "right",
                          render: (recebimento) => (
                            <ActionButton
                              type="button"
                              onClick={() => onEmitirComprovante(recebimento)}
                              icon={Printer}
                              intent="neutral"
                              tone="soft"
                              size="xs"
                            >
                              Emitir
                            </ActionButton>
                          ),
                        },
                      ]}
                      data={safeArray(detalhesCompletos?.recebimentos)}
                      getRowKey={(recebimento, index) => recebimento.id || index}
                      tableClassName="w-full"
                      theadClassName="bg-gray-50"
                      tbodyClassName="divide-y divide-gray-200"
                    />
                  </div>
                </div>
              )}

              {detalhesCompletos.observacoes && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Observacoes</label>
                  <p className="mt-1 text-gray-600">{detalhesCompletos.observacoes}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
