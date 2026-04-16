import { CheckCircle, X } from "lucide-react";
import { useState } from "react";
import api from "../../api";

function validarCpf(cpf) {
  const digits = String(cpf || "").replace(/\D/g, "");
  if (digits.length !== 11 || /^(\d)\1{10}$/.test(digits)) return false;

  const calcularDigito = (base, factor) => {
    let total = 0;
    for (const char of base) {
      total += Number(char) * factor;
      factor -= 1;
    }
    const rest = (total * 10) % 11;
    return rest === 10 ? 0 : rest;
  };

  const dig1 = calcularDigito(digits.slice(0, 9), 10);
  const dig2 = calcularDigito(digits.slice(0, 10), 11);
  return dig1 === Number(digits[9]) && dig2 === Number(digits[10]);
}

function inferirDadosIniciais(valorBuscaInicial) {
  const base = {
    nome: "",
    data_nascimento: "",
    telefone: "",
    cpf: "",
    email: "",
  };

  const texto = String(valorBuscaInicial || "").trim();
  if (!texto) return base;

  const digitos = texto.replace(/\D/g, "");
  const temLetras = /[a-zA-ZÀ-ÿ]/.test(texto);

  if (texto.includes("@")) {
    return { ...base, email: texto };
  }

  if (temLetras) {
    return { ...base, nome: texto };
  }

  if (digitos.length === 11 && validarCpf(digitos)) {
    return { ...base, cpf: texto };
  }

  if (digitos.length >= 10) {
    return { ...base, telefone: texto };
  }

  if (digitos.length > 0) {
    return { ...base, nome: texto };
  }

  return base;
}

export default function ModalCadastroCliente({ onClose, onClienteCriado, valorBuscaInicial }) {
  const [formData, setFormData] = useState({
    ...inferirDadosIniciais(valorBuscaInicial),
  });
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!formData.nome || !formData.telefone) {
      setErro("Nome e telefone sao obrigatorios");
      return;
    }

    setLoading(true);
    setErro("");

    try {
      const response = await api.post("/clientes", {
        ...formData,
        data_nascimento: formData.data_nascimento || null,
        tipo_cadastro: "cliente",
        tipo_pessoa: "PF",
      });

      onClienteCriado(response.data);
    } catch (error) {
      console.error("Erro ao cadastrar cliente rapido:", error);
      setErro("Erro ao cadastrar cliente");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="mx-4 w-full max-w-md rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b p-6">
          <h2 className="text-xl font-bold text-gray-900">Cadastro rapido</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-2 transition-colors hover:bg-gray-100"
            type="button"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          {erro && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {erro}
            </div>
          )}

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Nome *
            </label>
            <input
              type="text"
              value={formData.nome}
              onChange={(event) =>
                setFormData({ ...formData, nome: event.target.value })
              }
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Telefone *
            </label>
            <input
              type="tel"
              value={formData.telefone}
              onChange={(event) =>
                setFormData({ ...formData, telefone: event.target.value })
              }
              placeholder="(00) 00000-0000"
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              CPF
            </label>
            <input
              type="text"
              value={formData.cpf}
              onChange={(event) =>
                setFormData({ ...formData, cpf: event.target.value })
              }
              placeholder="000.000.000-00"
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Data de nascimento
            </label>
            <input
              type="date"
              value={formData.data_nascimento || ""}
              onChange={(event) =>
                setFormData({
                  ...formData,
                  data_nascimento: event.target.value,
                })
              }
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              E-mail
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(event) =>
                setFormData({ ...formData, email: event.target.value })
              }
              placeholder="cliente@email.com"
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-lg bg-gray-100 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-200 disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center space-x-2 rounded-lg bg-blue-600 px-6 py-2 font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  <span>Cadastrando...</span>
                </>
              ) : (
                <>
                  <CheckCircle className="h-5 w-5" />
                  <span>Cadastrar</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
