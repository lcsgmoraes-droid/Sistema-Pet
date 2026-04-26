import { useMemo } from "react";
import { buildReturnTo } from "../../../utils/petReturnFlow";

export function useInternacoesDerivados({
  agendaForm,
  agendaProcedimentos,
  evolucoes,
  filtroPessoaHistorico,
  formNova,
  internacoes,
  location,
  pets,
  totalBaias,
  tutorNovaSelecionado,
}) {
  const pessoas = useMemo(() => {
    const mapa = new Map();
    for (const pet of pets) {
      if (!pet?.cliente_id) continue;
      if (mapa.has(String(pet.cliente_id))) continue;
      mapa.set(String(pet.cliente_id), {
        id: String(pet.cliente_id),
        nome: pet.cliente_nome ?? `Pessoa #${pet.cliente_id}`,
      });
    }
    return Array.from(mapa.values()).sort((a, b) => a.nome.localeCompare(b.nome));
  }, [pets]);

  const petsDaPessoa = useMemo(() => {
    if (!formNova.pessoa_id) return [];
    return pets.filter(
      (pet) => String(pet.cliente_id) === String(formNova.pessoa_id) && pet.ativo !== false
    );
  }, [pets, formNova.pessoa_id]);

  const tutorAtualInternacao = useMemo(() => {
    if (tutorNovaSelecionado?.id) return tutorNovaSelecionado;
    if (!formNova.pessoa_id) return null;
    return pessoas.find((item) => String(item.id) === String(formNova.pessoa_id)) || null;
  }, [pessoas, formNova.pessoa_id, tutorNovaSelecionado]);

  const retornoNovoPet = useMemo(
    () => buildReturnTo(location.pathname, location.search, { abrir_nova: "1" }),
    [location.pathname, location.search]
  );

  const petsHistoricoDaPessoa = useMemo(() => {
    if (!filtroPessoaHistorico) return [];
    return pets.filter(
      (pet) => String(pet.cliente_id) === String(filtroPessoaHistorico) && pet.ativo !== false
    );
  }, [pets, filtroPessoaHistorico]);

  const internacoesOrdenadas = useMemo(
    () => [...internacoes].sort((a, b) => new Date(b.data_entrada) - new Date(a.data_entrada)),
    [internacoes]
  );

  const ocupacaoPorBaia = useMemo(() => {
    const mapa = new Map();
    for (const internacao of internacoesOrdenadas) {
      const chave = (internacao.box || "").trim();
      if (!chave) continue;
      mapa.set(chave, internacao);
    }
    return mapa;
  }, [internacoesOrdenadas]);

  const mapaInternacao = useMemo(() => {
    const lista = [];
    for (let numero = 1; numero <= totalBaias; numero += 1) {
      const chave = String(numero);
      const ocupacao = ocupacaoPorBaia.get(chave) ?? null;
      lista.push({
        numero,
        ocupada: Boolean(ocupacao),
        internacao: ocupacao,
      });
    }

    for (const [chave, internacao] of ocupacaoPorBaia.entries()) {
      const asNumero = Number.parseInt(chave, 10);
      if (Number.isFinite(asNumero) && asNumero >= 1 && asNumero <= totalBaias) continue;
      lista.push({
        numero: chave,
        ocupada: true,
        internacao,
      });
    }

    return lista;
  }, [ocupacaoPorBaia, totalBaias]);

  const indicadoresInternacao = useMemo(() => {
    const total = internacoes.length;
    const semBaia = internacoes.filter((internacao) => !internacao.box).length;
    const comEvolucao = internacoes.filter((internacao) => (evolucoes[internacao.id] ?? []).length > 0).length;
    const procedimentosPendentes = agendaProcedimentos.filter((procedimento) => !procedimento.feito).length;
    const procedimentosAtrasados = agendaProcedimentos.filter(
      (procedimento) => !procedimento.feito && new Date(procedimento.horario).getTime() <= Date.now()
    ).length;
    const mediaDias = total === 0
      ? 0
      : internacoes.reduce((acc, internacao) => {
          const dias = Math.max(
            0,
            Math.floor((Date.now() - new Date(internacao.data_entrada).getTime()) / 86400000)
          );
          return acc + dias;
        }, 0) / total;

    return {
      total,
      semBaia,
      comEvolucao,
      semEvolucao: Math.max(0, total - comEvolucao),
      baiasOcupadas: ocupacaoPorBaia.size,
      baiasLivres: Math.max(0, totalBaias - ocupacaoPorBaia.size),
      procedimentosPendentes,
      procedimentosAtrasados,
      mediaDias: Number.isFinite(mediaDias) ? mediaDias.toFixed(1) : "0.0",
    };
  }, [internacoes, evolucoes, agendaProcedimentos, ocupacaoPorBaia, totalBaias]);

  const agendaOrdenada = useMemo(
    () => [...agendaProcedimentos].sort((a, b) => new Date(a.horario).getTime() - new Date(b.horario).getTime()),
    [agendaProcedimentos]
  );

  const internacaoPorId = useMemo(() => {
    const mapa = new Map();
    for (const internacao of internacoes) mapa.set(String(internacao.id), internacao);
    return mapa;
  }, [internacoes]);

  const internacaoSelecionadaAgenda = useMemo(() => {
    if (!agendaForm.internacao_id) return null;
    return internacaoPorId.get(String(agendaForm.internacao_id)) ?? null;
  }, [agendaForm.internacao_id, internacaoPorId]);

  const sugestaoHorario = useMemo(() => {
    const data = new Date();
    data.setMinutes(data.getMinutes() + 30);
    const pad = (value) => String(value).padStart(2, "0");
    return `${data.getFullYear()}-${pad(data.getMonth() + 1)}-${pad(data.getDate())}T${pad(data.getHours())}:${pad(data.getMinutes())}`;
  }, []);

  return {
    agendaOrdenada,
    indicadoresInternacao,
    internacaoPorId,
    internacaoSelecionadaAgenda,
    internacoesOrdenadas,
    mapaInternacao,
    pessoas,
    petsDaPessoa,
    petsHistoricoDaPessoa,
    retornoNovoPet,
    sugestaoHorario,
    tutorAtualInternacao,
  };
}
