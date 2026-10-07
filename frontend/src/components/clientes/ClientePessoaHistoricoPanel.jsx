import { useEffect, useState } from "react";
import api from "../../api";
import { useAuth } from "../../contexts/AuthContext";
import InputTexto from "../v2/InputTexto/InputTexto";

function formatarData(valor) {
  if (!valor) return "-";
  const data = new Date(valor);
  return Number.isNaN(data.getTime()) ? "-" : data.toLocaleString("pt-BR");
}

export default function ClientePessoaHistoricoPanel({ clienteId, origemTenantId, versao }) {
  const { user } = useAuth();
  const [itens, setItens] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  const lojaAtualId = user?.tenant?.id;
  const origemLabel =
    !origemTenantId
      ? "-"
      : String(origemTenantId) === String(lojaAtualId)
        ? user?.tenant?.login_name || user?.tenant?.name || "Loja atual"
        : "Outra loja do grupo";

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    api
      .get(`/clientes/${clienteId}/historico-alteracoes`)
      .then(({ data }) => {
        if (ativo) setItens(data.items || []);
      })
      .catch(() => {
        if (ativo) setErro("Não foi possível carregar o histórico.");
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [clienteId, versao]);

  return (
    <section className="space-y-4">
      <InputTexto id="pessoa-origem-loja" label="Loja de origem" value={origemLabel} readOnly />
      <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Histórico de alterações</h3>
      {carregando ? <p className="text-sm text-slate-500">Carregando histórico...</p> : null}
      {erro ? <p className="text-sm text-red-600">{erro}</p> : null}
      {!carregando && !erro && itens.length === 0 ? (
        <p className="text-sm text-slate-500">Nenhuma alteração registrada ainda.</p>
      ) : null}
      {itens.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-600 dark:text-slate-300">
                <th className="py-2 pr-4 font-medium">Quando</th>
                <th className="py-2 pr-4 font-medium">Quem</th>
                <th className="py-2 pr-4 font-medium">Campo</th>
                <th className="py-2 pr-4 font-medium">Antes</th>
                <th className="py-2 font-medium">Depois</th>
              </tr>
            </thead>
            <tbody>
              {itens.map((item, indice) => (
                <tr key={`${item.alterado_em}-${item.campo}-${indice}`} className="border-b border-slate-100 dark:border-slate-800">
                  <td className="py-2 pr-4">{formatarData(item.alterado_em)}</td>
                  <td className="py-2 pr-4">{item.usuario || "-"}</td>
                  <td className="py-2 pr-4">{item.campo}</td>
                  <td className="py-2 pr-4">{item.valor_anterior ?? "-"}</td>
                  <td className="py-2">{item.valor_novo ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
