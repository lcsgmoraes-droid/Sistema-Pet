import { useState } from "react";

import { FORM_CONSULTORIO_INICIAL, FORM_PARCEIRO_INICIAL } from "./configuracoesConstants";
import { useConfiguracoesConsultoriosActions } from "./useConfiguracoesConsultoriosActions";
import { useConfiguracoesData } from "./useConfiguracoesData";
import { useConfiguracoesFeedback } from "./useConfiguracoesFeedback";
import { useConfiguracoesParceirosActions } from "./useConfiguracoesParceirosActions";

export function useVetConfiguracoes() {
  const data = useConfiguracoesData();
  const { mostrarSucesso, sucesso } = useConfiguracoesFeedback();
  const [mostrarForm, setMostrarForm] = useState(false);
  const [parceiroForm, setParceiroForm] = useState(FORM_PARCEIRO_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [mostrarFormConsultorio, setMostrarFormConsultorio] = useState(false);
  const [consultorioForm, setConsultorioForm] = useState(FORM_CONSULTORIO_INICIAL);

  const parceirosActions = useConfiguracoesParceirosActions({
    carregar: data.carregar,
    mostrarSucesso,
    parceiroForm,
    setErro: data.setErro,
    setMostrarForm,
    setParceiroForm,
    setParceiros: data.setParceiros,
    setSalvando,
  });
  const consultoriosActions = useConfiguracoesConsultoriosActions({
    carregar: data.carregar,
    consultorioForm,
    mostrarSucesso,
    setConsultorioForm,
    setConsultorios: data.setConsultorios,
    setErro: data.setErro,
    setMostrarFormConsultorio,
    setSalvando,
  });

  return {
    ...consultoriosActions,
    ...parceirosActions,
    carregar: data.carregar,
    carregando: data.carregando,
    consultorioForm,
    consultorios: data.consultorios,
    erro: data.erro,
    mostrarForm,
    mostrarFormConsultorio,
    parceiroForm,
    parceiros: data.parceiros,
    salvando,
    setErro: data.setErro,
    setMostrarForm,
    setMostrarFormConsultorio,
    sucesso,
    tenantsVet: data.tenantsVet,
  };
}
