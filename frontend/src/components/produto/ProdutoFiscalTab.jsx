import { useEffect, useState } from "react";
import api from "../../services/api";

export default function ProdutoFiscalTab({ produto }) {
  const [fiscal, setFiscal] = useState(null);
  const [sugestoes, setSugestoes] = useState([]);
  const [personalizado, setPersonalizado] = useState(false);

  useEffect(() => {
    async function carregar() {
      try {
        const { data } = await api.get(`/produto/${produto.id}/fiscal`);
        setFiscal(data);
        setPersonalizado(!data.herdado_da_empresa);
      } catch (e) {
        setFiscal({});
      }
    }

    async function carregarSugestoes() {
      if (!produto?.descricao) return;
      if (personalizado) return;

      const { data } = await api.post("/fiscal/sugestao/produto", {
        descricao: produto.descricao
      });
      setSugestoes(data.sugestoes || []);
    }

    carregar();
    carregarSugestoes();
  }, [produto, personalizado]);

  function editarCampo(e) {
    const { name, value } = e.target;
    setFiscal({
      ...fiscal,
      [name]: value
    });
    setPersonalizado(true);
  }

  async function salvarEdicaoManual() {
    await api.put(`/produto/${produto.id}/fiscal`, fiscal);
    alert("Configuração fiscal atualizada");
  }

  async function aplicarSugestao(s) {
    await api.post(`/produto/${produto.id}/fiscal/aplicar`, s);
    setFiscal({ ...s, herdado_da_empresa: false });
    setPersonalizado(false);
    setSugestoes([]);
  }

  async function resetar() {
    await api.post(`/produto/${produto.id}/fiscal/resetar`);
    setPersonalizado(false);
    alert("Fiscal resetado para padrão da empresa");
  }

  if (!fiscal) return <p>Carregando fiscal...</p>;

  return (
    <div className="card">
      <h3>Fiscal do Produto</h3>

      <label>
        NCM {personalizado ? <span className="badge yellow">Personalizado</span> : <span className="badge">Sugerido</span>}
      </label>
      <input name="ncm" value={fiscal.ncm || ""} onChange={editarCampo} />

      <label>
        CEST {personalizado ? <span className="badge yellow">Personalizado</span> : <span className="badge">Sugerido</span>}
      </label>
      <input name="cest" value={fiscal.cest || ""} onChange={editarCampo} />

      <label>
        CST ICMS {personalizado ? <span className="badge yellow">Personalizado</span> : <span className="badge">Sugerido</span>}
      </label>
      <input name="cst_icms" value={fiscal.cst_icms || ""} onChange={editarCampo} />

      <label>
        ICMS ST {personalizado ? <span className="badge yellow">Personalizado</span> : <span className="badge">Sugerido</span>}
      </label>
      <select name="icms_st" value={fiscal.icms_st ? "true" : "false"} onChange={editarCampo}>
        <option value="true">Sim</option>
        <option value="false">Não</option>
      </select>

      {personalizado && (
        <button onClick={salvarEdicaoManual}>
          Salvar alterações manuais
        </button>
      )}

      <button className="secondary" onClick={resetar}>
        Resetar para padrão da empresa
      </button>

      {!personalizado && sugestoes.length > 0 && (
        <div className="suggestion-box">
          <h4>💡 Sugestão do sistema</h4>
          <p><strong>{sugestoes[0].categoria_fiscal}</strong></p>
          <p>{sugestoes[0].observacao}</p>

          <button onClick={() => aplicarSugestao(sugestoes[0])}>
            Aplicar sugestão
          </button>
          <button className="secondary" onClick={() => setSugestoes([])}>
            Ignorar
          </button>
        </div>
      )}
    </div>
  );
}
