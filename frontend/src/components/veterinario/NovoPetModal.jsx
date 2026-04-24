import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { PawPrint, X } from "lucide-react";
import { api } from "../../services/api";
import CampoIdadeInteligente from "../CampoIdadeInteligente";

const formInicial = {
  nome: "",
  especie: "",
  raca: "",
  sexo: "",
  castrado: false,
  idade_aproximada: null,
  peso: "",
  observacoes: "",
};

function montarMensagemErro(erro) {
  const detalhe = erro?.response?.data?.detail;
  if (typeof detalhe === "string" && detalhe.trim()) return detalhe;
  return "Nao foi possivel cadastrar o pet agora.";
}

export default function NovoPetModal({
  isOpen,
  tutor,
  sugestoesEspecies,
  onClose,
  onCreated,
}) {
  const [form, setForm] = useState(formInicial);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [especiesCatalogo, setEspeciesCatalogo] = useState([]);

  const especiesDisponiveis = useMemo(() => {
    const nomes = [
      ...sugestoesEspecies,
      ...especiesCatalogo.map((item) => item?.nome).filter(Boolean),
    ];
    return Array.from(new Set(nomes.map((item) => String(item).trim()).filter(Boolean))).sort((a, b) =>
      a.localeCompare(b, "pt-BR")
    );
  }, [especiesCatalogo, sugestoesEspecies]);

  useEffect(() => {
    if (!isOpen) return;
    setForm(formInicial);
    setErro("");
    setSalvando(false);
  }, [isOpen, tutor?.id]);

  useEffect(() => {
    if (!isOpen) return;

    let ativo = true;
    api
      .get("/cadastros/especies", { params: { ativo: true } })
      .then((response) => {
        if (!ativo) return;
        setEspeciesCatalogo(Array.isArray(response.data) ? response.data : []);
      })
      .catch(() => {
        if (!ativo) return;
        setEspeciesCatalogo([]);
      });

    return () => {
      ativo = false;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  function atualizarCampo(evento) {
    const { name, value, type, checked } = evento.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function cadastrarPet(evento) {
    evento.preventDefault();
    setErro("");

    if (!tutor?.id) {
      setErro("Selecione um tutor valido antes de cadastrar o pet.");
      return;
    }

    if (!form.nome.trim()) {
      setErro("Informe o nome do pet.");
      return;
    }

    if (!form.especie.trim()) {
      setErro("Informe a especie do pet.");
      return;
    }

    setSalvando(true);
    try {
      const payload = {
        cliente_id: Number(tutor.id),
        nome: form.nome.trim(),
        especie: form.especie.trim(),
        raca: form.raca.trim() || null,
        sexo: form.sexo || null,
        castrado: Boolean(form.castrado),
        idade_aproximada:
          form.idade_aproximada != null && form.idade_aproximada !== ""
            ? Number(form.idade_aproximada)
            : null,
        peso: form.peso ? Number(String(form.peso).replace(",", ".")) : null,
        observacoes: form.observacoes.trim() || null,
      };

      const response = await api.post("/pets", payload);
      onCreated?.(response.data);
    } catch (erroRequest) {
      setErro(montarMensagemErro(erroRequest));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="rounded-xl bg-cyan-50 p-3 text-cyan-600">
              <PawPrint size={20} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Cadastro rapido de pet</h2>
              <p className="text-sm text-gray-500">
                Crie o pet aqui mesmo e ele ja entra selecionado na consulta.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={salvando ? undefined : onClose}
            className="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fechar modal de novo pet"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mt-5 rounded-xl border border-cyan-100 bg-cyan-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-cyan-700">Tutor selecionado</p>
          <p className="mt-1 text-sm font-semibold text-cyan-900">{tutor?.nome || "Tutor nao informado"}</p>
          <p className="mt-1 text-xs text-cyan-700">
            {[tutor?.telefone, tutor?.celular].filter(Boolean).join(" • ") || "Sem telefone cadastrado"}
          </p>
        </div>

        {erro && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {erro}
          </div>
        )}

        <form className="mt-5 space-y-4" onSubmit={cadastrarPet}>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs font-medium text-gray-600">
                Nome do pet <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                name="nome"
                value={form.nome}
                onChange={atualizarCampo}
                placeholder="Ex.: Mel, Thor, Nina..."
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300"
                autoFocus
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">
                Especie <span className="text-red-400">*</span>
              </label>
              <input
                list="novo-pet-especies"
                type="text"
                name="especie"
                value={form.especie}
                onChange={atualizarCampo}
                placeholder="Ex.: Canina, Felina..."
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300"
              />
              <datalist id="novo-pet-especies">
                {especiesDisponiveis.map((especie) => (
                  <option key={especie} value={especie} />
                ))}
              </datalist>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Raca</label>
              <input
                type="text"
                name="raca"
                value={form.raca}
                onChange={atualizarCampo}
                placeholder="Ex.: SRD, Shih Tzu..."
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Sexo</label>
              <select
                name="sexo"
                value={form.sexo}
                onChange={atualizarCampo}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300"
              >
                <option value="">Selecione...</option>
                <option value="Macho">Macho</option>
                <option value="Femea">Femea</option>
              </select>
            </div>

            <div>
              <CampoIdadeInteligente
                value={form.idade_aproximada}
                onChange={(idadeEmMeses) =>
                  setForm((prev) => ({ ...prev, idade_aproximada: idadeEmMeses }))
                }
                label="Idade"
                mostrarDataNascimento={false}
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Peso (kg)</label>
              <input
                type="number"
                name="peso"
                value={form.peso}
                onChange={atualizarCampo}
                min="0"
                step="0.01"
                placeholder="Ex.: 4,2"
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300"
              />
            </div>

            <div className="flex items-center gap-2 pt-5">
              <input
                id="novo-pet-castrado"
                type="checkbox"
                name="castrado"
                checked={form.castrado}
                onChange={atualizarCampo}
                className="h-4 w-4 rounded border-gray-300 text-cyan-600 focus:ring-cyan-300"
              />
              <label htmlFor="novo-pet-castrado" className="text-sm text-gray-700">
                Pet castrado
              </label>
            </div>

            <div className="md:col-span-2">
              <label className="mb-1 block text-xs font-medium text-gray-600">Observacoes</label>
              <textarea
                name="observacoes"
                value={form.observacoes}
                onChange={atualizarCampo}
                rows={3}
                placeholder="Alguma observacao importante para registrar agora..."
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300"
              />
              <p className="mt-1 text-[11px] text-gray-500">
                Se precisar complementar o cadastro depois, voce ainda pode editar o pet normalmente.
              </p>
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={salvando}
              className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-60"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={salvando}
              className="flex-1 rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-700 disabled:opacity-60"
            >
              {salvando ? "Cadastrando..." : "Cadastrar e selecionar pet"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

NovoPetModal.propTypes = {
  isOpen: PropTypes.bool,
  tutor: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    nome: PropTypes.string,
    telefone: PropTypes.string,
    celular: PropTypes.string,
  }),
  sugestoesEspecies: PropTypes.arrayOf(PropTypes.string),
  onClose: PropTypes.func,
  onCreated: PropTypes.func,
};

NovoPetModal.defaultProps = {
  isOpen: false,
  tutor: null,
  sugestoesEspecies: [],
  onClose: undefined,
  onCreated: undefined,
};
