import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import { confirmarCorePet } from "../../services/corepetDialog";

export default function useVendasGruposProdutos({
  dataInicio,
  dataFim,
  vendedorSelecionado,
  produtosSelecionados,
  setProdutosSelecionados,
}) {
  const [gruposSalvos, setGruposSalvos] = useState([]);
  const [grupoSelecionado, setGrupoSelecionado] = useState("");
  const [nomeGrupo, setNomeGrupo] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [erroGrupos, setErroGrupos] = useState("");
  const [configurando, setConfigurando] = useState(false);
  const grupo = gruposSalvos.find((item) => String(item.id) === String(grupoSelecionado));

  useEffect(() => {
    let ativo = true;
    api
      .get("/comissoes/grupos-produtos")
      .then(({ data }) => {
        if (ativo) setGruposSalvos(data.data || []);
      })
      .catch((erro) => {
        if (ativo)
          setErroGrupos(
            erro.response?.data?.detail || "Não foi possível carregar os grupos de comissão.",
          );
      });
    return () => {
      ativo = false;
    };
  }, []);

  const selecionarGrupo = (id) => {
    setGrupoSelecionado(id);
    const selecionado = gruposSalvos.find((item) => String(item.id) === String(id));
    setNomeGrupo(selecionado?.nome || "");
    if (selecionado) setProdutosSelecionados(selecionado.produto_ids.map(String));
  };

  const salvar = async (atualizar = false) => {
    if (!nomeGrupo.trim() || !produtosSelecionados.length) {
      toast.error("Informe o nome e selecione os produtos do grupo.");
      return;
    }
    setOcupado(true);
    try {
      const payload = { nome: nomeGrupo.trim(), produto_ids: produtosSelecionados.map(Number) };
      const { data } = atualizar
        ? await api.put(`/comissoes/grupos-produtos/${grupo.id}`, payload)
        : await api.post("/comissoes/grupos-produtos", payload);
      setGruposSalvos((atuais) =>
        [...atuais.filter((item) => item.id !== data.data.id), data.data].sort((a, b) =>
          a.nome.localeCompare(b.nome, "pt-BR"),
        ),
      );
      setGrupoSelecionado(String(data.data.id));
      toast.success("Grupo de produtos salvo.");
    } catch (erro) {
      toast.error(erro.response?.data?.detail || "Não foi possível salvar o grupo.");
    } finally {
      setOcupado(false);
    }
  };

  const provisionar = async () => {
    if (!grupo || vendedorSelecionado === "sem-vendedor") return;
    if (
      !(await confirmarCorePet(
        `Gerar contas a pagar das comissões já calculadas do grupo "${grupo.nome}", de ${dataInicio} até ${dataFim}? Comissões já provisionadas não serão duplicadas.`,
      ))
    )
      return;
    setOcupado(true);
    try {
      const { data } = await api.post(`/comissoes/grupos-produtos/${grupo.id}/provisionar`, {
        data_inicio: dataInicio,
        data_fim: dataFim,
        funcionario_id: vendedorSelecionado ? Number(vendedorSelecionado) : null,
      });
      toast.success(data.message);
    } catch (erro) {
      toast.error(erro.response?.data?.detail || "Não foi possível gerar as contas a pagar.");
    } finally {
      setOcupado(false);
    }
  };

  const grupoAlterado = Boolean(
    grupo &&
    (grupo.nome !== nomeGrupo.trim() ||
      JSON.stringify([...grupo.produto_ids].map(String).sort()) !==
        JSON.stringify([...produtosSelecionados].map(String).sort())),
  );

  return {
    gruposSalvos,
    grupoSelecionado,
    grupo,
    nomeGrupo,
    setNomeGrupo,
    selecionarGrupo,
    salvar,
    provisionar,
    ocupado,
    erroGrupos,
    grupoAlterado,
    configurando,
    setConfigurando,
  };
}
