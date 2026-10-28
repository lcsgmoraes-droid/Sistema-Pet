import { useMemo, useState } from "react";
import toast from "react-hot-toast";
import BuscaProduto from "../../components/v2/BuscaProduto/BuscaProduto";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
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
  const termo = normalizarTexto(value);
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
      <BuscaProduto
        id={id}
        name={name}
        label={label}
        value={value || ""}
        disabled={disabled}
        onChange={(texto) => {
          onChange(texto);
          setAberto(true);
        }}
        onFocus={() => setAberto(true)}
        suggestions={opcoes}
        showSuggestions={aberto}
        minChars={0}
        loading={loading}
        onSelect={selecionar}
        placeholder={placeholder}
        renderSuggestionContent={(produto) => (
          <>
            <span className="block font-medium">
              {produto.codigo || "Sem código"} - {produto.nome}
            </span>
            <span className="block text-xs text-slate-500">
              {produto.aptidao.apta ? "Apta" : "Cadastro incompleto"} |{" "}
              {formatarPeso(produto.peso_embalagem)} | {formatarMoeda(produto.preco_venda)} |{" "}
              {formatarPrecoPorKg(produto)} {produto.classificacao_racao || ""}
            </span>
            {!produto.aptidao.apta && (
              <span className="text-xs text-amber-700">
                {camposIncompletosTexto(produto.aptidao.faltantes)}
              </span>
            )}
          </>
        )}
      />
      {value && onClear && (
        <BotaoCancelar tamanho="pequeno" onClick={onClear}>
          Limpar seleção
        </BotaoCancelar>
      )}
      {aberto && !loading && opcoes.length === 0 && (
        <p className="text-sm text-slate-500">Nenhuma ração encontrada.</p>
      )}
      {warning && <small className="form-warning">{warning}</small>}
      {hint && <small className="form-hint">{hint}</small>}
    </div>
  );
}
