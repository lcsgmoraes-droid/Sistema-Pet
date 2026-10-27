import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
import ComissaoSelectedItemPanel from "./ComissaoSelectedItemPanel";
import { buildSelectedItemPayload, createSelectedCommissionItem } from "./comissoesUtils";
import { DEFAULT_COMMISSION_RULES } from "./comissoesConstants";
import { confirmarCorePet } from "../../services/corepetDialog";

export default function ComissaoGrupoConfiguracaoModal({ grupo, onClose }) {
  const [parceiros, setParceiros] = useState([]);
  const [parceiro, setParceiro] = useState("");
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [item, setItem] = useState(() => createSelectedCommissionItem("produto", 0, grupo.nome));
  useEffect(() => {
    let ativo = true;
    api
      .get("/comissoes/configuracoes/funcionarios")
      .then(({ data }) => {
        if (ativo) setParceiros(data.data || []);
      })
      .catch(() => {
        if (ativo) setErro("Não foi possível carregar os parceiros.");
      })
      .finally(() => {
        if (ativo) setLoading(false);
      });
    return () => {
      ativo = false;
    };
  }, []);

  const salvar = async () => {
    if (!parceiro || salvando) {
      toast.error("Selecione um parceiro.");
      return;
    }
    if (
      !(await confirmarCorePet(
        `Aplicar esta regra aos ${grupo.produto_ids.length} produtos do grupo para o parceiro selecionado? Regras anteriores desses produtos serão substituídas. Comissões de vendas anteriores permanecem como foram calculadas.`,
      ))
    )
      return;
    setSalvando(true);
    try {
      await api.post("/comissoes/configuracoes/batch", {
        configuracoes: grupo.produto_ids.map((id) =>
          buildSelectedItemPayload({ ...item, id }, parceiro, DEFAULT_COMMISSION_RULES),
        ),
      });
      toast.success("Comissão do grupo configurada para as próximas vendas.");
      onClose();
    } catch (error) {
      setErro(
        typeof error.response?.data?.detail === "string"
          ? error.response.data.detail
          : "Confira o valor da comissão e tente novamente.",
      );
    } finally {
      setSalvando(false);
    }
  };

  return (
    <ModalPadrao
      aberto
      onFechar={onClose}
      titulo={`Comissão do grupo: ${grupo.nome}`}
      tamanho="grande"
    >
      {loading ? (
        <p>Carregando parceiros...</p>
      ) : (
        <div className="space-y-4">
          <InputCombobox
            id="comissao-grupo-parceiro"
            label="Parceiro comissionado"
            value={parceiro}
            onChange={setParceiro}
            disabled={salvando}
            opcoes={parceiros.map((pessoa) => ({ value: String(pessoa.id), label: pessoa.nome }))}
          />
          {erro && (
            <p role="alert" className="text-sm text-red-600 dark:text-red-400">
              {erro}
            </p>
          )}
          <ComissaoSelectedItemPanel
            itemSelecionado={item}
            setItemSelecionado={setItem}
            salvarItem={salvar}
            ocultarAdicionar
            salvando={salvando}
          />
        </div>
      )}
    </ModalPadrao>
  );
}
