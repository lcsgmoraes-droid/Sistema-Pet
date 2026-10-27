import { useState } from "react";
import api from "../../platformApi";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputCheckbox from "../../components/v2/InputCheckbox/InputCheckbox";
import InputMoeda from "../../components/v2/InputMoeda/InputMoeda";
import InputQuantidade from "../../components/v2/InputQuantidade/InputQuantidade";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

function useEnvio(onSucesso) {
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const enviar = async (chamada) => {
    setEnviando(true);
    setErro("");
    try {
      await chamada();
      onSucesso();
    } catch (error) {
      setErro(mensagemDeErro(error, "Não foi possível salvar."));
    } finally {
      setEnviando(false);
    }
  };
  return { enviando, erro, enviar };
}

function Erro({ texto }) {
  return texto ? (
    <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
      {texto}
    </p>
  ) : null;
}

// Novo pacote avulso para o catálogo.
export function PacoteModal({ onFechar, onSalvo }) {
  const [nome, setNome] = useState("");
  const [creditos, setCreditos] = useState(0);
  const [preco, setPreco] = useState(0);
  const [tentou, setTentou] = useState(false);
  const { enviando, erro, enviar } = useEnvio(onSalvo);

  const erros = {
    nome: nome.trim().length >= 2 ? "" : "Informe o nome do pacote.",
    creditos: creditos >= 1 ? "" : "Informe a quantidade de créditos.",
    preco: preco > 0 ? "" : "Informe o preço.",
  };

  return (
    <ModalPadrao
      titulo="Novo pacote avulso"
      tamanho="pequena"
      onFechar={onFechar}
      rodape={
        <>
          <BotaoCancelar onClick={onFechar} disabled={enviando} />
          <BotaoSalva type="submit" form="pacote-novo" loading={enviando}>
            Criar pacote
          </BotaoSalva>
        </>
      }
    >
      <form
        id="pacote-novo"
        noValidate
        className="space-y-4"
        onSubmit={(evento) => {
          evento.preventDefault();
          setTentou(true);
          if (Object.values(erros).some(Boolean)) return;
          enviar(() => api.post("/admin/whatsapp-creditos/pacotes", { nome, creditos, preco }));
        }}
      >
        <InputTexto
          id="pacote-nome"
          label="Nome"
          value={nome}
          maxLength={80}
          onChange={setNome}
          error={tentou ? erros.nome : ""}
          required
        />
        <InputQuantidade
          id="pacote-creditos"
          label="Créditos"
          min={0}
          value={creditos}
          onChange={setCreditos}
          error={tentou ? erros.creditos : ""}
          required
        />
        <InputMoeda
          id="pacote-preco"
          label="Preço"
          value={preco}
          onChange={setPreco}
          error={tentou ? erros.preco : ""}
          required
        />
        <Erro texto={erro} />
      </form>
    </ModalPadrao>
  );
}

// Liga o controle de créditos da loja e define a franquia mensal.
export function ControleModal({ loja, onFechar, onSalvo }) {
  const [ativo, setAtivo] = useState(loja.controle_ativo);
  const [franquia, setFranquia] = useState(loja.franquia_mensal);
  const { enviando, erro, enviar } = useEnvio(onSalvo);

  return (
    <ModalPadrao
      titulo={`Controle de créditos · ${loja.loja_nome}`}
      tamanho="pequena"
      onFechar={onFechar}
      rodape={
        <>
          <BotaoCancelar onClick={onFechar} disabled={enviando} />
          <BotaoSalva type="submit" form="controle-loja" loading={enviando}>
            Salvar
          </BotaoSalva>
        </>
      }
    >
      <form
        id="controle-loja"
        noValidate
        className="space-y-4"
        onSubmit={(evento) => {
          evento.preventDefault();
          enviar(() =>
            api.put(`/admin/whatsapp-creditos/lojas/${loja.loja_id}/controle`, {
              ativo,
              franquia_mensal: franquia,
            }),
          );
        }}
      >
        <label className="flex items-center text-sm text-slate-800 dark:text-slate-200">
          <InputCheckbox
            rotulo="Ligar o controle de créditos desta loja"
            checked={ativo}
            onChange={(evento) => setAtivo(evento.target.checked)}
          />
          Ligar o controle de créditos
        </label>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Ligado, a loja só envia enquanto tiver créditos: ao acabar, a IA e os envios param até ela
          comprar um pacote. Desligado, não há limite.
        </p>
        <InputQuantidade
          id="franquia-mensal"
          label="Franquia mensal (créditos que renovam todo mês)"
          min={0}
          value={franquia}
          onChange={setFranquia}
        />
        <Erro texto={erro} />
      </form>
    </ModalPadrao>
  );
}

// Ajuste manual (cortesia ou correção) nos créditos avulsos, sempre com motivo.
export function AjusteModal({ loja, onFechar, onSalvo }) {
  const [quantidade, setQuantidade] = useState(0);
  const [negativo, setNegativo] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [tentou, setTentou] = useState(false);
  const { enviando, erro, enviar } = useEnvio(onSalvo);

  const erros = {
    quantidade: quantidade >= 1 ? "" : "Informe a quantidade.",
    motivo: motivo.trim().length >= 3 ? "" : "Explique o motivo do ajuste.",
  };

  return (
    <ModalPadrao
      titulo={`Ajustar créditos · ${loja.loja_nome}`}
      tamanho="pequena"
      onFechar={onFechar}
      rodape={
        <>
          <BotaoCancelar onClick={onFechar} disabled={enviando} />
          <BotaoSalva type="submit" form="ajuste-loja" loading={enviando}>
            Aplicar ajuste
          </BotaoSalva>
        </>
      }
    >
      <form
        id="ajuste-loja"
        noValidate
        className="space-y-4"
        onSubmit={(evento) => {
          evento.preventDefault();
          setTentou(true);
          if (Object.values(erros).some(Boolean)) return;
          enviar(() =>
            api.post(`/admin/whatsapp-creditos/lojas/${loja.loja_id}/ajuste`, {
              quantidade: negativo ? -quantidade : quantidade,
              descricao: motivo,
            }),
          );
        }}
      >
        <InputQuantidade
          id="ajuste-quantidade"
          label="Quantidade de créditos"
          min={0}
          value={quantidade}
          onChange={setQuantidade}
          error={tentou ? erros.quantidade : ""}
          required
        />
        <label className="flex items-center text-sm text-slate-800 dark:text-slate-200">
          <InputCheckbox
            rotulo="Tirar créditos em vez de dar"
            checked={negativo}
            onChange={(evento) => setNegativo(evento.target.checked)}
          />
          Tirar créditos (correção) em vez de dar
        </label>
        <InputTexto
          id="ajuste-motivo"
          label="Motivo"
          value={motivo}
          maxLength={200}
          onChange={setMotivo}
          error={tentou ? erros.motivo : ""}
          required
        />
        <Erro texto={erro} />
      </form>
    </ModalPadrao>
  );
}
