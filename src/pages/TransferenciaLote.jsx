
import { useState } from "react";
import api from "../services/api";

export default function TransferenciaLote() {
  const [arquivo, setArquivo] = useState(null);
  const [destino, setDestino] = useState("");
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState(null);
  const [loading, setLoading] = useState(false);

  async function enviar() {
    if (!arquivo || !destino) {
      setErro("Selecione o destino e o arquivo");
      return;
    }

    setErro(null);
    setResultado(null);
    setLoading(true);

    const formData = new FormData();
    formData.append("file", arquivo);

    const isCSV = arquivo.name.toLowerCase().endsWith(".csv");
    const endpoint = isCSV
      ? "/estoque/importacao/csv"
      : "/estoque/importacao/pdf";

    try {
      const res = await api.post(
        endpoint + "?local_destino_id=" + destino,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setResultado(res.data);
    } catch (e) {
      setErro("Erro ao importar arquivo");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 600 }}>
      <h2>Transferência de Estoque em Lote</h2>

      <label>Destino (FULL)</label>
      <select
        value={destino}
        onChange={e => setDestino(e.target.value)}
      >
        <option value="">Selecione</option>
        <option value="FULL_ML">Full Mercado Livre</option>
        <option value="FULL_SHOPEE">Full Shopee</option>
        <option value="FULL_AMAZON">Full Amazon</option>
      </select>

      <br /><br />

      <input
        type="file"
        accept=".csv,.pdf"
        onChange={e => setArquivo(e.target.files[0])}
      />

      <br /><br />

      <button onClick={enviar} disabled={loading}>
        {loading ? "Processando..." : "Importar"}
      </button>

      {erro && <p style={{ color: "red" }}>{erro}</p>}

      {resultado && (
        <div style={{ marginTop: 20 }}>
          <h4>Resultado</h4>

          <p>✔️ Sucesso: {resultado.sucesso?.length || 0}</p>
          <p>❌ Erros: {resultado.erros?.length || 0}</p>

          {resultado.erros?.map((e, i) => (
            <div key={i} style={{ color: "red" }}>
              Linha/SKU: {e.sku || e.linha} — {e.erro}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
