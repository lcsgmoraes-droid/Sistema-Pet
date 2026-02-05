import { useState } from "react";
import axios from "../services/api";

const CANAIS = [
  { label: "Loja Física", value: "loja_fisica" },
  { label: "Online", value: "online" },
  { label: "Mercado Livre", value: "mercado_livre" },
  { label: "Shopee", value: "shopee" },
  { label: "Amazon", value: "amazon" },
];

export default function NotaFiscalItemRateio({
  itemId,
  quantidadeTotal
}) {
  const [rateios, setRateios] = useState(
    CANAIS.map(c => ({ canal: c.value, quantidade: 0 }))
  );
  const [erro, setErro] = useState(null);
  const [resultado, setResultado] = useState(null);

  const soma = rateios.reduce(
    (acc, r) => acc + Number(r.quantidade || 0),
    0
  );

  function atualizar(canal, valor) {
    setRateios(prev =>
      prev.map(r =>
        r.canal === canal
          ? { ...r, quantidade: Number(valor) }
          : r
      )
    );
  }

  async function salvar() {
    setErro(null);
    setResultado(null);

    if (soma !== quantidadeTotal) {
      setErro(
        `Soma das quantidades (${soma}) deve ser igual ao total (${quantidadeTotal})`
      );
      return;
    }

    try {
      const response = await axios.post(
        `/notas-fiscais/itens/${itemId}/rateio`,
        rateios.filter(r => r.quantidade > 0)
      );
      setResultado(response.data.rateio);
    } catch (e) {
      setErro(e.response?.data?.detail || "Erro ao salvar rateio");
    }
  }

  return (
    <div style={{ maxWidth: 500 }}>
      <h3>Rateio do Item</h3>
      <p>Quantidade total: <strong>{quantidadeTotal}</strong></p>

      {CANAIS.map(c => (
        <div key={c.value} style={{ marginBottom: 8 }}>
          <label>{c.label}</label>
          <input
            type="number"
            min="0"
            value={
              rateios.find(r => r.canal === c.value)?.quantidade || 0
            }
            onChange={e => atualizar(c.value, e.target.value)}
            style={{ marginLeft: 8, width: 80 }}
          />
        </div>
      ))}

      <div style={{ marginTop: 10 }}>
        <strong>Soma: {soma}</strong>
      </div>

      {erro && <p style={{ color: "red" }}>{erro}</p>}

      <button onClick={salvar} style={{ marginTop: 10 }}>
        Salvar Rateio
      </button>

      {resultado && (
        <div style={{ marginTop: 15 }}>
          <h4>Resultado calculado</h4>
          {resultado.map(r => (
            <div key={r.canal}>
              {r.canal}: {r.quantidade} un — R$ {r.valor_calculado} ({r.percentual_calculado}%)
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
