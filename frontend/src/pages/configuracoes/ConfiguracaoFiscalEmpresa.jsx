import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../../services/api";
import toast from "react-hot-toast";
import { getGuiaClassNames } from "../../utils/guiaHighlight";

export default function ConfiguracaoFiscalEmpresa() {
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [buscandoCNPJ, setBuscandoCNPJ] = useState(false);
  const [guiaAtiva, setGuiaAtiva] = useState("");

  const normalizeCnaesSecundarios = (value) => {
    console.log('🔧 normalizeCnaesSecundarios chamado com:', value, 'tipo:', typeof value);
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
    console.warn('⚠️ Valor inesperado para CNAEs, retornando array vazio');
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
    uf: ""
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
    uf: ""
  });

  useEffect(() => {
    async function carregar() {
      try {
        // Carregar dados fiscais
        const resFiscal = await api.get("/empresa/fiscal");
        console.log('📊 Dados fiscais carregados:', resFiscal.data);
        console.log('🔍 cnaes_secundarios recebido:', resFiscal.data.cnaes_secundarios);
        console.log('🔍 Tipo:', typeof resFiscal.data.cnaes_secundarios);
        console.log('🔍 É array?', Array.isArray(resFiscal.data.cnaes_secundarios));
        
        const cnaesSecundarios = normalizeCnaesSecundarios(
          resFiscal.data.cnaes_secundarios
        );
        
        console.log('✅ Após normalizar:', cnaesSecundarios);
        console.log('✅ É array agora?', Array.isArray(cnaesSecundarios));

        setForm({
          regime_tributario: resFiscal.data.regime_tributario || "",
          simples_anexo: resFiscal.data.simples_anexo || "I",
          aliquota_simples_vigente: resFiscal.data.aliquota_simples_vigente ?? 0,
          aliquota_simples_sugerida: resFiscal.data.aliquota_simples_sugerida ?? 0,
          cnae_principal: resFiscal.data.cnae_principal || "",
          cnae_descricao: resFiscal.data.cnae_descricao || "",
          cnaes_secundarios: cnaesSecundarios,
          uf: resFiscal.data.uf || ""
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
              uf: resDados.data.uf || ""
            });
          }
        } catch (e) {
          console.log("Endpoint de dados cadastrais não existe ainda");
        }
      } catch (e) {
        console.error("❌ Erro ao carregar configurações:", e);
        console.error("❌ Resposta completa:", e.response);
        toast.error("Erro ao carregar configurações da empresa");
        
        // Garantir estados seguros mesmo em caso de erro
        setCnaesSecundarios([]);
        setForm(prev => ({
          ...prev,
          cnaes_secundarios: []
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
    return destacar
      ? `${base} ${guiaClasses.input}`
      : base;
  };

  function handleChange(e) {
    const { name, value } = e.target;
    setForm(prev => {
      const updated = {
        ...prev,
        [name]: value
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
    setDadosEmpresa(prev => ({
      ...prev,
      [name]: value
    }));
  }

  async function buscarDadosPorCNPJ() {
    const cnpjLimpo = dadosEmpresa.cnpj.replace(/[^0-9]/g, '');
    
    if (cnpjLimpo.length !== 14) {
      toast.error('CNPJ deve ter 14 dígitos');
      return;
    }

    setBuscandoCNPJ(true);
    try {
      const response = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${cnpjLimpo}`);
      
      if (!response.ok) {
        throw new Error('CNPJ não encontrado');
      }
      
      const dados = await response.json();
      console.log('🔍 Dados completos da API:', dados);
      console.log('📋 CNAE Fiscal:', dados.cnae_fiscal);
      console.log('📋 CNAE Descrição:', dados.cnae_fiscal_descricao);
      console.log('📋 CNAEs Secundários:', dados.cnaes_secundarios);
      
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
      if (dados.cep) novosDados.cep = dados.cep.replace(/[^0-9]/g, '');
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
        console.log('✅ CNAE encontrado:', cnaeNumero);
        
        const cnaesSecundarios = normalizeCnaesSecundarios(
          dados.cnaes_secundarios
        );

        setForm(prev => ({
          ...prev,
          cnae_principal: cnaeNumero,
          cnae_descricao: dados.cnae_fiscal_descricao || "",
          cnaes_secundarios: cnaesSecundarios
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
      
      toast.success('✅ Dados preenchidos com sucesso!');
    } catch (error) {
      console.error('Erro ao buscar CNPJ:', error);
      toast.error('❌ Erro ao buscar CNPJ. Verifique o número.');
    } finally {
      setBuscandoCNPJ(false);
    }
  }

  async function salvar() {
    setSalvando(true);
    try {
      const payload = {
        ...form,
        cnaes_secundarios: normalizeCnaesSecundarios(form.cnaes_secundarios)
      };

      console.log('💾 Salvando dados fiscais:', payload);
      console.log('📋 CNAE Descrição no form:', form.cnae_descricao);
      console.log('📋 CNAEs Secundários no form:', form.cnaes_secundarios);
      
      // Salvar dados fiscais
      const response = await api.put("/empresa/fiscal", payload);
      console.log('✅ Resposta do servidor (fiscal):', response.data);
      
      // Salvar dados cadastrais (se endpoint existir)
      try {
        console.log('💾 Salvando dados cadastrais:', dadosEmpresa);
        await api.put("/empresa/dados-cadastrais", dadosEmpresa);
      } catch (e) {
        console.log("Endpoint de dados cadastrais não implementado ainda");
      }
      
      toast.success("Configurações salvas com sucesso!");
    } catch (e) {
      console.error("Erro ao salvar:", e);
      toast.error(e.response?.data?.detail || "Erro ao salvar configurações");
    } finally {
      setSalvando(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando configurações...</p>
        </div>
      </div>
    );
  }

  // 🛡️ PROTEÇÃO: Garantir que cnaesSecundarios seja SEMPRE um array
  const cnaesSecundariosSeguro = Array.isArray(cnaesSecundarios) ? cnaesSecundarios : [];
  
  const simplesAtivo = form.regime_tributario === "Simples Nacional";

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Configuração da Empresa</h1>
        <p className="text-gray-600 mt-1">
          Configure os dados cadastrais, fiscais e tributários da sua empresa
        </p>
      </div>

      <div className="space-y-6">
        {guiaAtiva && (CAMPOS_DESTACADOS[guiaAtiva]?.size ?? 0) > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
            Campos desta etapa foram destacados em amarelo para facilitar o preenchimento.
          </div>
        )}

        {/* ===== SEÇÃO 1: DADOS CADASTRAIS ===== */}
        <div className="bg-white rounded-lg shadow">
          <div className="bg-blue-50 px-6 py-4 border-b border-blue-100">
            <h2 className="text-lg font-semibold text-blue-900">📋 Dados Cadastrais</h2>
            <p className="text-sm text-blue-700 mt-2">
              💡 <strong>Dica:</strong> Digite o CNPJ e clique no botão 🔍 para preencher automaticamente 
              os dados da empresa (razão social, endereço, CNAEs, etc.) consultando a Receita Federal.
            </p>
          </div>
          <div className="p-6 space-y-4">
            {/* Linha 1: CNPJ e Razão Social */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  CNPJ <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    name="cnpj"
                    value={dadosEmpresa.cnpj}
                    onChange={handleDadosChange}
                    placeholder="00.000.000/0000-00"
                    maxLength="18"
                    className={`${classeCampo("cnpj")} flex-1`}
                  />
                  <button
                    type="button"
                    onClick={buscarDadosPorCNPJ}
                    disabled={buscandoCNPJ || !dadosEmpresa.cnpj}
                    title="Buscar dados da Receita Federal pelo CNPJ"
                    className="px-3 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:from-blue-700 hover:to-blue-800 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed flex items-center justify-center shadow-md hover:shadow-lg transition-all duration-200"
                  >
                    {buscandoCNPJ ? (
                      <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    ) : (
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Razão Social <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="razao_social"
                  value={dadosEmpresa.razao_social}
                  onChange={handleDadosChange}
                  placeholder="Nome empresarial completo"
                  className={classeCampo("razao_social")}
                />
              </div>
            </div>

            {/* Linha 2: Nome Fantasia */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nome Fantasia
              </label>
              <input
                type="text"
                name="nome_fantasia"
                value={dadosEmpresa.nome_fantasia}
                onChange={handleDadosChange}
                placeholder="Nome comercial"
                className={classeCampo("nome_fantasia")}
              />
            </div>

            {/* Linha 3: Inscrições */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Inscrição Estadual
                </label>
                <input
                  type="text"
                  name="inscricao_estadual"
                  value={dadosEmpresa.inscricao_estadual}
                  onChange={handleDadosChange}
                  placeholder="000.000.000.000"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Inscrição Municipal
                </label>
                <input
                  type="text"
                  name="inscricao_municipal"
                  value={dadosEmpresa.inscricao_municipal}
                  onChange={handleDadosChange}
                  placeholder="000000"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Linha 4: Contatos */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  E-mail
                </label>
                <input
                  type="email"
                  name="email"
                  value={dadosEmpresa.email}
                  onChange={handleDadosChange}
                  placeholder="contato@empresa.com.br"
                  className={classeCampo("email")}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Telefone
                </label>
                <input
                  type="text"
                  name="telefone"
                  value={dadosEmpresa.telefone}
                  onChange={handleDadosChange}
                  placeholder="(00) 0000-0000"
                  className={classeCampo("telefone")}
                />
              </div>
            </div>

            {/* Linha 5: Endereço */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="md:col-span-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  CEP
                </label>
                <input
                  type="text"
                  name="cep"
                  value={dadosEmpresa.cep}
                  onChange={handleDadosChange}
                  placeholder="00000-000"
                  maxLength="9"
                  className={classeCampo("cep")}
                />
              </div>
              <div className="md:col-span-3">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Endereço
                </label>
                <input
                  type="text"
                  name="endereco"
                  value={dadosEmpresa.endereco}
                  onChange={handleDadosChange}
                  placeholder="Rua, Avenida, etc"
                  className={classeCampo("endereco")}
                />
              </div>
            </div>

            {/* Linha 6: Complemento do Endereço */}
            <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
              <div className="md:col-span-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Número
                </label>
                <input
                  type="text"
                  name="numero"
                  value={dadosEmpresa.numero}
                  onChange={handleDadosChange}
                  placeholder="123"
                  className={classeCampo("numero")}
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Complemento
                </label>
                <input
                  type="text"
                  name="complemento"
                  value={dadosEmpresa.complemento}
                  onChange={handleDadosChange}
                  placeholder="Sala, Apto, etc"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Bairro
                </label>
                <input
                  type="text"
                  name="bairro"
                  value={dadosEmpresa.bairro}
                  onChange={handleDadosChange}
                  placeholder="Centro"
                  className={classeCampo("bairro")}
                />
              </div>
              <div className="md:col-span-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  UF
                </label>
                <select
                  name="uf"
                  value={dadosEmpresa.uf}
                  onChange={handleDadosChange}
                  className={classeCampo("uf")}
                >
                  <option value="">-</option>
                  <option value="SP">SP</option>
                  <option value="RJ">RJ</option>
                  <option value="MG">MG</option>
                  <option value="RS">RS</option>
                  <option value="PR">PR</option>
                  <option value="SC">SC</option>
                  <option value="BA">BA</option>
                  <option value="PE">PE</option>
                  <option value="CE">CE</option>
                  <option value="GO">GO</option>
                  <option value="DF">DF</option>
                </select>
              </div>
            </div>

            {/* Linha 7: Cidade */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Cidade
              </label>
              <input
                type="text"
                name="cidade"
                value={dadosEmpresa.cidade}
                onChange={handleDadosChange}
                placeholder="Nome da cidade"
                className={classeCampo("cidade")}
              />
            </div>
          </div>
        </div>

        {/* ===== SEÇÃO 2: CONFIGURAÇÃO FISCAL ===== */}
        <div className="bg-white rounded-lg shadow">
          <div className="bg-green-50 px-6 py-4 border-b border-green-100">
            <h2 className="text-lg font-semibold text-green-900">💰 Configuração Fiscal e Tributária</h2>
          </div>
          <div className="p-6 space-y-4">
            {/* CNAE */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                CNAE Principal
              </label>
              <input
                type="text"
                name="cnae_principal"
                value={form.cnae_principal}
                onChange={handleChange}
                placeholder="0000-0/00"
                className={classeCampo("cnae_principal")}
              />
              {cnaePrincipalDescricao && (
                <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <p className="text-sm text-blue-900 font-medium">📋 {cnaePrincipalDescricao}</p>
                </div>
              )}
              <p className="text-xs text-gray-500 mt-1">
                Código da Classificação Nacional de Atividades Econômicas
              </p>
            </div>
            
            {/* CNAEs Secundários */}
            {cnaesSecundariosSeguro.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  CNAEs Secundários ({cnaesSecundariosSeguro.length})
                </label>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {cnaesSecundariosSeguro.map((cnae, index) => (
                    <div key={index} className="p-3 bg-gray-50 border border-gray-200 rounded-md text-sm">
                      <span className="font-semibold text-gray-700">{cnae?.codigo || 'N/A'}</span>
                      <span className="text-gray-600"> - {cnae?.descricao || 'Sem descrição'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
        
            {/* Regime Tributário */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Regime Tributário <span className="text-red-500">*</span>
              </label>
              <select
                name="regime_tributario"
                value={form.regime_tributario}
                onChange={handleChange}
                className={classeCampo("regime_tributario")}
              >
                <option value="">Selecione...</option>
                <option value="Simples Nacional">Simples Nacional</option>
                <option value="Lucro Presumido">Lucro Presumido</option>
                <option value="Lucro Real">Lucro Real</option>
              </select>
            </div>

            {/* Bloco Simples Nacional - Exibido apenas se regime = Simples */}
            {simplesAtivo && (
              <div className="border-l-4 border-blue-500 bg-blue-50 p-4 space-y-4">
                <h3 className="text-base font-semibold text-blue-900">
                  Parâmetros do Simples Nacional
                </h3>

                {/* Anexo */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Anexo
                  </label>
                  <select
                    name="simples_anexo"
                    value={form.simples_anexo || "I"}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="I">Anexo I - Comércio</option>
                    <option value="II">Anexo II - Indústria</option>
                    <option value="III">Anexo III - Serviços</option>
                    <option value="IV">Anexo IV - Serviços (Construção)</option>
                    <option value="V">Anexo V - Serviços (Intelectual)</option>
                  </select>
                </div>

                {/* Alíquota Vigente */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Alíquota Vigente (%)
                  </label>
                  <input
                    type="number"
                    name="aliquota_simples_vigente"
                    value={form.aliquota_simples_vigente || ""}
                    onChange={handleChange}
                    step="0.01"
                    min="0"
                    max="100"
                    placeholder="Ex: 4.00"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Alíquota atual utilizada para calcular provisões
                  </p>
                </div>

                {/* Alíquota Sugerida (Apenas Info) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Alíquota Sugerida (%)
                  </label>
                  <input
                    type="number"
                    name="aliquota_simples_sugerida"
                    value={form.aliquota_simples_sugerida || ""}
                    onChange={handleChange}
                    step="0.01"
                    min="0"
                    max="100"
                    placeholder="Ex: 4.50"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Sugestão baseada no histórico de fechamentos (informativo)
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Ações */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={salvar}
            disabled={salvando}
            className="px-8 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {salvando ? "Salvando..." : "Salvar Todas as Configurações"}
          </button>
        </div>
      </div>
    </div>
  );
}
