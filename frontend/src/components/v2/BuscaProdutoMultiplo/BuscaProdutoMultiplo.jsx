import { useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
import { getProdutosVendaveis } from "../../../api/produtos";
import { normalizarBusca } from "../../../utils/buscaEntidades";
import { obterCodigoProdutoPublico } from "../../../utils/codigosPublicos";
import BotaoInteracao from "../BotaoInteracao/BotaoInteracao";
import BuscaProduto from "../BuscaProduto/BuscaProduto";

// Combina o catálogo atual com os produtos do histórico fornecidos pela tela.
// Um produto inativo que foi vendido continua disponível para filtrar o período.
export default function BuscaProdutoMultiplo({
  id,
  label = "Produtos",
  help,
  disabled = false,
  value = [],
  onChange,
  opcoes = [],
}) {
  const [termo, setTermo] = useState("");
  const [remotos, setRemotos] = useState([]);
  const [conhecidos, setConhecidos] = useState({});
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");
  const registrosLocais = useMemo(
    () =>
      opcoes.map((opcao) => ({
        id: Number(opcao.value),
        nome: opcao.label,
        ...(opcao.produto || {}),
      })),
    [opcoes],
  );
  const selecionados = useMemo(() => new Set(value.map(String)), [value]);

  useEffect(() => {
    if (!termo.trim() || disabled) {
      setRemotos([]);
      setLoading(false);
      return undefined;
    }
    let ativo = true;
    const abortar = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      setErro("");
      try {
        const { data } = await getProdutosVendaveis(
          { busca: termo.trim(), page_size: 30, contar_total: false, incluir_imagens: false },
          { signal: abortar.signal },
        );
        if (ativo) setRemotos(data.items || []);
      } catch (error) {
        if (ativo && error.code !== "ERR_CANCELED")
          setErro(
            "Não foi possível buscar no catálogo. Os produtos do período continuam disponíveis.",
          );
      } finally {
        if (ativo) setLoading(false);
      }
    }, 180);
    return () => {
      ativo = false;
      clearTimeout(timer);
      abortar.abort();
    };
  }, [termo, disabled]);

  const registros = useMemo(() => {
    const porId = new Map(registrosLocais.map((item) => [String(item.id), item]));
    for (const item of remotos) porId.set(String(item.id), item);
    return [...porId.values()];
  }, [registrosLocais, remotos]);
  const sugestoes = useMemo(() => {
    const palavras = normalizarBusca(termo).split(" ").filter(Boolean);
    const idsRemotos = new Set(remotos.map((item) => String(item.id)));
    return registros.filter(
      (item) =>
        !selecionados.has(String(item.id)) &&
        (idsRemotos.has(String(item.id)) ||
          palavras.every((palavra) =>
            normalizarBusca(
              `${item.nome} ${obterCodigoProdutoPublico(item)} ${item.codigo_barras || ""}`,
            ).includes(palavra),
          )),
    );
  }, [registros, remotos, termo, selecionados]);
  const nomeSelecionado = (idProduto) => {
    const item =
      conhecidos[String(idProduto)] ||
      registros.find((produto) => String(produto.id) === String(idProduto));
    if (!item) return "Produto selecionado";
    const codigo = obterCodigoProdutoPublico(item);
    return `${item.nome}${codigo && !item.nome.includes(`(${codigo})`) ? ` (${codigo})` : ""}`;
  };

  return (
    <div className="space-y-2">
      <BuscaProduto
        inputId={id}
        label={label}
        value={termo}
        onChange={(texto) => {
          setTermo(texto);
          setRemotos([]);
          setErro("");
        }}
        disabled={disabled}
        showSuggestions
        suggestions={sugestoes}
        loading={loading}
        help={erro || help}
        onSelect={(produto) => {
          const idProduto = String(produto.id);
          setConhecidos((atuais) => ({ ...atuais, [idProduto]: produto }));
          if (!selecionados.has(idProduto)) onChange?.([...value, idProduto]);
          setTermo("");
        }}
      />
      {value.length > 0 && (
        <div className="flex flex-wrap gap-2" aria-label="Produtos selecionados">
          {value.map((idProduto) => (
            <BotaoInteracao
              key={idProduto}
              icon={X}
              tamanho="pequeno"
              disabled={disabled}
              aria-label={`Remover ${nomeSelecionado(idProduto)}`}
              onClick={() =>
                onChange?.(value.filter((idAtual) => String(idAtual) !== String(idProduto)))
              }
            >
              {nomeSelecionado(idProduto)}
            </BotaoInteracao>
          ))}
        </div>
      )}
    </div>
  );
}
