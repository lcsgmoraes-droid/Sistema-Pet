import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputQuantidade from "../../components/v2/InputQuantidade/InputQuantidade";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
import { MAXIMO_DE_COLUNAS, ROTULO_TIPO_DE_COLUNA, TIPOS_FINAIS, validarColunas } from "./crmUtils";

const OPCOES_DE_TIPO = Object.entries(ROTULO_TIPO_DE_COLUNA).map(([value, label]) => ({
  value,
  label,
}));

let contador = 0;
const novaChave = () => `nova-${(contador += 1)}`;

// Configuração das colunas do funil de UMA loja (nome, ordem, tipo e janela de dias).
export default function CrmColunasModal({ loja, onFechar, onSalvo }) {
  const [colunas, setColunas] = useState(() =>
    loja.colunas.map((coluna) => ({
      chave: String(coluna.id),
      id: coluna.id,
      nome: coluna.nome,
      tipo: coluna.tipo,
      janela_dias: coluna.janela_dias || null,
    })),
  );
  const [tentou, setTentou] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erroGeral, setErroGeral] = useState("");

  const problema = validarColunas(colunas);

  const alterar = (chave, campo, valor) =>
    setColunas((atual) =>
      atual.map((coluna) => (coluna.chave === chave ? { ...coluna, [campo]: valor } : coluna)),
    );
  const mover = (indice, delta) =>
    setColunas((atual) => {
      const destino = indice + delta;
      if (destino < 0 || destino >= atual.length) return atual;
      const copia = [...atual];
      [copia[indice], copia[destino]] = [copia[destino], copia[indice]];
      return copia;
    });
  const remover = (chave) =>
    setColunas((atual) => atual.filter((coluna) => coluna.chave !== chave));
  const adicionar = () =>
    setColunas((atual) => [
      ...atual,
      { chave: novaChave(), id: null, nome: "", tipo: "andamento", janela_dias: null },
    ]);

  const salvar = async (evento) => {
    evento.preventDefault();
    setTentou(true);
    setErroGeral("");
    if (problema) return;
    setEnviando(true);
    try {
      await api.put("/crm/funil/colunas", {
        loja_id: loja.loja_id,
        colunas: colunas.map(({ id, nome, tipo, janela_dias }) => ({
          id,
          nome: nome.trim(),
          tipo,
          janela_dias: TIPOS_FINAIS.includes(tipo) ? janela_dias : null,
        })),
      });
      toast.success("Colunas salvas.");
      onSalvo();
    } catch (error) {
      const detalhe = error?.response?.data?.detail;
      setErroGeral(typeof detalhe === "string" ? detalhe : "Não foi possível salvar as colunas.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <ModalPadrao
      titulo={`Colunas do funil · ${loja.loja_nome}`}
      tamanho="grande"
      onFechar={onFechar}
      rodape={
        <>
          <BotaoCancelar onClick={onFechar} disabled={enviando} />
          <BotaoSalva type="submit" form="crm-colunas" loading={enviando}>
            Salvar colunas
          </BotaoSalva>
        </>
      }
    >
      <form id="crm-colunas" noValidate onSubmit={salvar} className="space-y-4">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Use de 2 a {MAXIMO_DE_COLUNAS} colunas, com pelo menos uma de entrada e uma de concluído.
          Uma coluna só pode ser removida quando não tiver cards.
        </p>

        <ol className="space-y-3">
          {colunas.map((coluna, indice) => (
            <li
              key={coluna.chave}
              className="grid gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700 sm:grid-cols-[1fr_12rem_8rem_auto]"
            >
              <InputTexto
                id={`crm-coluna-nome-${coluna.chave}`}
                label={`Coluna ${indice + 1}`}
                value={coluna.nome}
                maxLength={60}
                onChange={(valor) => alterar(coluna.chave, "nome", valor)}
                error={tentou && !coluna.nome.trim() ? "Informe o nome." : ""}
                required
              />
              <InputCombobox
                id={`crm-coluna-tipo-${coluna.chave}`}
                label="Tipo"
                value={coluna.tipo}
                opcoes={OPCOES_DE_TIPO}
                onChange={(valor) => alterar(coluna.chave, "tipo", valor)}
              />
              {TIPOS_FINAIS.includes(coluna.tipo) ? (
                <InputQuantidade
                  id={`crm-coluna-janela-${coluna.chave}`}
                  label="Mostrar últimos (dias)"
                  value={coluna.janela_dias || 0}
                  min={0}
                  onChange={(valor) =>
                    alterar(coluna.chave, "janela_dias", valor > 0 ? valor : null)
                  }
                  help="0 mostra tudo"
                />
              ) : (
                <span />
              )}
              <div className="flex items-end gap-1">
                <BotaoInteracao
                  icon={ArrowUp}
                  aria-label={`Subir ${coluna.nome || "coluna"}`}
                  disabled={indice === 0}
                  onClick={() => mover(indice, -1)}
                />
                <BotaoInteracao
                  icon={ArrowDown}
                  aria-label={`Descer ${coluna.nome || "coluna"}`}
                  disabled={indice === colunas.length - 1}
                  onClick={() => mover(indice, 1)}
                />
                <BotaoInteracao
                  icon={Trash2}
                  aria-label={`Remover ${coluna.nome || "coluna"}`}
                  onClick={() => remover(coluna.chave)}
                />
              </div>
            </li>
          ))}
        </ol>

        <BotaoInteracao
          icon={Plus}
          onClick={adicionar}
          disabled={colunas.length >= MAXIMO_DE_COLUNAS}
        >
          Adicionar coluna
        </BotaoInteracao>

        {tentou && problema ? (
          <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
            {problema}
          </p>
        ) : null}
        {erroGeral ? (
          <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
            {erroGeral}
          </p>
        ) : null}
      </form>
    </ModalPadrao>
  );
}
