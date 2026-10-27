import { Coins, PackagePlus } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../../platformApi";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import InputQuantidade from "../../components/v2/InputQuantidade/InputQuantidade";
import {
  ROTULO_DA_COMPRA,
  ROTULO_DO_NIVEL,
  formatarCreditos,
  formatarQuando,
  formatarReais,
} from "../../utils/consumoWhatsapp";
import { AjusteModal, ControleModal, PacoteModal } from "./OpsCreditosModais";

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

function Bloco({ id, titulo, acao, children }) {
  return (
    <section
      aria-labelledby={id}
      className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
    >
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 id={id} className="text-base font-bold text-slate-950 dark:text-slate-100">
          {titulo}
        </h2>
        {acao}
      </div>
      {children}
    </section>
  );
}

function CampoDeCusto({ item, onSalvar }) {
  const [valor, setValor] = useState(item.creditos);
  return (
    <li className="flex flex-wrap items-end justify-between gap-2">
      <span className="text-sm">
        {item.rotulo}
        <span className="block text-xs text-slate-500 dark:text-slate-400">
          padrão {item.padrao}
        </span>
      </span>
      <div className="flex items-end gap-2">
        <div className="w-28">
          <InputQuantidade
            id={`custo-${item.chave}`}
            label="Créditos"
            min={0}
            value={valor}
            onChange={setValor}
          />
        </div>
        <BotaoInteracao
          tamanho="pequeno"
          disabled={valor === item.creditos}
          onClick={() => onSalvar(item.chave, valor)}
        >
          Salvar
        </BotaoInteracao>
      </div>
    </li>
  );
}

