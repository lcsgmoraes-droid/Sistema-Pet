import { useEffect, useState } from "react";
import api from "../api";
import { getCategorias, getMarcas } from "../api/produtos";

export default function useProdutosCatalogos() {
  const [categorias, setCategorias] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [fornecedores, setFornecedores] = useState([]);
  const [departamentos, setDepartamentos] = useState([]);

  useEffect(() => {
    void carregarCatalogos();
  }, []);

  const carregarCategorias = async () => {
    try {
      const response = await getCategorias();
      setCategorias(response.data);
    } catch (error) {
      console.error("Erro ao carregar categorias:", error);
    }
  };

  const carregarMarcas = async () => {
    try {
      const response = await getMarcas();
      setMarcas(response.data);
    } catch (error) {
      console.error("Erro ao carregar marcas:", error);
    }
  };

  const carregarFornecedores = async () => {
    try {
      const response = await api.get(
        "/clientes/?tipo_cadastro=fornecedor&apenas_ativos=true",
      );
      const dados = response.data;
      const lista = Array.isArray(dados)
        ? dados
        : dados.items || dados.clientes || dados.data || [];
      setFornecedores(lista);
    } catch (error) {
      console.error("Erro ao carregar fornecedores:", error);
    }
  };

  const carregarDepartamentos = async () => {
    try {
      const response = await api.get("/produtos/departamentos");
      setDepartamentos(response.data);
    } catch (error) {
      console.error("Erro ao carregar departamentos:", error);
    }
  };

  const carregarCatalogos = async () => {
    await Promise.allSettled([
      carregarCategorias(),
      carregarMarcas(),
      carregarFornecedores(),
      carregarDepartamentos(),
    ]);
  };

  return {
    categorias,
    departamentos,
    fornecedores,
    marcas,
    recarregarCatalogos: carregarCatalogos,
  };
}
