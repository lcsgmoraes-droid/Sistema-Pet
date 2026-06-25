import { Download, Printer, RefreshCw, X } from "lucide-react";

import CustomerIdentity from "../../components/ui/CustomerIdentity";
import { formatMoneyBRL } from "../../utils/formatters";
import {
  formatarDataBR,
  formatarValorDetalhe,
  getSituacaoCor,
  getSituacaoIcone,
  valorBooleanoLabel,
} from "./centralNFSaidaUtils";

function CampoDetalhe({ label, value, mono = false, destaque = false }) {
  return (
    <div>
      <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</label>
      <p
        className={`mt-1 ${mono ? "font-mono text-xs break-all" : "text-sm"} ${
          destaque ? "text-lg font-bold text-gray-900" : "text-gray-900"
        }`}
      >
        {formatarValorDetalhe(value)}
      </p>
    </div>
  );
}

function SecaoDetalhe({ titulo, children }) {
  return (
    <section className="rounded-xl border border-gray-200 bg-gray-50/60 p-4 space-y-4">
      <h4 className="text-sm font-bold text-gray-800 uppercase tracking-wide">{titulo}</h4>
      {children}
    </section>
  );
}

export default function NFSaidaDetalhesModal({
  notaSelecionada,
  detalheNota,
  carregandoDetalhe,
  erroDetalhe,
  fecharDetalhes,
  baixarDanfe,
  baixarXml,
}) {
  if (!notaSelecionada) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[92vh] overflow-y-auto m-4">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
          <h3 className="text-xl font-bold text-gray-800">
            Detalhes — NF #{notaSelecionada.numero}
          </h3>
          <button onClick={fecharDetalhes} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          {carregandoDetalhe && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800 flex items-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin" />
              Carregando detalhes completos da nota no Bling...
            </div>
          )}
          {erroDetalhe && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              {erroDetalhe}
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-600">Número</label>
              <p>{notaSelecionada.numero}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-600">Série</label>
              <p>{notaSelecionada.serie}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-600">Modelo</label>
              <p>{notaSelecionada.modelo}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-600">Tipo</label>
              <p>{notaSelecionada.tipo === "nfe" ? "NF-e" : "NFC-e"}</p>
            </div>
            <div className="col-span-2">
              <label className="text-sm font-medium text-gray-600">Chave de Acesso</label>
              <p className="text-xs break-all font-mono">{notaSelecionada.chave || "-"}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-600">Cliente</label>
              <p>
                <CustomerIdentity
                  code={
                    notaSelecionada.cliente?.codigo ||
                    notaSelecionada.cliente_id ||
                    notaSelecionada.cliente?.id
                  }
                  customer={notaSelecionada.cliente}
                  fallback="N/A"
                />
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-600">CPF/CNPJ</label>
              <p>{notaSelecionada.cliente?.cpf_cnpj}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-600">Valor Total</label>
              <p className="text-lg font-bold">{formatMoneyBRL(notaSelecionada.valor)}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-600">Situação</label>
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${getSituacaoCor(notaSelecionada.status)}`}
              >
                {getSituacaoIcone(notaSelecionada.status)}
                {notaSelecionada.status}
              </span>
            </div>
          </div>

          <SecaoDetalhe titulo="Dados fiscais">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <CampoDetalhe
                label="Data emissão"
                value={formatarDataBR(detalheNota?.data_emissao)}
              />
              <CampoDetalhe label="Hora emissão" value={detalheNota?.hora_emissao} />
              <CampoDetalhe label="Data saída" value={formatarDataBR(detalheNota?.data_saida)} />
              <CampoDetalhe label="Hora saída" value={detalheNota?.hora_saida} />
              <CampoDetalhe label="Natureza operação" value={detalheNota?.natureza_operacao} />
              <CampoDetalhe
                label="Regime tributário"
                value={detalheNota?.codigo_regime_tributario}
              />
              <CampoDetalhe label="Finalidade" value={detalheNota?.finalidade} />
              <CampoDetalhe label="Indicador presença" value={detalheNota?.indicador_presenca} />
            </div>
          </SecaoDetalhe>

          <SecaoDetalhe titulo="Loja e canal">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <CampoDetalhe label="Loja" value={detalheNota?.loja?.nome} />
              <CampoDetalhe label="Unidade negócio" value={detalheNota?.unidade_negocio?.nome} />
              <CampoDetalhe
                label="Canal venda"
                value={
                  detalheNota?.canal_label ||
                  detalheNota?.informacoes_adicionais?.origem_loja_virtual ||
                  detalheNota?.informacoes_adicionais?.origem_canal_venda ||
                  detalheNota?.canal
                }
              />
              <CampoDetalhe
                label="Origem loja virtual"
                value={
                  detalheNota?.informacoes_adicionais?.origem_loja_virtual ||
                  detalheNota?.canal_label
                }
              />
              <CampoDetalhe
                label="Origem canal venda"
                value={
                  detalheNota?.informacoes_adicionais?.origem_canal_venda ||
                  detalheNota?.canal_label
                }
              />
              <CampoDetalhe
                label="Número loja virtual"
                value={detalheNota?.informacoes_adicionais?.numero_loja_virtual}
              />
              <CampoDetalhe
                label="Número pedido loja"
                value={detalheNota?.informacoes_adicionais?.numero_pedido_loja}
              />
            </div>
          </SecaoDetalhe>

          <SecaoDetalhe titulo="Destinatário">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <CampoDetalhe label="Nome" value={detalheNota?.cliente?.nome} />
              <CampoDetalhe label="Tipo pessoa" value={detalheNota?.cliente?.tipo_pessoa} />
              <CampoDetalhe label="CPF/CNPJ" value={detalheNota?.cliente?.cpf_cnpj} />
              <CampoDetalhe label="Vendedor" value={detalheNota?.cliente?.vendedor} />
              <CampoDetalhe
                label="Consumidor final"
                value={valorBooleanoLabel(detalheNota?.cliente?.consumidor_final)}
              />
              <CampoDetalhe label="Telefone" value={detalheNota?.cliente?.telefone} />
              <CampoDetalhe label="Email" value={detalheNota?.cliente?.email} />
              <CampoDetalhe label="CEP" value={detalheNota?.cliente?.cep} />
              <CampoDetalhe label="UF" value={detalheNota?.cliente?.uf} />
              <CampoDetalhe label="Município" value={detalheNota?.cliente?.municipio} />
              <CampoDetalhe label="Bairro" value={detalheNota?.cliente?.bairro} />
              <CampoDetalhe label="Endereço" value={detalheNota?.cliente?.endereco} />
              <CampoDetalhe label="Número" value={detalheNota?.cliente?.numero} />
              <CampoDetalhe label="Complemento" value={detalheNota?.cliente?.complemento} />
            </div>
          </SecaoDetalhe>

          <SecaoDetalhe titulo="Itens da nota">
            {detalheNota?.itens?.length ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-white">
                    <tr>
                      <th className="px-3 py-2 text-left font-semibold text-gray-500">Produto</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-500">Código</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-500">UN</th>
                      <th className="px-3 py-2 text-right font-semibold text-gray-500">Qtd</th>
                      <th className="px-3 py-2 text-right font-semibold text-gray-500">Preço un</th>
                      <th className="px-3 py-2 text-right font-semibold text-gray-500">
                        Preço total
                      </th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-500">NCM</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {detalheNota.itens.map((item, index) => (
                      <tr key={`${item.codigo || item.descricao || "item"}-${index}`}>
                        <td className="px-3 py-2 text-gray-900">{item.descricao || "-"}</td>
                        <td className="px-3 py-2 text-gray-600">{item.codigo || "-"}</td>
                        <td className="px-3 py-2 text-gray-600">{item.unidade || "-"}</td>
                        <td className="px-3 py-2 text-right text-gray-900">
                          {item.quantidade || 0}
                        </td>
                        <td className="px-3 py-2 text-right text-gray-900">
                          {formatMoneyBRL(item.valor_unitario || 0)}
                        </td>
                        <td className="px-3 py-2 text-right font-semibold text-gray-900">
                          {formatMoneyBRL(item.valor_total || 0)}
                        </td>
                        <td className="px-3 py-2 text-gray-600">{item.ncm || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-gray-500">
                Nenhum item detalhado retornado para esta nota.
              </p>
            )}
          </SecaoDetalhe>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <SecaoDetalhe titulo="Totais">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <CampoDetalhe
                  label="Valor produtos"
                  value={formatMoneyBRL(detalheNota?.totais?.valor_produtos || 0)}
                />
                <CampoDetalhe
                  label="Frete"
                  value={formatMoneyBRL(detalheNota?.totais?.valor_frete || 0)}
                />
                <CampoDetalhe
                  label="Seguro"
                  value={formatMoneyBRL(detalheNota?.totais?.valor_seguro || 0)}
                />
                <CampoDetalhe
                  label="Outras despesas"
                  value={formatMoneyBRL(detalheNota?.totais?.outras_despesas || 0)}
                />
                <CampoDetalhe
                  label="Desconto"
                  value={formatMoneyBRL(detalheNota?.totais?.valor_desconto || 0)}
                />
                <CampoDetalhe
                  label="Valor total"
                  value={formatMoneyBRL(detalheNota?.totais?.valor_total || 0)}
                  destaque
                />
              </div>
            </SecaoDetalhe>

            <SecaoDetalhe titulo="Entrega e transporte">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <CampoDetalhe label="Transporte" value={detalheNota?.transporte?.tipo} />
                <CampoDetalhe
                  label="Frete por conta"
                  value={detalheNota?.transporte?.frete_por_conta}
                />
                <CampoDetalhe label="Nome entrega" value={detalheNota?.endereco_entrega?.nome} />
                <CampoDetalhe label="CEP entrega" value={detalheNota?.endereco_entrega?.cep} />
                <CampoDetalhe label="UF entrega" value={detalheNota?.endereco_entrega?.uf} />
                <CampoDetalhe
                  label="Município entrega"
                  value={detalheNota?.endereco_entrega?.municipio}
                />
                <CampoDetalhe
                  label="Bairro entrega"
                  value={detalheNota?.endereco_entrega?.bairro}
                />
                <CampoDetalhe
                  label="Endereço entrega"
                  value={detalheNota?.endereco_entrega?.endereco}
                />
                <CampoDetalhe
                  label="Número entrega"
                  value={detalheNota?.endereco_entrega?.numero}
                />
                <CampoDetalhe
                  label="Complemento entrega"
                  value={detalheNota?.endereco_entrega?.complemento}
                />
              </div>
            </SecaoDetalhe>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <SecaoDetalhe titulo="Pagamento">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <CampoDetalhe label="Condição pagamento" value={detalheNota?.pagamento?.condicao} />
                <CampoDetalhe label="Categoria" value={detalheNota?.pagamento?.categoria} />
              </div>
              {detalheNota?.pagamento?.parcelas?.length ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-white">
                      <tr>
                        <th className="px-3 py-2 text-left font-semibold text-gray-500">Dias</th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-500">Data</th>
                        <th className="px-3 py-2 text-right font-semibold text-gray-500">Valor</th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-500">Forma</th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-500">
                          Observação
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 bg-white">
                      {detalheNota.pagamento.parcelas.map((parcela, index) => (
                        <tr key={`parcela-${index}`}>
                          <td className="px-3 py-2">{parcela.dias || "-"}</td>
                          <td className="px-3 py-2">{formatarDataBR(parcela.data)}</td>
                          <td className="px-3 py-2 text-right">
                            {formatMoneyBRL(parcela.valor || 0)}
                          </td>
                          <td className="px-3 py-2">{parcela.forma || "-"}</td>
                          <td className="px-3 py-2">{parcela.observacao || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-gray-500">
                  Sem parcelas detalhadas na resposta do Bling.
                </p>
              )}
            </SecaoDetalhe>

            <SecaoDetalhe titulo="Intermediador">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <CampoDetalhe label="Intermediador" value={detalheNota?.intermediador?.ativo} />
                <CampoDetalhe label="CNPJ" value={detalheNota?.intermediador?.cnpj} />
                <CampoDetalhe
                  label="Identificação"
                  value={detalheNota?.intermediador?.identificacao}
                />
              </div>
            </SecaoDetalhe>
          </div>

          <SecaoDetalhe titulo="Informações adicionais">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <CampoDetalhe
                label="Número pedido loja"
                value={detalheNota?.informacoes_adicionais?.numero_pedido_loja}
              />
              <CampoDetalhe
                label="Número loja virtual"
                value={detalheNota?.informacoes_adicionais?.numero_loja_virtual}
              />
              <div className="md:col-span-2">
                <CampoDetalhe
                  label="Informações complementares"
                  value={detalheNota?.informacoes_adicionais?.informacoes_complementares}
                />
              </div>
              <div className="md:col-span-2">
                <CampoDetalhe
                  label="Informações de interesse do fisco"
                  value={detalheNota?.informacoes_adicionais?.informacoes_fisco}
                />
              </div>
            </div>
          </SecaoDetalhe>

          <SecaoDetalhe titulo="Pessoas autorizadas no XML">
            {detalheNota?.pessoas_autorizadas_xml?.length ? (
              <div className="flex flex-wrap gap-2">
                {detalheNota.pessoas_autorizadas_xml.map((pessoa, index) => (
                  <span
                    key={`${pessoa}-${index}`}
                    className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700"
                  >
                    {pessoa}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">
                Nenhuma pessoa autorizada retornada para esta nota.
              </p>
            )}
          </SecaoDetalhe>

          <div className="flex gap-2 pt-4">
            <button
              onClick={() => baixarDanfe(notaSelecionada.id, notaSelecionada.numero)}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
            >
              <Printer className="w-5 h-5" /> Baixar DANFE
            </button>
            <button
              onClick={() => baixarXml(notaSelecionada.id, notaSelecionada.numero)}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
            >
              <Download className="w-5 h-5" /> Baixar XML
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
