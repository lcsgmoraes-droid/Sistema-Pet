import { useEffect, useState } from "react";
import { api } from "../../services/api";

export default function ConciliacaoCartao() {
  const [pendentes, setPendentes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);

  const [selecionado, setSelecionado] = useState(null);
  const [dataRecebimento, setDataRecebimento] = useState("");
  const [salvando, setSalvando] = useState(false);

  const [arquivo, setArquivo] = useState(null);
  const [resultadoUpload, setResultadoUpload] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function carregarPendentes() {
    try {
      setLoading(true);
      const response = await api.get(
        "/financeiro/conciliacao-cartao/pendentes"
      );
      setPendentes(response.data);
    } catch (err) {
      console.error(err);
      setErro("Erro ao carregar conciliações pendentes");
    } finally {
      setLoading(false);
    }
  }

  async function conciliar() {
    if (!dataRecebimento) {
      alert("Informe a data de recebimento");
      return;
    }

    try {
      setSalvando(true);
      await api.post("/financeiro/conciliacao-cartao", {
        nsu: selecionado.nsu,
        valor: selecionado.valor,
        data_recebimento: dataRecebimento,
        adquirente: selecionado.adquirente,
      });

      setSelecionado(null);
      setDataRecebimento("");
      await carregarPendentes();
    } catch (err) {
      console.error(err);
      alert("Erro ao conciliar. Verifique os dados.");
    } finally {
      setSalvando(false);
    }
  }

  async function enviarCSV() {
    if (!arquivo) {
      alert("Selecione um arquivo CSV");
      return;
    }

    const formData = new FormData();
    formData.append("file", arquivo);

    try {
      setEnviando(true);
      const response = await api.post(
        "/financeiro/conciliacao-cartao/upload",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );

      setResultadoUpload(response.data);
      setArquivo(null);
      await carregarPendentes();
    } catch (err) {
      console.error(err);
      alert("Erro ao processar o CSV");
    } finally {
      setEnviando(false);
    }
  }

  useEffect(() => {
    carregarPendentes();
  }, []);

  if (loading) return <p>Carregando conciliações pendentes...</p>;
  if (erro) return <p style={{ color: "red" }}>{erro}</p>;

  return (
    <div style={{ padding: 24 }}>
      <h1>Conciliação de Cartão</h1>

      {/* UPLOAD CSV */}
      <div style={{ marginBottom: 24 }}>
        <h3>Upload de Conciliação (CSV)</h3>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setArquivo(e.target.files[0])}
        />
        <button onClick={enviarCSV} disabled={enviando}>
          {enviando ? "Processando..." : "Enviar CSV"}
        </button>

        {resultadoUpload && (
          <pre style={{ background: "#f4f4f4", padding: 12, marginTop: 12 }}>
            {JSON.stringify(resultadoUpload, null, 2)}
          </pre>
        )}
      </div>

      {/* TABELA */}
      {pendentes.length === 0 ? (
        <p>Nenhuma conciliação pendente 🎉</p>
      ) : (
        <table width="100%" border="1" cellPadding="8">
          <thead>
            <tr>
              <th>ID</th>
              <th>NSU</th>
              <th>Adquirente</th>
              <th>Valor</th>
              <th>Parcela</th>
              <th>Data Prevista</th>
              <th>Ação</th>
            </tr>
          </thead>
          <tbody>
            {pendentes.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.nsu}</td>
                <td>{item.adquirente}</td>
                <td>R$ {item.valor.toFixed(2)}</td>
                <td>
                  {item.numero_parcela}/{item.total_parcelas}
                </td>
                <td>{item.data_prevista || "-"}</td>
                <td>
                  <button onClick={() => setSelecionado(item)}>
                    Conciliar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* MODAL */}
      {selecionado && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div style={{ background: "#fff", padding: 24, minWidth: 320 }}>
            <h3>Conciliar Parcela</h3>

            <p><strong>NSU:</strong> {selecionado.nsu}</p>
            <p><strong>Valor:</strong> R$ {selecionado.valor.toFixed(2)}</p>

            <label>Data de Recebimento</label>
            <input
              type="date"
              value={dataRecebimento}
              onChange={(e) => setDataRecebimento(e.target.value)}
              style={{ display: "block", marginBottom: 16 }}
            />

            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => setSelecionado(null)}>Cancelar</button>
              <button onClick={conciliar} disabled={salvando}>
                {salvando ? "Conciliando..." : "Confirmar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
