import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { Building2, Plus, Save, Trash2 } from "lucide-react";

import { orcamentosGrupoApi } from "../../api/orcamentosGrupo";
import PessoaSelector from "../../components/clientes/PessoaSelector";
import ModalCadastroCliente from "../../components/pdv/ModalCadastroCliente";
import ActionButton from "../../components/ui/ActionButton";

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";

function erro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

export default function EmpresaGrupoConfigPanel({ configuracao, empresas, onAtualizar }) {
  const [form, setForm] = useState(configuracao);
  const [busca, setBusca] = useState("");
  const [resultados, setResultados] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [buscandoPessoas, setBuscandoPessoas] = useState(false);
  const [mostrarCadastroPessoa, setMostrarCadastroPessoa] = useState(false);
  const buscaAtualRef = useRef(0);

  useEffect(() => setForm(configuracao), [configuracao]);

  useEffect(() => {
    const termo = busca.trim();
    const buscaId = ++buscaAtualRef.current;

    if (termo.length < 2) {
      setResultados([]);
      setBuscandoPessoas(false);
      return undefined;
    }

    setBuscandoPessoas(true);
    const timeoutId = window.setTimeout(async () => {
      try {
        const response = await orcamentosGrupoApi.buscarPessoas(termo);
        if (buscaAtualRef.current !== buscaId) return;

        const empresasJaAdicionadas = new Set(empresas.map((empresa) => empresa.cliente_id));
        setResultados(
          (response.data || []).filter((pessoa) => !empresasJaAdicionadas.has(pessoa.id)),
        );
      } catch (error) {
        if (buscaAtualRef.current !== buscaId) return;
        setResultados([]);
        toast.error(erro(error, "Não foi possível buscar as pessoas."));
      } finally {
        if (buscaAtualRef.current === buscaId) setBuscandoPessoas(false);
      }
    }, 300);

    return () => window.clearTimeout(timeoutId);
  }, [busca, empresas]);

  async function salvarConfiguracao(event) {
    event.preventDefault();
    setCarregando(true);
    try {
      await orcamentosGrupoApi.salvarConfiguracao({
        ...form,
        percentual_minimo: Number(form.percentual_minimo),
        percentual_maximo: Number(form.percentual_maximo),
        quantidade_empresas: Number(form.quantidade_empresas),
        validade_dias: Number(form.validade_dias),
      });
      toast.success("Regras dos orçamentos salvas.");
      await onAtualizar();
    } catch (error) {
      toast.error(erro(error, "Não foi possível salvar as regras."));
    } finally {
      setCarregando(false);
    }
  }

  async function adicionar(pessoa) {
    setCarregando(true);
    try {
      await orcamentosGrupoApi.adicionarEmpresa({ cliente_id: pessoa.id });
      toast.success(`${pessoa.nome} adicionada às empresas do grupo.`);
      setBusca("");
      setResultados([]);
      await onAtualizar();
    } catch (error) {
      toast.error(erro(error, "Não foi possível adicionar a empresa."));
    } finally {
      setCarregando(false);
    }
  }

  async function adicionarPessoaCriada(pessoa) {
    setMostrarCadastroPessoa(false);
    await adicionar(pessoa);
  }

  async function alternarFixada(empresa) {
    try {
      await orcamentosGrupoApi.atualizarEmpresa(empresa.id, {
        fixada_padrao: !empresa.fixada_padrao,
      });
      await onAtualizar();
    } catch (error) {
      toast.error(erro(error, "Não foi possível atualizar a empresa."));
    }
  }

  async function remover(empresa) {
    try {
      await orcamentosGrupoApi.removerEmpresa(empresa.id);
      toast.success("Empresa removida da lista de orçamentos.");
      await onAtualizar();
    } catch (error) {
      toast.error(erro(error, "Não foi possível remover a empresa."));
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <form
        onSubmit={salvarConfiguracao}
        className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950"
      >
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-teal-50 p-2 text-teal-700 dark:bg-teal-500/10 dark:text-teal-200">
            <Save size={18} />
          </div>
          <div>
            <h2 className="font-semibold text-slate-900 dark:text-slate-100">Regras de cálculo</h2>
            <p className="text-xs text-slate-500">Faixa usada para cada empresa comparada.</p>
          </div>
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <label className="text-sm text-slate-700 dark:text-slate-300">
            Percentual mínimo
            <input
              className={`${inputClass} mt-1`}
              type="number"
              min="0"
              max="500"
              step="0.01"
              value={form?.percentual_minimo ?? 10}
              onChange={(event) =>
                setForm((atual) => ({ ...atual, percentual_minimo: event.target.value }))
              }
            />
          </label>
          <label className="text-sm text-slate-700 dark:text-slate-300">
            Percentual máximo
            <input
              className={`${inputClass} mt-1`}
              type="number"
              min="0"
              max="500"
              step="0.01"
              value={form?.percentual_maximo ?? 30}
              onChange={(event) =>
                setForm((atual) => ({ ...atual, percentual_maximo: event.target.value }))
              }
            />
          </label>
          <label className="text-sm text-slate-700 dark:text-slate-300">
            Empresas comparadas
            <input
              className={`${inputClass} mt-1`}
              type="number"
              min="1"
              max="5"
              value={form?.quantidade_empresas ?? 2}
              onChange={(event) =>
                setForm((atual) => ({ ...atual, quantidade_empresas: event.target.value }))
              }
            />
          </label>
          <label className="text-sm text-slate-700 dark:text-slate-300">
            Validade padrão em dias
            <input
              className={`${inputClass} mt-1`}
              type="number"
              min="1"
              max="365"
              value={form?.validade_dias ?? 15}
              onChange={(event) =>
                setForm((atual) => ({ ...atual, validade_dias: event.target.value }))
              }
            />
          </label>
        </div>
        <label className="mt-4 block text-sm text-slate-700 dark:text-slate-300">
          Observações padrão
          <textarea
            className={`${inputClass} mt-1 min-h-24`}
            value={form?.observacoes_padrao || ""}
            onChange={(event) =>
              setForm((atual) => ({ ...atual, observacoes_padrao: event.target.value }))
            }
          />
        </label>
        <button
          type="submit"
          disabled={carregando}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50"
        >
          <Save size={16} /> Salvar regras
        </button>
      </form>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-blue-50 p-2 text-blue-700 dark:bg-blue-500/10 dark:text-blue-200">
            <Building2 size={18} />
          </div>
          <div>
            <h2 className="font-semibold text-slate-900 dark:text-slate-100">Empresas do grupo</h2>
            <p className="text-xs text-slate-500">
              Busque uma Pessoa já cadastrada e habilite-a para os orçamentos.
            </p>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-start">
          <PessoaSelector
            className="min-w-0 flex-1"
            disabled={carregando}
            minChars={2}
            value={busca}
            onChange={setBusca}
            onSelect={adicionar}
            placeholder="Digite nome, CPF/CNPJ ou telefone..."
            showSuggestions={resultados.length > 0}
            suggestions={resultados}
            inputClassName="h-10 border-slate-300 bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            renderSuggestion={(pessoa) => (
              <button
                key={pessoa.id}
                type="button"
                onClick={() => adicionar(pessoa)}
                className="flex w-full items-center justify-between gap-3 border-b px-4 py-3 text-left last:border-b-0 hover:bg-blue-50 dark:border-slate-800 dark:hover:bg-slate-800"
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {pessoa.nome}
                  </span>
                  <span className="block text-xs text-slate-500">
                    {pessoa.cnpj ||
                      pessoa.razao_social ||
                      pessoa.telefone ||
                      "Cadastro sem documento"}
                  </span>
                </span>
                <span className="inline-flex flex-shrink-0 items-center gap-1 text-xs font-semibold text-blue-700 dark:text-blue-300">
                  <Plus size={14} /> Adicionar
                </span>
              </button>
            )}
          />
          <ActionButton
            type="button"
            onClick={() => setMostrarCadastroPessoa(true)}
            disabled={carregando}
            icon={Plus}
            intent="create"
            size="md"
            className="h-10 w-full whitespace-nowrap sm:w-auto"
          >
            Novo
          </ActionButton>
        </div>

        {buscandoPessoas && busca.trim().length >= 2 ? (
          <p className="mt-2 text-center text-sm text-slate-500">Buscando pessoas...</p>
        ) : null}
        {!buscandoPessoas && busca.trim().length >= 2 && resultados.length === 0 ? (
          <p className="mt-2 text-center text-sm text-slate-500">Nenhuma pessoa encontrada</p>
        ) : null}

        <div className="mt-4 space-y-2">
          {empresas.length === 0 ? (
            <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-500 dark:bg-slate-900">
              Nenhuma empresa do grupo cadastrada para esta finalidade.
            </p>
          ) : (
            empresas.map((empresa) => (
              <div
                key={empresa.id}
                className="flex flex-col gap-3 rounded-xl border border-slate-200 p-3 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {empresa.nome}
                  </p>
                  <p className="text-xs text-slate-500">
                    {empresa.cnpj || empresa.razao_social || "Dados cadastrais incompletos"}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={empresa.fixada_padrao}
                      onChange={() => alternarFixada(empresa)}
                      className="h-4 w-4 rounded border-slate-300 text-teal-600"
                    />
                    Fixar por padrão
                  </label>
                  <button
                    type="button"
                    onClick={() => remover(empresa)}
                    className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"
                    aria-label={`Remover ${empresa.nome}`}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {mostrarCadastroPessoa ? (
        <ModalCadastroCliente
          onClose={() => setMostrarCadastroPessoa(false)}
          onClienteCriado={adicionarPessoaCriada}
          valorBuscaInicial={busca}
        />
      ) : null}
    </div>
  );
}
