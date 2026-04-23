/**
 * VetConfiguracoes.jsx
 * Tela de configurações do módulo veterinário:
 *  - Modelo operacional (funcionário vs. parceiro)
 *  - Gerenciamento de parceiros vinculados
 */
import { useState, useEffect } from "react";
import {
  Settings,
  Building2,
  Link2,
  Trash2,
  Plus,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { vetApi } from "./vetApi";

const TIPO_RELACAO_LABEL = {
  parceiro: "Parceiro (tenant próprio)",
  funcionario: "Funcionário (mesmo tenant)",
};

export default function VetConfiguracoes() {
  const [parceiros, setParceiros] = useState([]);
  const [tenantsVet, setTenantsVet] = useState([]);
  const [consultorios, setConsultorios] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(null);

  // Formulário de novo parceiro
  const [mostrarForm, setMostrarForm] = useState(false);
  const [novoVetTenantId, setNovoVetTenantId] = useState("");
  const [novoTipoRelacao, setNovoTipoRelacao] = useState("parceiro");
  const [novaComissao, setNovaComissao] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [mostrarFormConsultorio, setMostrarFormConsultorio] = useState(false);
  const [novoConsultorioNome, setNovoConsultorioNome] = useState("");
  const [novoConsultorioDescricao, setNovoConsultorioDescricao] = useState("");
  const [novoConsultorioOrdem, setNovoConsultorioOrdem] = useState("");

  useEffect(() => {
    carregar();
  }, []);

  async function carregar() {
    try {
      setCarregando(true);
      setErro(null);
      const [parcRes, tenRes, consultRes] = await Promise.all([
        vetApi.listarParceiros(),
        vetApi.listarTenantsVeterinarios(),
        vetApi.listarConsultorios({ ativos_only: false }),
      ]);
      setParceiros(Array.isArray(parcRes.data) ? parcRes.data : []);
      setTenantsVet(Array.isArray(tenRes.data) ? tenRes.data : []);
      setConsultorios(Array.isArray(consultRes.data) ? consultRes.data : []);
    } catch {
      setErro("Não foi possível carregar as configurações de parceria.");
    } finally {
      setCarregando(false);
    }
  }

  async function salvarNovoParceiro() {
    if (!novoVetTenantId) {
      setErro("Selecione o tenant veterinário parceiro.");
      return;
    }
    try {
      setSalvando(true);
      setErro(null);
      await vetApi.criarParceiro({
        vet_tenant_id: novoVetTenantId,
        tipo_relacao: novoTipoRelacao,
        comissao_empresa_pct: novaComissao ? parseFloat(novaComissao) : null,
      });
      setSucesso("Parceiro cadastrado com sucesso!");
      setMostrarForm(false);
      setNovoVetTenantId("");
      setNovaComissao("");
      setTimeout(() => setSucesso(null), 3000);
      await carregar();
    } catch (e) {
      const msg = e?.response?.data?.detail || "Erro ao cadastrar parceiro.";
      setErro(msg);
    } finally {
      setSalvando(false);
    }
  }

  async function toggleAtivo(parceiro) {
    try {
      await vetApi.atualizarParceiro(parceiro.id, { ativo: !parceiro.ativo });
      setParceiros((prev) =>
        prev.map((p) => (p.id === parceiro.id ? { ...p, ativo: !p.ativo } : p))
      );
    } catch {
      setErro("Não foi possível atualizar o parceiro.");
    }
  }

  async function removerParceiro(id) {
    if (!window.confirm("Tem certeza que deseja remover este vínculo de parceria?")) return;
    try {
      await vetApi.removerParceiro(id);
      setParceiros((prev) => prev.filter((p) => p.id !== id));
      setSucesso("Parceiro removido.");
      setTimeout(() => setSucesso(null), 3000);
    } catch {
      setErro("Erro ao remover parceiro.");
    }
  }

  async function salvarNovoConsultorio() {
    if (!novoConsultorioNome.trim()) {
      setErro("Informe o nome do consultório.");
      return;
    }
    try {
      setSalvando(true);
      setErro(null);
      await vetApi.criarConsultorio({
        nome: novoConsultorioNome.trim(),
        descricao: novoConsultorioDescricao.trim() || undefined,
        ordem: novoConsultorioOrdem ? Number.parseInt(novoConsultorioOrdem, 10) : undefined,
      });
      setSucesso("Consultório cadastrado com sucesso!");
      setMostrarFormConsultorio(false);
      setNovoConsultorioNome("");
      setNovoConsultorioDescricao("");
      setNovoConsultorioOrdem("");
      setTimeout(() => setSucesso(null), 3000);
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail || "Erro ao cadastrar consultório.");
    } finally {
      setSalvando(false);
    }
  }

  async function toggleAtivoConsultorio(consultorio) {
    try {
      await vetApi.atualizarConsultorio(consultorio.id, { ativo: !consultorio.ativo });
      setConsultorios((prev) =>
        prev.map((item) =>
          item.id === consultorio.id ? { ...item, ativo: !consultorio.ativo } : item
        )
      );
    } catch (e) {
      setErro(e?.response?.data?.detail || "Não foi possível atualizar o consultório.");
    }
  }

  async function removerConsultorio(consultorio) {
    if (!window.confirm(`Deseja remover o consultório "${consultorio.nome}"?`)) return;
    try {
      await vetApi.removerConsultorio(consultorio.id);
      setConsultorios((prev) => prev.filter((item) => item.id !== consultorio.id));
      setSucesso("Consultório removido.");
      setTimeout(() => setSucesso(null), 3000);
    } catch (e) {
      setErro(e?.response?.data?.detail || "Erro ao remover consultório.");
    }
  }

  if (carregando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-lg">
          <Settings size={24} className="text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Configurações — Módulo Veterinário</h1>
          <p className="text-gray-500 text-sm">Gerencie o modelo operacional e os veterinários parceiros.</p>
        </div>
        <button
          onClick={carregar}
          className="ml-auto p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          title="Recarregar"
        >
          <RefreshCw size={18} />
        </button>
      </div>

      {/* Mensagem de erro */}
      {erro && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg p-4">
          <AlertCircle size={18} />
          <span>{erro}</span>
          <button onClick={() => setErro(null)} className="ml-auto text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {/* Mensagem de sucesso */}
      {sucesso && (
        <div className="flex items-center gap-2 text-green-700 bg-green-50 border border-green-200 rounded-lg p-4">
          <CheckCircle size={18} />
          <span>{sucesso}</span>
        </div>
      )}

      {/* Seção de parceiros */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Link2 size={20} className="text-blue-500" />
            <h2 className="text-lg font-semibold text-gray-900">Veterinários Parceiros</h2>
            <span className="ml-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
              {parceiros.length}
            </span>
          </div>
          <button
            onClick={() => setMostrarForm((v) => !v)}
            className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus size={16} />
            Vincular parceiro
            {mostrarForm ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>

        {/* Formulário de novo parceiro */}
        {mostrarForm && (
          <div className="p-5 bg-blue-50 border-b border-blue-100 space-y-4">
            <h3 className="font-medium text-gray-800">Novo vínculo de parceria</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tenant veterinário *
                </label>
                {tenantsVet.length === 0 ? (
                  <p className="text-sm text-gray-500 italic">
                    Nenhum tenant veterinário cadastrado no sistema.
                    O veterinário precisa ter uma conta própria no sistema.
                  </p>
                ) : (
                  <select
                    value={novoVetTenantId}
                    onChange={(e) => setNovoVetTenantId(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Selecione...</option>
                    {tenantsVet.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.nome} {t.cnpj ? `— CNPJ ${t.cnpj}` : ""}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo de relação
                </label>
                <select
                  value={novoTipoRelacao}
                  onChange={(e) => setNovoTipoRelacao(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="parceiro">Parceiro (tenant próprio)</option>
                  <option value="funcionario">Funcionário (mesmo tenant)</option>
                </select>
              </div>

              {novoTipoRelacao === "parceiro" && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Comissão da empresa (%)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.5"
                    placeholder="Ex: 20"
                    value={novaComissao}
                    onChange={(e) => setNovaComissao(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Percentual que vai para a empresa sobre os procedimentos do veterinário parceiro.
                  </p>
                </div>
              )}
            </div>
            <div className="flex gap-3">
              <button
                onClick={salvarNovoParceiro}
                disabled={salvando || !novoVetTenantId}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {salvando ? "Salvando..." : "Salvar parceiro"}
              </button>
              <button
                onClick={() => { setMostrarForm(false); setErro(null); }}
                className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}

        {/* Lista de parceiros */}
        {parceiros.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Building2 size={36} className="mx-auto mb-3 text-gray-300" />
            <p className="font-medium">Nenhum parceiro vinculado</p>
            <p className="text-sm mt-1">
              Clique em &quot;Vincular parceiro&quot; para conectar um veterinário com conta própria no sistema.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {parceiros.map((p) => (
              <div key={p.id} className="flex items-center gap-4 p-4">
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <Building2 size={20} className="text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">
                    {p.vet_tenant_nome || "Veterinário"}
                  </p>
                  <p className="text-xs text-gray-500">
                    {TIPO_RELACAO_LABEL[p.tipo_relacao] ?? p.tipo_relacao}
                    {p.comissao_empresa_pct != null && p.tipo_relacao === "parceiro" && (
                      <> · Comissão empresa: <strong>{p.comissao_empresa_pct}%</strong></>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {/* Toggle ativo/inativo */}
                  <button
                    onClick={() => toggleAtivo(p)}
                    className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
                      p.ativo
                        ? "bg-green-100 text-green-700 hover:bg-green-200"
                        : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                    }`}
                  >
                    {p.ativo ? "Ativo" : "Inativo"}
                  </button>
                  <button
                    onClick={() => removerParceiro(p.id)}
                    className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors"
                    title="Remover vínculo"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Building2 size={20} className="text-emerald-500" />
            <h2 className="text-lg font-semibold text-gray-900">Consultórios / Salas</h2>
            <span className="ml-1 text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
              {consultorios.length}
            </span>
          </div>
          <button
            onClick={() => setMostrarFormConsultorio((v) => !v)}
            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 transition-colors"
          >
            <Plus size={16} />
            Novo consultório
            {mostrarFormConsultorio ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>

        {mostrarFormConsultorio && (
          <div className="p-5 bg-emerald-50 border-b border-emerald-100 space-y-4">
            <h3 className="font-medium text-gray-800">Cadastrar consultório</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
                <input
                  type="text"
                  value={novoConsultorioNome}
                  onChange={(e) => setNovoConsultorioNome(e.target.value)}
                  placeholder="Ex: Consultório 1"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ordem</label>
                <input
                  type="number"
                  min="1"
                  max="999"
                  value={novoConsultorioOrdem}
                  onChange={(e) => setNovoConsultorioOrdem(e.target.value)}
                  placeholder="Ex: 1"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                />
              </div>
              <div className="sm:col-span-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
                <input
                  type="text"
                  value={novoConsultorioDescricao}
                  onChange={(e) => setNovoConsultorioDescricao(e.target.value)}
                  placeholder="Opcional. Ex: Sala com ultrassom"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                />
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={salvarNovoConsultorio}
                disabled={salvando || !novoConsultorioNome.trim()}
                className="px-4 py-2 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {salvando ? "Salvando..." : "Salvar consultório"}
              </button>
              <button
                onClick={() => {
                  setMostrarFormConsultorio(false);
                  setNovoConsultorioNome("");
                  setNovoConsultorioDescricao("");
                  setNovoConsultorioOrdem("");
                }}
                className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}

        {consultorios.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Building2 size={36} className="mx-auto mb-3 text-gray-300" />
            <p className="font-medium">Nenhum consultório cadastrado</p>
            <p className="text-sm mt-1">
              Cadastre as salas para a agenda alertar conflito por consultório.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {consultorios.map((consultorio) => (
              <div key={consultorio.id} className="flex items-center gap-4 p-4">
                <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
                  <Building2 size={20} className="text-emerald-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">{consultorio.nome}</p>
                  <p className="text-xs text-gray-500">
                    Ordem {consultorio.ordem}
                    {consultorio.descricao ? ` · ${consultorio.descricao}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleAtivoConsultorio(consultorio)}
                    className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
                      consultorio.ativo
                        ? "bg-green-100 text-green-700 hover:bg-green-200"
                        : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                    }`}
                  >
                    {consultorio.ativo ? "Ativo" : "Inativo"}
                  </button>
                  <button
                    onClick={() => removerConsultorio(consultorio)}
                    className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors"
                    title="Remover consultório"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Informativo sobre multi-tenant */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 text-sm text-amber-800 space-y-2">
        <p className="font-semibold">Como funciona o veterinário parceiro?</p>
        <ul className="list-disc pl-5 space-y-1">
          <li>O veterinário parceiro tem sua <strong>própria conta no sistema</strong> (tenant independente).</li>
          <li>Prontuários, financeiro e estoque ficam <strong>separados</strong> por conta.</li>
          <li>A loja vê apenas o resumo do pet (vacinas, alergias, peso) — não o prontuário completo.</li>
          <li>A comissão configurada é calculada sobre os procedimentos realizados pelo veterinário.</li>
          <li>Para o veterinário se cadastrar como parceiro, ele precisa criar uma conta própria no sistema
            com tipo de organização &quot;Clínica Veterinária&quot;.</li>
        </ul>
      </div>
    </div>
  );
}
