import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputCheckTexto from "../v2/InputCheckTexto/InputCheckTexto";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputTexto from "../v2/InputTexto/InputTexto";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";

const OPCOES_PRIORIDADE_ALERTA = [
  { value: "aviso", label: "Aviso" },
  { value: "importante", label: "Importante" },
  { value: "info", label: "Info" },
];

export default function ClientePessoaAlertaPdvModal({
  alertaAtual,
  fecharModal,
  salvarAlerta,
  setAlertaAtual,
}) {
  if (!alertaAtual) return null;

  return (
    <ModalPadrao
      titulo={alertaAtual.index !== undefined ? "Editar Alerta" : "Adicionar Alerta"}
      onFechar={fecharModal}
      rodape={
        <>
          <BotaoCancelar onClick={fecharModal}>Cancelar</BotaoCancelar>
          <BotaoSalva onClick={salvarAlerta}>Salvar alerta</BotaoSalva>
        </>
      }
    >
      <div className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-[minmax(0,1fr)_180px]">
          <InputTexto
            id="alerta-titulo"
            label="Tag"
            required
            value={alertaAtual.titulo || ""}
            onChange={(titulo) => setAlertaAtual({ ...alertaAtual, titulo })}
            placeholder="Preço especial"
          />
          <InputCombobox
            id="alerta-prioridade"
            label="Prioridade"
            opcoes={OPCOES_PRIORIDADE_ALERTA}
            permitirLimpar={false}
            value={alertaAtual.prioridade || "aviso"}
            onChange={(prioridade) => setAlertaAtual({ ...alertaAtual, prioridade })}
          />
        </div>

        <InputTextoLongo
          id="alerta-mensagem"
          label="Mensagem"
          linhas={3}
          value={alertaAtual.mensagem || ""}
          onChange={(mensagem) => setAlertaAtual({ ...alertaAtual, mensagem })}
          placeholder="Cliente tem preço especial na ração X: fazer por R$ 120,00"
        />

        <InputCheckTexto
          id="alerta-ativo"
          checked={alertaAtual.ativo !== false}
          onChange={(ativo) => setAlertaAtual({ ...alertaAtual, ativo })}
        >
          <span className="text-sm text-slate-700 dark:text-slate-300">Ativo no PDV</span>
        </InputCheckTexto>

        <p className="text-xs text-gray-500">* Campos obrigatórios</p>
      </div>
    </ModalPadrao>
  );
}
