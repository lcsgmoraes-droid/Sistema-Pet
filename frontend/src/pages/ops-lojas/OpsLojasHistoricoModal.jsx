import { useEffect, useState } from "react";
import api from "../../platformApi";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
import { MODULOS_INFO } from "../../contexts/ModulosContext";
import { descreverAlteracao, formatarQuando } from "./opsLojasUtils";

// Histórico de alterações: o que mudou, valor anterior, quem fez e quando.
// Sem `loja`, mostra as últimas alterações de todas as lojas.
export default function OpsLojasHistoricoModal({ loja, nomesPorId, onFechar }) {
  const [itens, setItens] = useState(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const caminho = loja ? `/admin/lojas/${loja.id}/historico` : "/admin/lojas/historico";
        const { data } = await api.get(caminho);
        if (ativo) setItens(data.items || []);
      } catch (error) {
        const detalhe = error?.response?.data?.detail;
        if (ativo)
          setErro(typeof detalhe === "string" ? detalhe : "Não foi possível carregar o histórico.");
      }
    })();
    return () => {
      ativo = false;
    };
  }, [loja]);

  return (
    <ModalPadrao
      titulo={loja ? `Histórico · ${loja.nome}` : "Histórico de todas as lojas"}
      tamanho="grande"
      onFechar={onFechar}
      rodape={<BotaoCancelar onClick={onFechar}>Fechar</BotaoCancelar>}
    >
      {erro ? (
        <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
          {erro}
        </p>
      ) : null}
      {!itens && !erro ? (
        <p role="status" className="text-sm text-slate-500 dark:text-slate-400">
          Carregando o histórico…
        </p>
      ) : null}
      {itens && itens.length === 0 ? (
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Nenhuma alteração registrada ainda. As mudanças feitas daqui para frente aparecem aqui.
        </p>
      ) : null}
      {itens && itens.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                <th className="py-2 pr-3 font-semibold">Quando</th>
                <th className="py-2 pr-3 font-semibold">Quem</th>
                {!loja ? <th className="py-2 pr-3 font-semibold">Loja</th> : null}
                <th className="py-2 pr-3 font-semibold">O que mudou</th>
                <th className="py-2 pr-3 font-semibold">Antes</th>
                <th className="py-2 font-semibold">Depois</th>
              </tr>
            </thead>
            <tbody>
              {itens.map((item) => {
                const alteracao = descreverAlteracao(item, MODULOS_INFO);
                return (
                  <tr
                    key={item.id}
                    className="border-b border-slate-100 align-top dark:border-slate-800"
                  >
                    <td className="whitespace-nowrap py-2 pr-3">{formatarQuando(item.quando)}</td>
                    <td className="py-2 pr-3">{item.quem}</td>
                    {!loja ? (
                      <td className="py-2 pr-3">
                        {nomesPorId?.[item.tenant_id] || item.tenant_id}
                      </td>
                    ) : null}
                    <td className="py-2 pr-3">{alteracao.titulo}</td>
                    <td className="py-2 pr-3">{alteracao.antes}</td>
                    <td className="py-2 font-medium">{alteracao.depois}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </ModalPadrao>
  );
}
