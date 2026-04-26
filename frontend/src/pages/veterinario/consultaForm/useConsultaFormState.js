import { useCallback, useState } from "react";

import {
  criarConsultaFormInicial,
  criarInsumoRapidoFormInicial,
  criarNovoExameFormInicial,
} from "./consultaFormState";

export default function useConsultaFormState(consultaId) {
  const [etapa, setEtapa] = useState(0);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(null);
  const [consultaIdAtual, setConsultaIdAtual] = useState(consultaId ?? null);
  const [modalCalculadoraAberto, setModalCalculadoraAberto] = useState(false);
  const [modalNovoExameAberto, setModalNovoExameAberto] = useState(false);
  const [salvandoNovoExame, setSalvandoNovoExame] = useState(false);
  const [modalNovoPetAberto, setModalNovoPetAberto] = useState(false);
  const [refreshExamesToken, setRefreshExamesToken] = useState(0);
  const [novoExameForm, setNovoExameForm] = useState(criarNovoExameFormInicial);
  const [novoExameArquivo, setNovoExameArquivo] = useState(null);
  const [modalInsumoAberto, setModalInsumoAberto] = useState(false);
  const [salvandoInsumoRapido, setSalvandoInsumoRapido] = useState(false);
  const [insumoRapidoSelecionado, setInsumoRapidoSelecionado] = useState(null);
  const [insumoRapidoForm, setInsumoRapidoForm] = useState(criarInsumoRapidoFormInicial);
  const [form, setForm] = useState(criarConsultaFormInicial);

  const setCampo = useCallback((campo, valor) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }, []);

  return {
    consultaIdAtual,
    erro,
    etapa,
    form,
    insumoRapidoForm,
    insumoRapidoSelecionado,
    modalCalculadoraAberto,
    modalInsumoAberto,
    modalNovoExameAberto,
    modalNovoPetAberto,
    novoExameArquivo,
    novoExameForm,
    refreshExamesToken,
    salvando,
    salvandoInsumoRapido,
    salvandoNovoExame,
    setCampo,
    setConsultaIdAtual,
    setErro,
    setEtapa,
    setForm,
    setInsumoRapidoForm,
    setInsumoRapidoSelecionado,
    setModalCalculadoraAberto,
    setModalInsumoAberto,
    setModalNovoExameAberto,
    setModalNovoPetAberto,
    setNovoExameArquivo,
    setNovoExameForm,
    setRefreshExamesToken,
    setSalvando,
    setSalvandoInsumoRapido,
    setSalvandoNovoExame,
    setSucesso,
    sucesso,
  };
}
