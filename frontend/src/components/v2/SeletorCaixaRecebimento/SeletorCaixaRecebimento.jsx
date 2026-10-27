import { useEffect, useState } from "react";
import api from "../../../api";
import InputCombobox from "../InputCombobox/InputCombobox";
import { safeArray } from "../../../utils/safeArray";

export default function SeletorCaixaRecebimento({
  value,
  onChange,
  disabled = false,
  label = "Caixa do recebimento",
}) {
  const [caixas, setCaixas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let ativo = true;
    api
      .get("/caixas", { params: { status_filter: "aberto", compact: true } })
      .then(({ data }) => {
        if (!ativo) return;
        const lista = safeArray(data);
        setCaixas(lista);
        if (lista.length === 1) onChange?.(lista[0].id);
        else onChange?.(null);
        if (!lista.length) setError("Abra ou reabra um caixa para registrar o recebimento.");
      })
      .catch(() => {
        if (ativo)
          setError(
            "Não foi possível consultar os caixas. Feche e abra o recebimento para tentar novamente.",
          );
      })
      .finally(() => {
        if (ativo) setLoading(false);
      });
    return () => {
      ativo = false;
    };
  }, []);
  return (
    <InputCombobox
      id="caixa-recebimento"
      label={label}
      value={value}
      onChange={(id) => onChange?.(Number(id) || null)}
      required
      disabled={disabled || loading}
      error={error}
      placeholder={loading ? "Consultando caixas..." : "Selecione o caixa"}
      help={
        caixas.length > 1
          ? "Há mais de um caixa aberto. Confira onde este recebimento deve entrar."
          : "O movimento ficará vinculado ao caixa selecionado."
      }
      opcoes={caixas.map((caixa) => ({
        value: caixa.id,
        label: `Caixa ${caixa.numero_caixa} · ${caixa.usuario_nome || "Operador"} · ${new Date(caixa.data_abertura).toLocaleDateString("pt-BR")}`,
      }))}
    />
  );
}
