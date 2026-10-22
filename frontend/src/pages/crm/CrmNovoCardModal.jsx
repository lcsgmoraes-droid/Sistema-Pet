import { useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputMoeda from "../../components/v2/InputMoeda/InputMoeda";
import InputTelefone from "../../components/v2/InputTelefone/InputTelefone";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";

function apenasDigitos(texto) {
  return String(texto || "").replace(/\D/g, "");
}

// Criação manual de um card para um contato sem cadastro. Vincular a uma pessoa já cadastrada
// entra junto da busca de tutor (ROADMAP 2.6).
export default function CrmNovoCardModal({ lojas, lojaInicial, onCriado, onFechar }) {
  const [lojaId, setLojaId] = useState(lojaInicial || lojas[0]?.id || "");
  const [nome, setNome] = useState("");
  const [telefone, setTelefone] = useState("");
  const [valor, setValor] = useState(0);
  const [tentou, setTentou] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erroGeral, setErroGeral] = useState("");

  const erros = {
    nome: nome.trim() ? "" : "Informe o nome do contato.",
    telefone: apenasDigitos(telefone).length >= 10 ? "" : "Informe o telefone com DDD.",
  };
  const valido = !erros.nome && !erros.telefone;

  const salvar = async (evento) => {
    evento.preventDefault();
    setTentou(true);
    setErroGeral("");
    if (!valido) return;
    setEnviando(true);
    try {
      await api.post("/crm/leads", {
        loja_id: lojaId || null,
        nome: nome.trim(),
        telefone: apenasDigitos(telefone),
        valor_estimado: valor > 0 ? valor : null,
      });
      toast.success("Card criado.");
      onCriado();
    } catch (error) {
      const detalhe = error?.response?.data?.detail;
      setErroGeral(typeof detalhe === "string" ? detalhe : "Não foi possível criar o card.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <ModalPadrao
      titulo="Novo card"
      tamanho="pequena"
      onFechar={onFechar}
      rodape={
        <>
          <BotaoCancelar onClick={onFechar} disabled={enviando} />
          <BotaoSalva type="submit" form="crm-novo-card" loading={enviando}>
            Criar card
          </BotaoSalva>
        </>
      }
    >
      <form id="crm-novo-card" noValidate onSubmit={salvar} className="space-y-4">
        {lojas.length > 1 ? (
          <InputCombobox
            id="crm-novo-loja"
            label="Loja"
            value={lojaId}
            opcoes={lojas.map((loja) => ({ value: loja.id, label: loja.nome }))}
            onChange={setLojaId}
            required
          />
        ) : null}
        <InputTexto
          id="crm-novo-nome"
          label="Nome do contato"
          value={nome}
          maxLength={200}
          onChange={setNome}
          error={tentou ? erros.nome : ""}
          autoFocus
          required
        />
        <InputTelefone
          id="crm-novo-telefone"
          label="Telefone (WhatsApp)"
          tipo="celular"
          value={telefone}
          onChange={setTelefone}
          error={tentou ? erros.telefone : ""}
          required
        />
        <InputMoeda
          id="crm-novo-valor"
          label="Valor estimado (opcional)"
          value={valor}
          onChange={setValor}
        />
        {erroGeral ? (
          <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
            {erroGeral}
          </p>
        ) : null}
      </form>
    </ModalPadrao>
  );
}
