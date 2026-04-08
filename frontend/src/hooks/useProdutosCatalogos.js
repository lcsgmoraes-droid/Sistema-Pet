import { useEffect, useState } from "react";
import api from "../api";
import { getCategorias, getMarcas } from "../api/produtos";

const CATALOGOS_CACHE_KEY = "produtos_catalogos_cache_v1";
const CATALOGOS_CACHE_TTL_MS = 5 * 60 * 1000;

function readCatalogosCache() {
  try {
    const raw = sessionStorage.getItem(CATALOGOS_CACHE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw);
    if (!parsed?.savedAt || !parsed?.data) {
      return null;
    }

    if (Date.now() - Number(parsed.savedAt) > CATALOGOS_CACHE_TTL_MS) {
      sessionStorage.removeItem(CATALOGOS_CACHE_KEY);
      return null;
    }

    return parsed.data;
  } catch {
    return null;
  }
}

function writeCatalogosCache(data) {
  try {
    sessionStorage.setItem(
      CATALOGOS_CACHE_KEY,
      JSON.stringify({
        savedAt: Date.now(),
        data,
      }),
    );
  } catch {
    // Cache é apenas otimização; falhas aqui não devem afetar a tela.
  }
}

export default function useProdutosCatalogos() {
  const [categorias, setCategorias] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [fornecedores, setFornecedores] = useState([]);
  const [departamentos, setDepartamentos] = useState([]);

  useEffect(() => {
    const cached = readCatalogosCache();
    if (cached) {
      setCategorias(cached.categorias || []);
      setMarcas(cached.marcas || []);
      setFornecedores(cached.fornecedores || []);
      setDepartamentos(cached.departamentos || []);
      return;
    }

    void carregarCatalogos();
  }, []);

  const carregarCatalogos = async ({ force = false } = {}) => {
    if (!force) {
      const cached = readCatalogosCache();
      if (cached) {
        setCategorias(cached.categorias || []);
        setMarcas(cached.marcas || []);
        setFornecedores(cached.fornecedores || []);
        setDepartamentos(cached.departamentos || []);
        return cached;
      }
    }

    const [categoriasResult, marcasResult, fornecedoresResult, departamentosResult] =
      await Promise.allSettled([
        getCategorias(),
        getMarcas(),
        api.get("/clientes/", {
          params: {
            tipo_cadastro: "fornecedor",
            ativo: true,
            limit: 200,
          },
        }),
        api.get("/produtos/departamentos"),
      ]);

    if (categoriasResult.status === "rejected") {
      console.error("Erro ao carregar categorias:", categoriasResult.reason);
    }
    if (marcasResult.status === "rejected") {
      console.error("Erro ao carregar marcas:", marcasResult.reason);
    }
    if (fornecedoresResult.status === "rejected") {
      console.error("Erro ao carregar fornecedores:", fornecedoresResult.reason);
    }
    if (departamentosResult.status === "rejected") {
      console.error("Erro ao carregar departamentos:", departamentosResult.reason);
    }

    const categoriasData =
      categoriasResult.status === "fulfilled" ? categoriasResult.value.data || [] : [];
    const marcasData =
      marcasResult.status === "fulfilled" ? marcasResult.value.data || [] : [];
    const fornecedoresPayload =
      fornecedoresResult.status === "fulfilled" ? fornecedoresResult.value.data : [];
    const departamentosData =
      departamentosResult.status === "fulfilled" ? departamentosResult.value.data || [] : [];

    const fornecedoresData = Array.isArray(fornecedoresPayload)
      ? fornecedoresPayload
      : fornecedoresPayload.items || fornecedoresPayload.clientes || fornecedoresPayload.data || [];

    setCategorias(categoriasData);
    setMarcas(marcasData);
    setFornecedores(fornecedoresData);
    setDepartamentos(departamentosData);

    writeCatalogosCache({
      categorias: categoriasData,
      marcas: marcasData,
      fornecedores: fornecedoresData,
      departamentos: departamentosData,
    });
  };

  return {
    categorias,
    departamentos,
    fornecedores,
    marcas,
    recarregarCatalogos: (options = {}) => carregarCatalogos({ force: true, ...options }),
  };
}
