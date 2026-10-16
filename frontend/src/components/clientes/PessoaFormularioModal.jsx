import { useState } from "react";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";
import PessoaFormulario from "./PessoaFormulario";

const FORM_ID = "pessoa-formulario-modal";

// A ÚNICA modal de cadastro/edição rápida de Pessoa do sistema — nunca criar uma modal
// própria por processo (PDV, fornecedor, etc.): todos os pontos de entrada chamam esta,
// com `prefill` pra já vir com o tipo de cadastro certo marcado quando fizer sentido.
export default function PessoaFormularioModal({ onFechar, onSalvo, prefill, pessoa }) {
  const [salvando, setSalvando] = useState(false);

  return (
    <ModalPadrao
      titulo={pessoa ? "Editar pessoa" : "Nova pessoa"}
      tamanho="grande"
      onFechar={onFechar}
      rodape={
        <>
          <BotaoCancelar onClick={onFechar}>Cancelar</BotaoCancelar>
          <BotaoSalva form={FORM_ID} loading={salvando}>
            {pessoa ? "Salvar" : "Criar cadastro"}
          </BotaoSalva>
        </>
      }
    >
      <PessoaFormulario
        formId={FORM_ID}
        onSalvandoChange={setSalvando}
        onSalvo={onSalvo}
        prefill={prefill}
        pessoa={pessoa}
      />
    </ModalPadrao>
  );
}
