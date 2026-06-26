import { useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import {
  camposIncompletosTexto,
  formatarMoeda,
  formatarPeso,
  normalizarTexto,
  pontuarBuscaRacao,
} from "../calculadoraRacaoUtils";
import { formatarPrecoPorKg } from "../../utils/racaoPrecoKg";

export default function RacaoSearchInput({
  disabled = false,
  hint,
  id,
  label,
  loading = false,
  name,
  onChange,
  onClear,
  onSelect,
  placeholder,
  produtos,
  value,
  warning,
}) {
  const [aberto, setAberto] = useState(false);
  const [dropdown, setDropdown] = useState({
    direction: "down",
    maxHeight: 320,
  });
  const controlRef = useRef(null);
  const termo = normalizarTexto(value);

  const abrirDropdown = () => {
    if (disabled) return;

    if (typeof window === "undefined" || !controlRef.current) {
      setAberto(true);
      return;
    }

    const rect = controlRef.current.getBoundingClientRect();
    const margemTela = 16;
    const espacoAbaixo = window.innerHeight - rect.bottom - margemTela;
    const espacoAcima = rect.top - margemTela;
    const direction = espacoAbaixo < 260 && espacoAcima > espacoAbaixo ? "up" : "down";
    const espacoDisponivel = direction === "up" ? espacoAcima : espacoAbaixo;

    setDropdown({
      direction,
      maxHeight: Math.max(140, Math.min(320, Math.floor(espacoDisponivel))),
    });
    setAberto(true);
  };

  const opcoes = useMemo(() => {
    const filtradas = produtos
      .map((produto) => ({
        produto,
        score: termo ? pontuarBuscaRacao(produto, value) : 1,
      }))
      .filter((item) => item.score > 0);

    return filtradas
      .sort((a, b) => {
        if (a.produto.aptidao.apta !== b.produto.aptidao.apta) {
          return a.produto.aptidao.apta ? -1 : 1;
        }
        if (a.score !== b.score) return b.score - a.score;
        return a.produto.nome.localeCompare(b.produto.nome, "pt-BR");
      })
      .map((item) => item.produto)
      .slice(0, 12);
  }, [produtos, termo, value]);

  const selecionar = (produto) => {
    if (!produto.aptidao.apta) {
      toast.error(camposIncompletosTexto(produto.aptidao.faltantes));
      return;
    }
    onSelect(produto);
    setAberto(false);
  };

  return (
    <div className="racao-search-field">
      <label htmlFor={id}>{label}</label>
      <div className="racao-search-control" ref={controlRef}>
        <input
          id={id}
          name={name}
          type="text"
          value={value || ""}
          onChange={(event) => {
            onChange(event.target.value);
            abrirDropdown();
          }}
          onFocus={abrirDropdown}
          onClick={abrirDropdown}
          onBlur={() => setTimeout(() => setAberto(false), 160)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
        />
        {value && onClear && (
          <button
            type="button"
            onMouseDown={(event) => event.preventDefault()}
            onClick={onClear}
            className="btn-clear btn-clear-compact"
            title="Limpar selecao"
          >
            x
          </button>
        )}
      </div>

      {aberto && !disabled && (
        <div
          className={`racao-options open-${dropdown.direction}`}
          role="listbox"
          style={{
            "--racao-options-max-height": `${dropdown.maxHeight}px`,
          }}
        >
          {loading && <div className="racao-empty">Buscando no cadastro...</div>}
          {!loading && opcoes.length === 0 ? (
            <div className="racao-empty">Nenhuma racao encontrada.</div>
          ) : (
            opcoes.map((produto) => (
              <button
                key={produto.id}
                type="button"
                className={`racao-option ${produto.aptidao.apta ? "is-ready" : "is-incomplete"}`}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => selecionar(produto)}
                aria-disabled={!produto.aptidao.apta}
              >
                <div className="racao-option-main">
                  <span className="racao-option-name">{produto.nome}</span>
                  <span className={`racao-status ${produto.aptidao.apta ? "ready" : "incomplete"}`}>
                    {produto.aptidao.apta ? "Apta" : "Cadastro incompleto"}
                  </span>
                </div>
                <div className="racao-option-meta">
                  <span>{formatarPeso(produto.peso_embalagem)}</span>
                  <span>{formatarMoeda(produto.preco_venda)}</span>
                  {formatarPrecoPorKg(produto) && <span>{formatarPrecoPorKg(produto)}</span>}
                  {produto.classificacao_racao && <span>{produto.classificacao_racao}</span>}
                </div>
                {!produto.aptidao.apta && (
                  <div className="racao-option-missing">
                    {camposIncompletosTexto(produto.aptidao.faltantes)}
                  </div>
                )}
              </button>
            ))
          )}
        </div>
      )}

      {warning && <small className="form-warning">{warning}</small>}
      {hint && <small className="form-hint">{hint}</small>}
    </div>
  );
}
