import { useEffect, useState } from "react";

import { api } from "../../../services/api";
import { vetApi } from "../vetApi";

export default function useConsultaCatalogos() {
  const [pets, setPets] = useState([]);
  const [veterinarios, setVeterinarios] = useState([]);
  const [medicamentosCatalogo, setMedicamentosCatalogo] = useState([]);
  const [procedimentosCatalogo, setProcedimentosCatalogo] = useState([]);

  useEffect(() => {
    api
      .get("/vet/pets", { params: { limit: 500 } })
      .then((res) => setPets(res.data?.items ?? res.data ?? []))
      .catch(() => {});
    api
      .get("/vet/veterinarios")
      .then((res) => setVeterinarios(res.data ?? []))
      .catch(() => {});

    vetApi
      .listarMedicamentos()
      .then((res) => setMedicamentosCatalogo(Array.isArray(res.data) ? res.data : (res.data?.items ?? [])))
      .catch(() => {});
    vetApi
      .listarCatalogoProcedimentos()
      .then((res) => setProcedimentosCatalogo(Array.isArray(res.data) ? res.data : (res.data?.items ?? [])))
      .catch(() => {});
  }, []);

  return {
    pets,
    setPets,
    veterinarios,
    medicamentosCatalogo,
    procedimentosCatalogo,
  };
}
