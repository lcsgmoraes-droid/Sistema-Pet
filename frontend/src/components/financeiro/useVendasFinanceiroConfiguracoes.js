import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  carregarConfigDiasUteis,
  carregarFeriadosCustomizados,
  getDiasUteisStorageKey,
  getFeriadosStorageKey,
} from "./vendasFinanceiroUtils";

const COLUNAS_RELATORIO_PADRAO = [
  "data_venda",
  "numero_venda",
  "cliente_nome",
  "venda_bruta",
  "venda_liquida",
  "valor_recebido",
  "lucro",
  "status",
];

export default function useVendasFinanceiroConfiguracoes() {
  const [mostrarConfigFeriados, setMostrarConfigFeriados] = useState(false);
  const [feriadosCustomizados, setFeriadosCustomizados] = useState(
    carregarFeriadosCustomizados,
  );
  const [configDiasUteis, setConfigDiasUteis] = useState(carregarConfigDiasUteis);
  const [novoFeriadoData, setNovoFeriadoData] = useState("");
  const [novoFeriadoNome, setNovoFeriadoNome] = useState("");
  const [ordenacaoRelatorio, setOrdenacaoRelatorio] = useState("data_desc");
  const [colunasRelatorio, setColunasRelatorio] = useState(COLUNAS_RELATORIO_PADRAO);

  const adicionarFeriadoCustomizado = () => {
    if (!novoFeriadoData) {
      toast.error("Informe a data do feriado.");
      return;
    }

    setFeriadosCustomizados((prev) => {
      const semDuplicado = prev.filter((feriado) => feriado.data !== novoFeriadoData);
      return [
        ...semDuplicado,
        {
          data: novoFeriadoData,
          nome: novoFeriadoNome.trim() || "Feriado local",
        },
      ].sort((a, b) => a.data.localeCompare(b.data));
    });
    setNovoFeriadoData("");
    setNovoFeriadoNome("");
    toast.success("Feriado salvo para a contagem de dias úteis.");
  };

  const removerFeriadoCustomizado = (data) => {
    setFeriadosCustomizados((prev) => prev.filter((feriado) => feriado.data !== data));
  };

  const toggleColunaRelatorio = (key) => {
    setColunasRelatorio((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key],
    );
  };

  useEffect(() => {
    window.localStorage.setItem(
      getFeriadosStorageKey(),
      JSON.stringify(feriadosCustomizados),
    );
  }, [feriadosCustomizados]);

  useEffect(() => {
    window.localStorage.setItem(
      getDiasUteisStorageKey(),
      JSON.stringify(configDiasUteis),
    );
  }, [configDiasUteis]);

  return {
    adicionarFeriadoCustomizado,
    colunasRelatorio,
    configDiasUteis,
    feriadosCustomizados,
    mostrarConfigFeriados,
    novoFeriadoData,
    novoFeriadoNome,
    ordenacaoRelatorio,
    removerFeriadoCustomizado,
    setConfigDiasUteis,
    setMostrarConfigFeriados,
    setNovoFeriadoData,
    setNovoFeriadoNome,
    setOrdenacaoRelatorio,
    toggleColunaRelatorio,
  };
}
