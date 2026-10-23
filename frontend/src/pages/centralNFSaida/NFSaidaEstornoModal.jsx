import { Download, FileInput, Printer, RefreshCw } from "lucide-react";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputCheckTexto from "../../components/v2/InputCheckTexto/InputCheckTexto";
import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";
import { formatMoneyBRL } from "../../utils/formatters";
import { documentosEstornoDisponiveis, obterSituacaoEstorno } from "../../utils/nfeEstorno";
import useNFSaidaEstorno from "./useNFSaidaEstorno";

function Campo({ titulo, valor }) {
  return (
    <div>
      <dt className="text-xs text-slate-500 dark:text-slate-400">{titulo}</dt>
      <dd className="mt-1 break-all text-sm font-semibold text-slate-900 dark:text-slate-100">
        {valor ?? "—"}
      </dd>
    </div>
  );
}

export default function NFSaidaEstornoModal({ nota, onFechar, onAtualizado, onBaixarDocumento }) {
  const estado = useNFSaidaEstorno({ vendaId: nota.venda_id, onAtualizado });
  const previa = estado.dados?.previa;
  const situacao = obterSituacaoEstorno(estado.dados || {});
  const docsDisponiveis = documentosEstornoDisponiveis(estado.dados || {});
  const tentativaExistente = Boolean(situacao || estado.envioIniciado);
  const bloqueios = estado.dados?.bloqueios || [];
  const fechar = () => {
    if (!estado.ocupado) onFechar();
  };

  return (
    <div role="dialog" aria-modal="true" aria-label={`NF-e de estorno da NFC-e ${nota.numero}`}>
      <ModalPadrao
        tamanho="grande"
        titulo={`NF-e de estorno — NFC-e ${nota.numero}`}
        onFechar={fechar}
        rodape={
          <>
            <BotaoCancelar onClick={fechar} disabled={estado.ocupado}>
              Fechar
            </BotaoCancelar>
            {tentativaExistente && (
              <BotaoInteracao
                icon={RefreshCw}
                onClick={estado.consultar}
                loading={estado.ocupado}
                disabled={!estado.podeConsultar}
                title={
                  !estado.podeConsultar
                    ? "Sem identificador do emissor; solicite conferência ao suporte e não reenvie."
                    : undefined
                }
              >
                Consultar estorno
              </BotaoInteracao>
            )}
            {!tentativaExistente && !estado.loading && (
              <BotaoInteracao
                icon={FileInput}
                onClick={estado.emitir}
                disabled={!estado.podeEmitir}
                loading={estado.ocupado}
              >
                Emitir NF-e de estorno
              </BotaoInteracao>
            )}
          </>
        }
      >
        {estado.loading ? (
          <p role="status" className="py-8 text-center text-slate-600 dark:text-slate-300">
            Carregando a prévia fiscal do estorno…
          </p>
        ) : (
          <div className="space-y-5">
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100">
              O estorno gera outra NF-e vinculada à NFC-e original. A nota original mantém seu
              status fiscal. Estoque e financeiro da venda não serão movimentados novamente.
            </div>
            {estado.erro && (
              <div
                role="alert"
                className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-700 dark:bg-red-950 dark:text-red-100"
              >
                {estado.erro}
              </div>
            )}
            {!tentativaExistente &&
              (estado.dados?.destinatario_anonimo || estado.dados?.requer_destinatario) && (
                <InputCheckTexto
                  id="estorno-destinatario-proprio"
                  checked={estado.destinatarioProprio}
                  onChange={estado.setDestinatarioProprio}
                  disabled={estado.ocupado}
                >
                  Usar próprio CNPJ como destinatário, conforme orientação contábil
                </InputCheckTexto>
              )}
            {bloqueios.length > 0 && (
              <div
                role="alert"
                className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-700 dark:bg-red-950 dark:text-red-100"
              >
                <p className="font-semibold">A prévia ainda possui impedimentos:</p>
                <ul className="mt-2 list-disc pl-5">
                  {bloqueios.map((bloqueio, index) => (
                    <li key={index}>
                      {typeof bloqueio === "string"
                        ? bloqueio
                        : bloqueio.mensagem || bloqueio.motivo || "Revisão fiscal necessária."}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {situacao && (
              <section className="rounded-lg border border-slate-300 p-3 dark:border-slate-700">
                <h4 className="font-semibold text-slate-900 dark:text-slate-100">
                  {situacao.label}
                </h4>
                <dl className="mt-3 grid gap-3 sm:grid-cols-2">
                  <Campo
                    titulo="Número / série do estorno"
                    valor={
                      situacao.estorno.numero
                        ? `${situacao.estorno.numero} / ${situacao.estorno.serie ?? "—"}`
                        : "Aguardando emissor"
                    }
                  />
                  <Campo titulo="Chave do estorno" valor={situacao.estorno.chave} />
                  <Campo titulo="Protocolo do estorno" valor={situacao.estorno.protocolo} />
                  <Campo
                    titulo="Código / motivo"
                    valor={
                      [situacao.estorno.codigo, situacao.detalhe].filter(Boolean).join(" — ") || "—"
                    }
                  />
                </dl>
                {docsDisponiveis && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <BotaoInteracao
                      icon={Download}
                      onClick={() => onBaixarDocumento(nota, "xml", situacao.estorno)}
                    >
                      XML do estorno
                    </BotaoInteracao>
                    <BotaoInteracao
                      icon={Printer}
                      onClick={() => onBaixarDocumento(nota, "danfe", situacao.estorno)}
                    >
                      DANFE do estorno
                    </BotaoInteracao>
                  </div>
                )}
              </section>
            )}
            {estado.envioIniciado && !situacao && (
              <p role="status" className="text-sm text-amber-900 dark:text-amber-200">
                A emissão foi enviada, mas o resultado ainda não foi confirmado. Consulte a situação
                antes de qualquer nova tentativa.
              </p>
            )}
            {previa && (
              <>
                <dl className="grid gap-4 rounded-lg bg-slate-50 p-4 dark:bg-slate-800 sm:grid-cols-2">
                  <Campo
                    titulo="Documento original"
                    valor={`NFC-e ${previa.original?.numero ?? nota.numero} — ${previa.original?.status ?? nota.status}`}
                  />
                  <Campo titulo="Chave referenciada" valor={previa.original?.chave} />
                  <Campo
                    titulo="Novo documento"
                    valor={`NF-e modelo ${previa.modelo} · Entrada · Ajuste`}
                  />
                  <Campo titulo="Ambiente" valor={previa.ambiente_label} />
                  <Campo titulo="Emitente" valor={previa.emitente?.nome} />
                  <Campo titulo="CNPJ do emitente" valor={previa.emitente?.cnpj} />
                  <Campo
                    titulo="Destinatário do estorno"
                    valor={previa.destinatario?.nome || previa.destinatario?.razaoSocial}
                  />
                  <Campo
                    titulo="CPF/CNPJ do destinatário"
                    valor={
                      previa.destinatario?.cpf_cnpj ||
                      previa.destinatario?.cnpj ||
                      previa.destinatario?.cpf
                    }
                  />
                </dl>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left text-sm text-slate-800 dark:text-slate-200">
                    <thead>
                      <tr>
                        <th className="p-2">Produto</th>
                        <th className="p-2">Qtd.</th>
                        <th className="p-2">CFOP</th>
                        <th className="p-2">Valor unit.</th>
                        <th className="p-2">Desconto</th>
                        <th className="p-2">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(previa.itens || []).map((item, index) => (
                        <tr
                          key={item.codigo_produto || index}
                          className="border-t border-slate-200 dark:border-slate-700"
                        >
                          <td className="p-2">{item.descricao}</td>
                          <td className="p-2">
                            {new Intl.NumberFormat("pt-BR").format(item.quantidade)}
                          </td>
                          <td className="p-2">{item.cfop}</td>
                          <td className="p-2">{formatMoneyBRL(item.valor_unitario)}</td>
                          <td className="p-2">{formatMoneyBRL(item.desconto)}</td>
                          <td className="p-2">{formatMoneyBRL(item.total)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <dl className="grid grid-cols-3 gap-3">
                  <Campo titulo="Produtos" valor={formatMoneyBRL(previa.totais?.produtos)} />
                  <Campo titulo="Descontos" valor={formatMoneyBRL(previa.totais?.desconto)} />
                  <Campo titulo="Total da NF-e" valor={formatMoneyBRL(previa.totais?.total)} />
                </dl>
              </>
            )}
            {!tentativaExistente && previa && (
              <>
                <InputTextoLongo
                  label="Motivo do estorno"
                  value={estado.motivo}
                  onChange={estado.setMotivo}
                  linhas={3}
                  required
                  help="Informe pelo menos 15 caracteres."
                  maxLength={500}
                  disabled={estado.ocupado}
                />
                <InputCheckTexto
                  id="declaracao-estorno-operacao"
                  checked={estado.declarado}
                  onChange={estado.setDeclarado}
                  disabled={estado.ocupado || estado.dados?.elegivel !== true}
                  required
                >
                  {previa.declaracao ||
                    "Declaro que a operação não ocorreu e que a mercadoria não saiu do estabelecimento."}
                </InputCheckTexto>
              </>
            )}
          </div>
        )}
      </ModalPadrao>
    </div>
  );
}
