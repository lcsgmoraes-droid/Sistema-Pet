import { useState } from "react";
import { enviar, substituir } from "../api/cliente";
import { Aviso, Campo } from "../components/ui";
import { CaixaDeMarcar, Janela } from "../components/formulario";
import { lerNumero } from "../lib/whatsapp";

function useEnvio(aoSucesso) {
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const executar = async (chamada) => {
    setEnviando(true);
    setErro("");
    try {
      await chamada();
      aoSucesso();
    } catch (falha) {
      setErro(falha.message || "Não foi possível salvar.");
    } finally {
      setEnviando(false);
    }
  };
  return { enviando, erro, executar };
}

// Novo pacote avulso para o catálogo.
export function PacoteModal({ aoFechar, aoSalvo }) {
  const [nome, setNome] = useState("");
  const [creditos, setCreditos] = useState("");
  const [preco, setPreco] = useState("");
  const [tentou, setTentou] = useState(false);
  const { enviando, erro, executar } = useEnvio(aoSalvo);

  const erros = {
    nome: nome.trim().length >= 2 ? "" : "Informe o nome do pacote.",
    creditos: lerNumero(creditos) >= 1 ? "" : "Informe a quantidade de créditos.",
    preco: lerNumero(preco) > 0 ? "" : "Informe o preço.",
  };

  return (
    <Janela
      titulo="Novo pacote avulso"
      formId="pacote-novo"
      rotuloSalvar="Criar pacote"
      enviando={enviando}
      aoFechar={aoFechar}
      aoSalvar={() => {
        setTentou(true);
        if (Object.values(erros).some(Boolean)) return;
        executar(() =>
          enviar("/admin/whatsapp-creditos/pacotes", {
            nome,
            creditos: Math.floor(lerNumero(creditos)),
            preco: lerNumero(preco),
          }),
        );
      }}
    >
      <Campo
        rotulo="Nome"
        maxLength={80}
        value={nome}
        onChange={(e) => setNome(e.target.value)}
        erro={tentou ? erros.nome : ""}
      />
      <Campo
        rotulo="Créditos"
        inputMode="numeric"
        value={creditos}
        onChange={(e) => setCreditos(e.target.value)}
        erro={tentou ? erros.creditos : ""}
      />
      <Campo
        rotulo="Preço (R$)"
        inputMode="decimal"
        value={preco}
        onChange={(e) => setPreco(e.target.value)}
        erro={tentou ? erros.preco : ""}
      />
      {erro ? <Aviso tom="erro">{erro}</Aviso> : null}
    </Janela>
  );
}

// Liga o controle de créditos da loja e define a franquia mensal.
export function ControleModal({ loja, aoFechar, aoSalvo }) {
  const [ativo, setAtivo] = useState(loja.controle_ativo);
  const [franquia, setFranquia] = useState(String(loja.franquia_mensal ?? 0));
  const { enviando, erro, executar } = useEnvio(aoSalvo);

  return (
    <Janela
      titulo={`Controle de créditos · ${loja.loja_nome}`}
      formId="controle-loja"
      enviando={enviando}
      aoFechar={aoFechar}
      aoSalvar={() =>
        executar(() =>
          substituir(`/admin/whatsapp-creditos/lojas/${loja.loja_id}/controle`, {
            ativo,
            franquia_mensal: Math.floor(lerNumero(franquia)),
          }),
        )
      }
    >
      <CaixaDeMarcar checked={ativo} onChange={(e) => setAtivo(e.target.checked)}>
        Ligar o controle de créditos desta loja
      </CaixaDeMarcar>
      <p className="text-xs text-slate-600 dark:text-slate-400">
        Ligado, a loja só envia enquanto tiver créditos: ao acabar, a IA e os envios param até ela comprar um pacote.
        Desligado, não há limite.
      </p>
      <Campo
        rotulo="Franquia mensal (créditos que renovam todo mês)"
        inputMode="numeric"
        value={franquia}
        onChange={(e) => setFranquia(e.target.value)}
      />
      {erro ? <Aviso tom="erro">{erro}</Aviso> : null}
    </Janela>
  );
}

// Ajuste manual (cortesia ou correção) nos créditos avulsos, sempre com motivo.
export function AjusteModal({ loja, aoFechar, aoSalvo }) {
  const [quantidade, setQuantidade] = useState("");
  const [negativo, setNegativo] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [tentou, setTentou] = useState(false);
  const { enviando, erro, executar } = useEnvio(aoSalvo);

  const erros = {
    quantidade: lerNumero(quantidade) >= 1 ? "" : "Informe a quantidade.",
    motivo: motivo.trim().length >= 3 ? "" : "Explique o motivo do ajuste.",
  };

  return (
    <Janela
      titulo={`Ajustar créditos · ${loja.loja_nome}`}
      formId="ajuste-loja"
      rotuloSalvar="Aplicar ajuste"
      enviando={enviando}
      aoFechar={aoFechar}
      aoSalvar={() => {
        setTentou(true);
        if (Object.values(erros).some(Boolean)) return;
        const valor = Math.floor(lerNumero(quantidade));
        executar(() =>
          enviar(`/admin/whatsapp-creditos/lojas/${loja.loja_id}/ajuste`, {
            quantidade: negativo ? -valor : valor,
            descricao: motivo,
          }),
        );
      }}
    >
      <Campo
        rotulo="Quantidade de créditos"
        inputMode="numeric"
        value={quantidade}
        onChange={(e) => setQuantidade(e.target.value)}
        erro={tentou ? erros.quantidade : ""}
      />
      <CaixaDeMarcar checked={negativo} onChange={(e) => setNegativo(e.target.checked)}>
        Tirar créditos (correção) em vez de dar
      </CaixaDeMarcar>
      <Campo
        rotulo="Motivo"
        maxLength={200}
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
        erro={tentou ? erros.motivo : ""}
      />
      {erro ? <Aviso tom="erro">{erro}</Aviso> : null}
    </Janela>
  );
}
