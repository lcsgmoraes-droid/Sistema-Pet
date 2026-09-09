import { useEffect, useId, useState } from "react";
import api from "../../api";
import { nomeOrigemCliente, ORIGENS_CLIENTE } from "../../utils/clienteOrigem";

export default function ClienteOrigemSelect({ value, onChange, filtro = false, disabled = false }) {
  const id = useId();
  const [opcoes, setOpcoes] = useState(ORIGENS_CLIENTE);
  const [nova, setNova] = useState(false);
  const [erro, setErro] = useState(false);
  useEffect(() => {
    let ativo = true;
    api
      .get("/clientes/origens")
      .then(({ data }) => {
        if (ativo) setOpcoes(data);
      })
      .catch(() => {
        if (ativo) setErro(true);
      });
    return () => {
      ativo = false;
    };
  }, []);
  const selecionado = filtro ? value : value || "nao_identificada";
  const extras =
    value && value !== "nao_identificada" && !opcoes.some((item) => item.value === value)
      ? [{ value, label: nomeOrigemCliente(value) }]
      : [];

  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-gray-700">
        Origem do cliente
      </label>
      <select
        id={id}
        value={nova ? "__nova__" : selecionado}
        disabled={disabled}
        onChange={(event) => {
          const next = event.target.value;
          setNova(next === "__nova__");
          onChange(next === "__nova__" ? "" : next === "nao_identificada" && !filtro ? null : next);
        }}
        className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900"
      >
        {filtro && <option value="">Todas as origens</option>}
        {[...opcoes, ...extras].map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
        <option value="nao_identificada">Não identificada</option>
        {!filtro && <option value="__nova__">+ Nova origem</option>}
      </select>
      {nova && (
        <input
          aria-label="Nome da nova origem"
          value={value || ""}
          required
          maxLength={50}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          placeholder="Ex.: Feira de adoção"
          className="mt-2 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
        />
      )}
      {erro && (
        <p className="mt-1 text-xs text-amber-700">
          Não foi possível carregar as origens adicionais. As opções padrão continuam disponíveis.
        </p>
      )}
    </div>
  );
}
