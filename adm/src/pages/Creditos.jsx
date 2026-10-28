import { useEffect, useState } from "react";
import { Coins, PackagePlus } from "lucide-react";
import { alterar, enviar, obter, substituir } from "../api/cliente";
import { Aviso, Botao, Carregando, VazioComTexto } from "../components/ui";
import { Campo } from "../components/ui";
import {
  ROTULO_DA_COMPRA,
  ROTULO_DO_NIVEL,
  formatarCreditos,
  formatarQuando,
  formatarReais,
  lerNumero,
} from "../lib/whatsapp";
import { AjusteModal, ControleModal, PacoteModal } from "./CreditosModais";

function Bloco({ id, titulo, acao, children }) {
  return (
    <section
      aria-labelledby={id}
      className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id={id} className="text-base font-bold">
          {titulo}
        </h2>
        {acao}
      </div>
      {children}
    </section>
  );
}

function CampoDeCusto({ item, aoSalvar }) {
  const [valor, setValor] = useState(String(item.creditos));
  const novo = Math.floor(lerNumero(valor));
  return (
    <li className="flex flex-wrap items-end justify-between gap-2">
      <span className="text-sm">
        {item.rotulo}
        <span className="block text-xs text-slate-600 dark:text-slate-400">padrão {item.padrao}</span>
      </span>
      <div className="flex items-end gap-2">
        <div className="w-28">
          <Campo rotulo="Créditos" inputMode="numeric" value={valor} onChange={(e) => setValor(e.target.value)} />
        </div>
        <Botao variante="secundario" disabled={novo === item.creditos} onClick={() => aoSalvar(item.chave, novo)}>
          Salvar
        </Botao>
      </div>
    </li>
  );
}