export default function OpsCreditosWhatsAppPage() {
  const [versao, setVersao] = useState(0);
  // Um único loading do início até os dados aparecerem.
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [dados, setDados] = useState(null);
  const [modal, setModal] = useState(null); // { tipo: "pacote" | "controle" | "ajuste", loja? }

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const { data } = await api.get("/admin/whatsapp-creditos");
        if (!ativo) return;
        setDados(data);
        setErro("");
      } catch (error) {
        if (ativo) setErro(mensagemDeErro(error, "Não foi possível carregar os créditos."));
      } finally {
        if (ativo) setCarregando(false);
      }
    })();
    return () => {
      ativo = false;
    };
  }, [versao]);

  const recarregar = () => setVersao((atual) => atual + 1);

  const executar = async (chamada, sucesso) => {
    try {
      await chamada();
      toast.success(sucesso);
      recarregar();
    } catch (error) {
      toast.error(mensagemDeErro(error, "Não foi possível concluir."));
    }
  };

  const pendentes = (dados?.compras || []).filter((compra) => compra.status === "pendente");

  return (
    <div className="mx-auto w-full max-w-6xl space-y-4 p-4 sm:p-6">
      <header>
        <p className="m-0 text-xs font-bold uppercase tracking-[0.18em] text-teal-700 dark:text-teal-300">
          Plataforma
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-950 dark:text-slate-100 sm:text-3xl">
          Créditos de WhatsApp
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600 dark:text-slate-400">
          Cada loja tem uma franquia mensal e pode comprar pacotes avulsos. Com o controle ligado,
          quando os créditos acabam a IA e os envios param até a compra de um pacote. O controle
          começa desligado em todas as lojas.
        </p>
      </header>

      {erro ? (
        <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
          {erro}
        </p>
      ) : null}

      {carregando ? (
        <div
          role="status"
          aria-label="Carregando"
          className="h-40 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900"
        />
      ) : dados ? (
        <>
          <Bloco id="ops-pedidos" titulo={`Pedidos aguardando pagamento (${pendentes.length})`}>
            {pendentes.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">Nenhum pedido pendente.</p>
            ) : (
              <ul className="space-y-2">
                {pendentes.map((compra) => (
                  <li
                    key={compra.id}
                    className="flex flex-wrap items-center justify-between gap-2 text-sm"
                  >
                    <span>
                      <strong>{compra.loja_nome || compra.loja_id}</strong> · {compra.pacote_nome} ·{" "}
                      {formatarCreditos(compra.creditos)} · {formatarReais(compra.preco)} ·{" "}
                      {formatarQuando(compra.solicitado_em)} · por {compra.solicitado_por}
                    </span>
                    <span className="flex gap-2">
                      <BotaoInteracao
                        tamanho="pequeno"
                        onClick={() =>
                          executar(
                            () =>
                              api.post(
                                `/admin/whatsapp-creditos/compras/${compra.id}/confirmar`,
                                {},
                              ),
                            "Pagamento confirmado e créditos liberados.",
                          )
                        }
                      >
                        Confirmar pagamento
                      </BotaoInteracao>
                      <BotaoInteracao
                        tamanho="pequeno"
                        onClick={() =>
                          executar(
                            () =>
                              api.post(`/admin/whatsapp-creditos/compras/${compra.id}/cancelar`),
                            "Pedido cancelado.",
                          )
                        }
                      >
                        Cancelar
                      </BotaoInteracao>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Bloco>

          <Bloco id="ops-lojas-creditos" titulo="Lojas">
            {dados.lojas.length === 0 ? (
              <EstadoVazio icone={Coins} titulo="Nenhuma loja com WhatsApp configurado" />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[800px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                      <th className="py-2 pr-3 font-semibold">Ações</th>
                      <th className="py-2 pr-3 font-semibold">Loja</th>
                      <th className="py-2 pr-3 font-semibold">Controle</th>
                      <th className="py-2 pr-3 font-semibold">Franquia (restante / mês)</th>
                      <th className="py-2 pr-3 font-semibold">Avulsos</th>
                      <th className="py-2 font-semibold">Situação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dados.lojas.map((loja) => (
                      <tr
                        key={loja.loja_id}
                        className="border-b border-slate-100 dark:border-slate-800"
                      >
                        <td className="py-2 pr-3">
                          <span className="flex gap-2">
                            <BotaoInteracao
                              tamanho="pequeno"
                              onClick={() => setModal({ tipo: "controle", loja })}
                            >
                              Controle
                            </BotaoInteracao>
                            <BotaoInteracao
                              tamanho="pequeno"
                              onClick={() => setModal({ tipo: "ajuste", loja })}
                            >
                              Ajustar
                            </BotaoInteracao>
                          </span>
                        </td>
                        <td className="py-2 pr-3 font-medium">{loja.loja_nome}</td>
                        <td className="py-2 pr-3">
                          {loja.controle_ativo ? "Ligado" : "Desligado"}
                        </td>
                        <td className="py-2 pr-3">
                          {loja.franquia_restante} / {loja.franquia_mensal}
                        </td>
                        <td className="py-2 pr-3">{loja.avulso}</td>
                        <td className="py-2">{ROTULO_DO_NIVEL[loja.nivel]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Bloco>

          <div className="grid gap-4 lg:grid-cols-2">
            <Bloco
              id="ops-pacotes"
              titulo="Pacotes avulsos"
              acao={
                <BotaoInteracao
                  icon={PackagePlus}
                  tamanho="pequeno"
                  onClick={() => setModal({ tipo: "pacote" })}
                >
                  Novo pacote
                </BotaoInteracao>
              }
            >
              {dados.pacotes.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Nenhum pacote. Sem pacotes, a loja sem créditos não consegue comprar.
                </p>
              ) : (
                <ul className="space-y-2">
                  {dados.pacotes.map((pacote) => (
                    <li
                      key={pacote.id}
                      className="flex flex-wrap items-center justify-between gap-2 text-sm"
                    >
                      <span>
                        <strong>{pacote.nome}</strong> · {formatarCreditos(pacote.creditos)} ·{" "}
                        {formatarReais(pacote.preco)} · {pacote.ativo ? "À venda" : "Desativado"}
                      </span>
                      <BotaoInteracao
                        tamanho="pequeno"
                        onClick={() =>
                          executar(
                            () =>
                              api.patch(`/admin/whatsapp-creditos/pacotes/${pacote.id}`, {
                                ativo: !pacote.ativo,
                              }),
                            pacote.ativo ? "Pacote desativado." : "Pacote reativado.",
                          )
                        }
                      >
                        {pacote.ativo ? "Desativar" : "Reativar"}
                      </BotaoInteracao>
                    </li>
                  ))}
                </ul>
              )}
            </Bloco>

            <Bloco id="ops-custos" titulo="Quanto cada envio consome">
              <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
                Os valores padrão são de exemplo até fecharmos o modelo de cobrança. Mudar aqui vale
                para os próximos envios de todas as lojas.
              </p>
              <ul className="space-y-3">
                {dados.custos.map((item) => (
                  <CampoDeCusto
                    key={`${item.chave}-${item.creditos}`}
                    item={item}
                    onSalvar={(chave, valor) =>
                      executar(
                        () =>
                          api.put(`/admin/whatsapp-creditos/custos/${chave}`, { creditos: valor }),
                        "Custo atualizado.",
                      )
                    }
                  />
                ))}
              </ul>
            </Bloco>
          </div>

          <Bloco id="ops-historico-compras" titulo="Pedidos já resolvidos">
            {(dados.compras || []).filter((c) => c.status !== "pendente").length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Nenhum pedido resolvido ainda.
              </p>
            ) : (
              <ul className="space-y-1 text-sm">
                {dados.compras
                  .filter((c) => c.status !== "pendente")
                  .map((compra) => (
                    <li key={compra.id}>
                      {formatarQuando(compra.confirmado_em || compra.solicitado_em)} ·{" "}
                      {compra.loja_nome || compra.loja_id} · {compra.pacote_nome} ·{" "}
                      {formatarCreditos(compra.creditos)} · {ROTULO_DA_COMPRA[compra.status]}
                      {compra.confirmado_por ? ` por ${compra.confirmado_por}` : ""}
                    </li>
                  ))}
              </ul>
            )}
          </Bloco>
        </>
      ) : null}

      {modal?.tipo === "pacote" ? (
        <PacoteModal
          onFechar={() => setModal(null)}
          onSalvo={() => {
            setModal(null);
            toast.success("Pacote criado.");
            recarregar();
          }}
        />
      ) : null}
      {modal?.tipo === "controle" ? (
        <ControleModal
          loja={modal.loja}
          onFechar={() => setModal(null)}
          onSalvo={() => {
            setModal(null);
            toast.success("Controle atualizado.");
            recarregar();
          }}
        />
      ) : null}
      {modal?.tipo === "ajuste" ? (
        <AjusteModal
          loja={modal.loja}
          onFechar={() => setModal(null)}
          onSalvo={() => {
            setModal(null);
            toast.success("Ajuste aplicado.");
            recarregar();
          }}
        />
      ) : null}
    </div>
  );
}
