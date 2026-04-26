import { useMemo } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { buildReturnTo } from "../../../utils/petReturnFlow";
import { useExamesAnexadosList } from "./useExamesAnexadosList";
import { useExamesAnexadosNovoExame } from "./useExamesAnexadosNovoExame";
import { useExamesAnexadosPets } from "./useExamesAnexadosPets";
import { useExamesAnexadosResumo } from "./useExamesAnexadosResumo";

export function useVetExamesAnexados() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const lista = useExamesAnexadosList();
  const pets = useExamesAnexadosPets();

  const petIdQuery = searchParams.get("pet_id") || "";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const acaoQuery = searchParams.get("acao") || "";
  const agendamentoIdQuery = searchParams.get("agendamento_id") || "";
  const consultaIdQuery = searchParams.get("consulta_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";

  const novoExame = useExamesAnexadosNovoExame({
    acaoQuery,
    agendamentoIdQuery,
    carregar: lista.carregar,
    consultaIdQuery,
    navigate,
    novoPetIdQuery,
    petIdQuery,
    pets,
    tutorIdQuery,
    tutorNomeQuery,
  });
  const resumo = useExamesAnexadosResumo({ navigate, setDados: lista.setDados });

  const retornoNovoPet = useMemo(
    () => buildReturnTo(location.pathname, location.search, { acao: "novo" }),
    [location.pathname, location.search]
  );

  return {
    ...lista,
    ...novoExame,
    ...resumo,
    consultaIdQuery,
    retornoNovoPet,
    verPet: (petId) => navigate(`/pets/${petId}`),
    verPets: () => navigate("/pets"),
  };
}
