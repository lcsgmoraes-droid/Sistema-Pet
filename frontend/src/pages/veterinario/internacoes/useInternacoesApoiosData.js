import { useEffect, useState } from "react";

import { api } from "../../../services/api";
import { vetApi } from "../vetApi";

export function useInternacoesApoiosData() {
  const [pets, setPets] = useState([]);
  const [veterinarios, setVeterinarios] = useState([]);

  useEffect(() => {
    api
      .get("/pets", { params: { limit: 500 } })
      .then((res) => setPets(res.data?.items ?? res.data ?? []))
      .catch(() => {});

    vetApi
      .listarVeterinarios()
      .then((res) => setVeterinarios(Array.isArray(res.data) ? res.data : []))
      .catch(() => setVeterinarios([]));
  }, []);

  return { pets, veterinarios };
}
