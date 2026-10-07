import { useEffect, useState } from "react";
import api from "../../api";
import { useAuth } from "../../contexts/AuthContext";
import InputTexto from "../v2/InputTexto/InputTexto";

function formatarData(valor) {
  if (!valor) return "-";
  const data = new Date(valor);
  return Number.isNaN(data.getTime()) ? "-" : data.toLocaleString("pt-BR");
}

export default function ProdutoHistoricoPanel({ produtoId }) {
  const { user } = useAuth();
  const [origemId, setOrigemId] = useState(null);
  const [itens, setItens] = useState([]);
  const [erro, setErro] = useState("");

  useEffect(() => {
    let ativo = true;
    Promise.all([
      api.get(`/produtos/${produtoId}`),
      api.get(`/produtos/${produtoId}/historico-alteracoes`),
    ])
      .then(([produto, historico]) => {
        if (!ativo) return;
        setOrigemId(produto.data?.origem_tenant_id ?? null);
        setItens(historico.data?.items || []);
      })
      .catch(() => {
        if (ativo) setErro("Não foi possível carregar o histórico do produto.");
      });
    return () => {
      ativo = false;
    };
  }, [produtoId]);

  const origemLabel = !origemId
    ? "-"
    : String(origemId) === String(user?.tenant?.id)
      ? user?.tenant?.login_name || user?.tenant?.name || "Loja atual"
      : "Outra loja do grupo";

  return (
    <section className="mt-6 space-y-3 rounded-xl border border-gray-200 bg-white p-4">
      <InputTexto id="produto-origem-loja" label="Loja de origem" value={origemLabel} readOnly />
      <h3 className="text-base font-semibold text-gray-900">Histórico de alterações</h3>
      {erro ? <p className="text-sm text-red-600">{erro}</p> : null}
      {!erro && itens.length === 0 ? (
        <p className="text-sm text-gray-500">Nenhuma alteração registrada ainda.</p>
      ) : null}
      {itens.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-gray-600">
                <th className="py-2 pr-4 font-medium">Quando</th>
                <th className="py-2 pr-4 font-medium">Quem</th>
                <th className="py-2 pr-4 font-medium">Campo</th>
                <th className="py-2 pr-4 font-medium">Antes</th>
                <th className="py-2 font-medium">Depois</th>
              </tr>
            </thead>
            <tbody>
              {itens.map((item, indice) => (
                <tr key={`${item.alterado_em}-${item.campo}-${indice}`} className="border-b border-gray-100">
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
