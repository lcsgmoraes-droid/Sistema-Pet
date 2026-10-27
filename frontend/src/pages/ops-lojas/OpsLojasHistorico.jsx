import { useEffect, useState } from "react";
import api from "../../platformApi";
import { MODULOS_INFO } from "../../contexts/ModulosContext";
import { descreverAlteracao, formatarQuando } from "./opsLojasUtils";

// Histórico de alterações de uma loja: o que mudou, valor anterior, quem fez e quando.
export default function OpsLojasHistorico({ lojaId }) {
  const [itens, setItens] = useState(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const { data } = await api.get(`/admin/lojas/${lojaId}/historico`);
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
  }, [lojaId]);

  if (erro) {
    return (
      <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
        {erro}
      </p>
    );
  }
  if (!itens) {
    return (
      <p role="status" className="text-sm text-slate-500 dark:text-slate-400">
        Carregando o histórico…
      </p>
    );
  }
  if (itens.length === 0) {
    return (
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Nenhuma alteração registrada ainda. As mudanças feitas daqui para frente aparecem aqui.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
            <th className="py-2 pr-3 font-semibold">Quando</th>
            <th className="py-2 pr-3 font-semibold">Quem</th>
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
                <td className="py-2 pr-3">{alteracao.titulo}</td>
                <td className="py-2 pr-3">{alteracao.antes}</td>
                <td className="py-2 font-medium">{alteracao.depois}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
