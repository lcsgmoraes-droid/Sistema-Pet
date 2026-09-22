import { useEffect, useId, useState } from "react";
import api from "../../api";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputTexto from "../v2/InputTexto/InputTexto";
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

  const opcoesCombobox = [
    ...(filtro ? [{ value: "", label: "Todas as origens" }] : []),
    ...opcoes,
    ...extras,
    { value: "nao_identificada", label: "Não identificada" },
    ...(!filtro ? [{ value: "__nova__", label: "+ Nova origem" }] : []),
  ];

  return (
    <div>
      <InputCombobox
        id={id}
        label="Origem do cliente"
        opcoes={opcoesCombobox}
        value={nova ? "__nova__" : selecionado}
        disabled={disabled}
        permitirLimpar={false}
        onChange={(next) => {
          setNova(next === "__nova__");
          onChange(next === "__nova__" ? "" : next === "nao_identificada" && !filtro ? null : next);
        }}
      />
      {nova && (
        <div className="mt-2">
          <InputTexto
            id={`${id}-nova`}
            value={value || ""}
            required
            maxLength={50}
            onChange={onChange}
            disabled={disabled}
            placeholder="Ex.: Feira de adoção"
          />
        </div>
      )}
      {erro && (
        <p className="mt-1 text-xs text-amber-700">
          Não foi possível carregar as origens adicionais. As opções padrão continuam disponíveis.
        </p>
      )}
    </div>
  );
}
