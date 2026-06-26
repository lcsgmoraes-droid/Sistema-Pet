import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../../services/api";
import toast from "react-hot-toast";
import { getGuiaClassNames } from "../../utils/guiaHighlight";
import ConfiguracaoFiscalEmpresaView from "./ConfiguracaoFiscalEmpresaView";

export default function ConfiguracaoFiscalEmpresa() {
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [buscandoCNPJ, setBuscandoCNPJ] = useState(false);
  const [guiaAtiva, setGuiaAtiva] = useState("");

  const normalizeCnaesSecundarios = (value) => {
    console.log("🔧 normalizeCnaesSecundarios chamado com:", value, "tipo:", typeof value);
    if (!value) return [];
    if (Array.isArray(value)) return value;
    if (typeof value === "string") {
      try {
        const parsed = JSON.parse(value);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }
    console.warn("⚠️ Valor inesperado para CNAEs, retornando array vazio");
    return [];
  };

  // Informações de CNAE
  const [cnaePrincipalDescricao, setCnaePrincipalDescricao] = useState("");
  const [cnaesSecundarios, setCnaesSecundarios] = useState([]);

  // Dados Cadastrais
  const [dadosEmpresa, setDadosEmpresa] = useState({
    cnpj: "",
    razao_social: "",
    nome_fantasia: "",
    inscricao_estadual: "",
    inscricao_municipal: "",
    email: "",
    telefone: "",
    cep: "",
    endereco: "",
    numero: "",
    complemento: "",
    bairro: "",
    cidade: "",
    uf: "",
  });

  // Dados Fiscais
  const [form, setForm] = useState({
    regime_tributario: "",
    simples_anexo: "I",
    aliquota_simples_vigente: 0,
    aliquota_simples_sugerida: 0,
    cnae_principal: "",
    cnae_descricao: "",
    cnaes_secundarios: [],
    uf: "",
  });

  useEffect(() => {
    async function carregar() {
      try {
        // Carregar dados fiscais
        const resFiscal = await api.get("/empresa/fiscal");
        console.log("📊 Dados fiscais carregados:", resFiscal.data);
        console.log("🔍 cnaes_secundarios recebido:", resFiscal.data.cnaes_secundarios);
        console.log("🔍 Tipo:", typeof resFiscal.data.cnaes_secundarios);
        console.log("🔍 É array?", Array.isArray(resFiscal.data.cnaes_secundarios));

        const cnaesSecundarios = normalizeCnaesSecundarios(resFiscal.data.cnaes_secundarios);

        console.log("✅ Após normalizar:", cnaesSecundarios);
        console.log("✅ É array agora?", Array.isArray(cnaesSecundarios));

        setForm({
          regime_tributario: resFiscal.data.regime_tributario || "",
          simples_anexo: resFiscal.data.simples_anexo || "I",
          aliquota_simples_vigente: resFiscal.data.aliquota_simples_vigente ?? 0,
          aliquota_simples_sugerida: resFiscal.data.aliquota_simples_sugerida ?? 0,
          cnae_principal: resFiscal.data.cnae_principal || "",
          cnae_descricao: resFiscal.data.cnae_descricao || "",
          cnaes_secundarios: cnaesSecundarios,
          uf: resFiscal.data.uf || "",
        });

        // Atualizar estados locais para exibição
        if (resFiscal.data.cnae_descricao) {
          setCnaePrincipalDescricao(resFiscal.data.cnae_descricao);
        }
        // Sempre atualizar cnaesSecundarios, mesmo que vazio
        setCnaesSecundarios(cnaesSecundarios);

        // Tentar carregar dados cadastrais (se endpoint existir)
        try {
          const resDados = await api.get("/empresa/dados-cadastrais");
          if (resDados.data) {
            // Garantir que campos null sejam convertidos para string vazia
            setDadosEmpresa({
              cnpj: resDados.data.cnpj || "",
              razao_social: resDados.data.razao_social || "",
              nome_fantasia: resDados.data.nome_fantasia || "",
              inscricao_estadual: resDados.data.inscricao_estadual || "",
              inscricao_municipal: resDados.data.inscricao_municipal || "",
              email: resDados.data.email || "",
              telefone: resDados.data.telefone || "",
              cep: resDados.data.cep || "",
              endereco: resDados.data.endereco || "",
              numero: resDados.data.numero || "",
              complemento: resDados.data.complemento || "",
              bairro: resDados.data.bairro || "",
              cidade: resDados.data.cidade || "",
              uf: resDados.data.uf || "",
            });
          }
        } catch (e) {
          if (e.response?.status === 404) {
            console.log("Endpoint de dados cadastrais não existe ainda");
          } else {
            throw e;
          }
        }
      } catch (e) {
        console.error("❌ Erro ao carregar configurações:", e);
        console.error("❌ Resposta completa:", e.response);
        toast.error("Erro ao carregar configurações da empresa");

        // Garantir estados seguros mesmo em caso de erro
        setCnaesSecundarios([]);
        setForm((prev) => ({
          ...prev,
          cnaes_secundarios: [],
        }));
      } finally {
        setLoading(false);
      }
    }
    carregar();
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    setGuiaAtiva(params.get("guia") || "");
  }, [location.search]);

  const CAMPOS_DESTACADOS = {
    "empresa-dados": new Set([
      "cnpj",
      "razao_social",
      "nome_fantasia",
      "email",
      "telefone",
      "cep",
      "endereco",
      "numero",
      "bairro",
      "cidade",
      "uf",
    ]),
    "empresa-fiscal": new Set(["cnae_principal", "regime_tributario"]),
  };

  const classeCampo = (name) => {
    const base =
      "w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500";
    const destacar = Boolean(CAMPOS_DESTACADOS[guiaAtiva]?.has(name));
    const guiaClasses = getGuiaClassNames(destacar);
    return destacar ? `${base} ${guiaClasses.input}` : base;
  };

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => {
      const updated = {
        ...prev,
        [name]: value,
      };

      // Se mudou o regime para Simples Nacional, garantir valores padrão
      if (name === "regime_tributario" && value === "Simples Nacional") {
        if (!updated.simples_anexo || updated.simples_anexo === "") {
          updated.simples_anexo = "I";
        }
        if (!updated.aliquota_simples_vigente || updated.aliquota_simples_vigente === 0) {
          updated.aliquota_simples_vigente = 4.0;
        }
      }

      return updated;
    });
  }

  function handleDadosChange(e) {
    const { name, value } = e.target;
    setDadosEmpresa((prev) => ({
      ...prev,
      [name]: value,
    }));
  }

  async function buscarDadosPorCNPJ() {
    const cnpjLimpo = dadosEmpresa.cnpj.replace(/[^0-9]/g, "");

    if (cnpjLimpo.length !== 14) {
      toast.error("CNPJ deve ter 14 dígitos");
      return;
    }

    setBuscandoCNPJ(true);
    try {
      const response = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${cnpjLimpo}`);

      if (!response.ok) {
        throw new Error("CNPJ não encontrado");
      }

      const dados = await response.json();
      console.log("🔍 Dados completos da API:", dados);
      console.log("📋 CNAE Fiscal:", dados.cnae_fiscal);
      console.log("📋 CNAE Descrição:", dados.cnae_fiscal_descricao);
      console.log("📋 CNAEs Secundários:", dados.cnaes_secundarios);

      // Atualizar apenas campos que vieram preenchidos da API
      const novosDados = { ...dadosEmpresa };

      if (dados.razao_social) novosDados.razao_social = dados.razao_social;
      if (dados.nome_fantasia) novosDados.nome_fantasia = dados.nome_fantasia;
      if (dados.email) novosDados.email = dados.email;

      // Inscrições (geralmente não vem da Receita Federal)
      if (dados.inscricao_estadual) novosDados.inscricao_estadual = dados.inscricao_estadual;

      // Telefone pode vir em ddd_telefone_1 ou telefone
      const telefone = dados.ddd_telefone_1 || dados.telefone;
      if (telefone) novosDados.telefone = telefone;

      // Endereço
      if (dados.cep) novosDados.cep = dados.cep.replace(/[^0-9]/g, "");
      if (dados.logradouro) novosDados.endereco = dados.logradouro;
      if (dados.numero) novosDados.numero = dados.numero;
      if (dados.complemento) novosDados.complemento = dados.complemento;
      if (dados.bairro) novosDados.bairro = dados.bairro;
      if (dados.municipio) novosDados.cidade = dados.municipio;
      if (dados.uf) novosDados.uf = dados.uf;

      setDadosEmpresa(novosDados);

      // Atualizar CNAE principal com descrição
      if (dados.cnae_fiscal) {
        const cnaeNumero = dados.cnae_fiscal.toString();
        console.log("✅ CNAE encontrado:", cnaeNumero);

        const cnaesSecundarios = normalizeCnaesSecundarios(dados.cnaes_secundarios);

        setForm((prev) => ({
          ...prev,
          cnae_principal: cnaeNumero,
          cnae_descricao: dados.cnae_fiscal_descricao || "",
          cnaes_secundarios: cnaesSecundarios,
        }));

        // Atualizar estados para exibição
        if (dados.cnae_fiscal_descricao) {
          setCnaePrincipalDescricao(dados.cnae_fiscal_descricao);
        }

        // Sempre atualizar cnaesSecundarios, mesmo que vazio
        setCnaesSecundarios(cnaesSecundarios);
        if (cnaesSecundarios.length > 0) {
          console.log(`📋 Encontrados ${cnaesSecundarios.length} CNAEs secundários`);
        }
      }

      toast.success("✅ Dados preenchidos com sucesso!");
    } catch (error) {
      console.error("Erro ao buscar CNPJ:", error);
      toast.error("❌ Erro ao buscar CNPJ. Verifique o número.");
    } finally {
      setBuscandoCNPJ(false);
    }
  }

  async function salvar() {
    setSalvando(true);
    try {
      const payload = {
        ...form,
        cnaes_secundarios: normalizeCnaesSecundarios(form.cnaes_secundarios),
      };

      console.log("💾 Salvando dados fiscais:", payload);
      console.log("📋 CNAE Descrição no form:", form.cnae_descricao);
      console.log("📋 CNAEs Secundários no form:", form.cnaes_secundarios);

      // Salvar dados fiscais
      const response = await api.put("/empresa/fiscal", payload);
      console.log("✅ Resposta do servidor (fiscal):", response.data);

      // Salvar dados cadastrais (se endpoint existir)
      try {
        console.log("💾 Salvando dados cadastrais:", dadosEmpresa);
        await api.put("/empresa/dados-cadastrais", dadosEmpresa);
      } catch (e) {
        if (e.response?.status === 404) {
          console.log("Endpoint de dados cadastrais não implementado ainda");
        } else {
          throw e;
        }
      }

      toast.success("Configurações salvas com sucesso!");
    } catch (e) {
      console.error("Erro ao salvar:", e);
      toast.error(e.response?.data?.detail || "Erro ao salvar configurações");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <ConfiguracaoFiscalEmpresaView
      loading={loading}
      guiaAtiva={guiaAtiva}
      camposDestacados={CAMPOS_DESTACADOS}
      cnaesSecundarios={cnaesSecundarios}
      form={form}
      dadosEmpresa={dadosEmpresa}
      buscandoCNPJ={buscandoCNPJ}
      salvando={salvando}
      classeCampo={classeCampo}
      buscarDadosPorCNPJ={buscarDadosPorCNPJ}
      handleDadosChange={handleDadosChange}
      handleChange={handleChange}
      cnaePrincipalDescricao={cnaePrincipalDescricao}
      salvar={salvar}
    />
  );
}