export default function Creditos() {
  const [versao, setVersao] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [dados, setDados] = useState(null);
  const [modal, setModal] = useState(null); // { tipo: "pacote" | "controle" | "ajuste", loja? }

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const resposta = await obter("/admin/whatsapp-creditos");
        if (!ativo) return;
        setDados(resposta);
        setErro("");
      } catch (falha) {
        if (ativo) setErro(falha.message || "Não foi possível carregar os créditos.");
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
    setAviso("");
    setErro("");
    try {
      await chamada();
      setAviso(sucesso);
      recarregar();
    } catch (falha) {
      setErro(falha.message || "Não foi possível concluir.");
    }
  };

  const concluido = (texto) => () => {
    setModal(null);
    setAviso(texto);
    recarregar();
  };

  const compras = dados?.compras || [];
  const pendentes = compras.filter((compra) => compra.status === "pendente");
  const resolvidas = compras.filter((compra) => compra.status !== "pendente");

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-bold">Créditos de WhatsApp</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600 dark:text-slate-400">
          Cada loja tem uma franquia mensal e pode comprar pacotes avulsos. Com o controle ligado, quando os créditos
          acabam a IA e os envios param até a compra de um pacote. O controle começa desligado em todas as lojas.
        </p>
      </header>

      {erro ? <Aviso tom="erro">{erro}</Aviso> : null}
      {aviso ? <Aviso tom="ok">{aviso}</Aviso> : null}

      {carregando && !dados ? <Carregando rotulo="Carregando créditos" /> : null}

      {dados ? (
        <>
          <Bloco id="pedidos" titulo={`Pedidos aguardando pagamento (${pendentes.length})`}>
            {pendentes.length === 0 ? (
              <p className="text-sm text-slate-600 dark:text-slate-400">Nenhum pedido pendente.</p>
            ) : (
              <ul className="space-y-3">
                {pendentes.map((compra) => (
                  <li key={compra.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span>
                      <strong>{compra.loja_nome || compra.loja_id}</strong> · {compra.pacote_nome} ·{" "}
                      {formatarCreditos(compra.creditos)} · {formatarReais(compra.preco)} ·{" "}
                      {formatarQuando(compra.solicitado_em)} · por {compra.solicitado_por}
                    </span>
                    <span className="flex gap-2">
                      <Botao
                        onClick={() =>
                          executar(
                            () => enviar(`/admin/whatsapp-creditos/compras/${compra.id}/confirmar`, {}),
                            "Pagamento confirmado e créditos liberados.",
                          )
                        }
                      >
                        Confirmar pagamento
                      </Botao>
                      <Botao
                        variante="secundario"
                        onClick={() =>
                          executar(
                            () => enviar(`/admin/whatsapp-creditos/compras/${compra.id}/cancelar`),
                            "Pedido cancelado.",
                          )
                        }
                      >
                        Cancelar
                      </Botao>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Bloco>

          <Bloco id="lojas" titulo="Lojas">
            {dados.lojas.length === 0 ? (
              <VazioComTexto icone={Coins} titulo="Nenhuma loja com WhatsApp configurado" />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[800px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-400">
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
                      <tr key={loja.loja_id} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-2 pr-3">
                          <span className="flex gap-2">
                            <Botao variante="secundario" onClick={() => setModal({ tipo: "controle", loja })}>
                              Controle
                            </Botao>
                            <Botao variante="secundario" onClick={() => setModal({ tipo: "ajuste", loja })}>
                              Ajustar
                            </Botao>
                          </span>
                        </td>
                        <td className="py-2 pr-3 font-medium">{loja.loja_nome}</td>
                        <td className="py-2 pr-3">{loja.controle_ativo ? "Ligado" : "Desligado"}</td>
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
              id="pacotes"
              titulo="Pacotes avulsos"
              acao={
                <Botao variante="secundario" onClick={() => setModal({ tipo: "pacote" })}>
                  <PackagePlus className="h-4 w-4" aria-hidden="true" />
                  Novo pacote
                </Botao>
              }
            >
              {dados.pacotes.length === 0 ? (
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Nenhum pacote. Sem pacotes, a loja sem créditos não consegue comprar.
                </p>
              ) : (
                <ul className="space-y-3">
                  {dados.pacotes.map((pacote) => (
                    <li key={pacote.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                      <span>
                        <strong>{pacote.nome}</strong> · {formatarCreditos(pacote.creditos)} ·{" "}
                        {formatarReais(pacote.preco)} · {pacote.ativo ? "À venda" : "Desativado"}
                      </span>
                      <Botao
                        variante="secundario"
                        onClick={() =>
                          executar(
                            () => alterar(`/admin/whatsapp-creditos/pacotes/${pacote.id}`, { ativo: !pacote.ativo }),
                            pacote.ativo ? "Pacote desativado." : "Pacote reativado.",
                          )
                        }
                      >
                        {pacote.ativo ? "Desativar" : "Reativar"}
                      </Botao>
                    </li>
                  ))}
                </ul>
              )}
            </Bloco>

            <Bloco id="custos" titulo="Quanto cada envio consome">
              <p className="mb-3 text-xs text-slate-600 dark:text-slate-400">
                Os valores padrão são de exemplo até fecharmos o modelo de cobrança. Mudar aqui vale para os próximos
                envios de todas as lojas.
              </p>
              <ul className="space-y-3">
                {dados.custos.map((item) => (
                  <CampoDeCusto
                    key={`${item.chave}-${item.creditos}`}
                    item={item}
                    aoSalvar={(chave, valor) =>
                      executar(
                        () => substituir(`/admin/whatsapp-creditos/custos/${chave}`, { creditos: valor }),
                        "Custo atualizado.",
                      )
                    }
                  />
                ))}
              </ul>
            </Bloco>
          </div>

          <Bloco id="historico" titulo="Pedidos já resolvidos">
            {resolvidas.length === 0 ? (
              <p className="text-sm text-slate-600 dark:text-slate-400">Nenhum pedido resolvido ainda.</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {resolvidas.map((compra) => (
                  <li key={compra.id}>
                    {formatarQuando(compra.confirmado_em || compra.solicitado_em)} · {compra.loja_nome || compra.loja_id}{" "}
                    · {compra.pacote_nome} · {formatarCreditos(compra.creditos)} · {ROTULO_DA_COMPRA[compra.status]}
                    {compra.confirmado_por ? ` por ${compra.confirmado_por}` : ""}
                  </li>
                ))}
              </ul>
            )}
          </Bloco>
        </>
      ) : null}

      {modal?.tipo === "pacote" ? <PacoteModal aoFechar={() => setModal(null)} aoSalvo={concluido("Pacote criado.")} /> : null}
      {modal?.tipo === "controle" ? (
        <ControleModal loja={modal.loja} aoFechar={() => setModal(null)} aoSalvo={concluido("Controle atualizado.")} />
      ) : null}
      {modal?.tipo === "ajuste" ? (
        <AjusteModal loja={modal.loja} aoFechar={() => setModal(null)} aoSalvo={concluido("Ajuste aplicado.")} />
      ) : null}
    </div>
  );
}
