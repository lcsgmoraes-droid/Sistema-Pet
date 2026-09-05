import { useEffect, useState } from "react";
import { consultarSkuProdutoRapido } from "../../../services/funcionarioProdutos.service";

export function useSkuProdutoRapido(sku: string) {
  const [consulta, setConsulta] = useState<{ codigo: string; status: "disponivel" | "ocupado" | "erro" } | null>(null);
  const codigo = sku.trim().toUpperCase();
  useEffect(() => {
    if (!codigo) return;
    let cancelado = false;
    const timer = setTimeout(async () => {
      try {
        const resultado = await consultarSkuProdutoRapido(codigo);
        if (!cancelado) setConsulta({ codigo, status: resultado.disponivel ? "disponivel" : "ocupado" });
      } catch {
        if (!cancelado) setConsulta({ codigo, status: "erro" });
      }
    }, 450);
    return () => { cancelado = true; clearTimeout(timer); };
  }, [codigo]);

  const status = !codigo ? "automatico" : consulta?.codigo === codigo ? consulta.status : "consultando";
  const mensagem = {
    automatico: "Deixe vazio para gerar o SKU automaticamente.",
    consultando: "Conferindo disponibilidade do SKU...",
    disponivel: "SKU disponível. Será conferido novamente ao salvar.",
    ocupado: "SKU já utilizado, inclusive se o produto estiver inativo. Escolha outro ou deixe vazio.",
    erro: "Não foi possível consultar o SKU. Será conferido ao salvar.",
  }[status];
  return { status, mensagem };
}
