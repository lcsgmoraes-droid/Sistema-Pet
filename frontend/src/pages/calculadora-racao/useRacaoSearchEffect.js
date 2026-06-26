import { useEffect } from "react";
import { buscarRacoesNoCadastro } from "./calculadoraRacaoApi";

export default function useRacaoSearchEffect({
  contextoErro,
  produtoId,
  setLoading,
  setProdutos,
  termo,
}) {
  useEffect(() => {
    const texto = String(termo || "").trim();
    if (produtoId || texto.length < 2) {
      setProdutos([]);
      setLoading(false);
      return undefined;
    }

    let ativo = true;
    const timer = setTimeout(async () => {
      try {
        setLoading(true);
        const racoes = await buscarRacoesNoCadastro(texto);
        if (ativo) setProdutos(racoes);
      } catch (error) {
        console.error(contextoErro, error);
        if (ativo) setProdutos([]);
      } finally {
        if (ativo) setLoading(false);
      }
    }, 250);

    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, [contextoErro, produtoId, setLoading, setProdutos, termo]);
}
