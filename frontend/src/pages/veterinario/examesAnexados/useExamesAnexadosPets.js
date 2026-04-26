import { useEffect, useState } from "react";

import { api } from "../../../services/api";

export function useExamesAnexadosPets() {
  const [pets, setPets] = useState([]);

  useEffect(() => {
    api
      .get("/vet/pets", { params: { limit: 500 } })
      .then((res) => setPets(res.data?.items ?? res.data ?? []))
      .catch(() => setPets([]));
  }, []);

  return pets;
}
