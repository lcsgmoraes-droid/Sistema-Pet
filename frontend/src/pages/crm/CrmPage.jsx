import { Plus, SearchX } from "lucide-react";
import { useState } from "react";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import InputComboboxMultiplo from "../../components/v2/InputComboboxMultiplo/InputComboboxMultiplo";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import CrmConcluirModal from "./CrmConcluirModal";
import CrmFichaModal from "./CrmFichaModal";
import CrmNovoCardModal from "./CrmNovoCardModal";
import CrmQuadro from "./CrmQuadro";
import useCrmQuadro from "./useCrmQuadro";

function Esqueleto() {
  return (
    <div className="flex gap-3 overflow-hidden" role="status" aria-label="Carregando o quadro">
      {[0, 1, 2, 3].map((item) => (
        <div
          key={item}
          className="h-64 w-72 flex-none animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900"
        />
      ))}
    </div>
  );
}

export default function CrmPage() {
  const crm = useCrmQuadro();
  const [novoCard, setNovoCard] = useState(false);
  const [fichaDoCard, setFichaDoCard] = useState(null);
  const semCards = crm.colunas.every((coluna) => coluna.total === 0);

  return (
    <div className="mx-auto w-full max-w-[1600px] p-4 sm:p-6">
      <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="m-0 text-xs font-bold uppercase tracking-[0.18em] text-teal-700 dark:text-teal-300">
            Relacionamento
          </p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100 sm:text-3xl">
            CRM
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600 dark:text-slate-400">
            Acompanhe seus tutores e oportunidades. Arraste os cards entre as colunas.
          </p>
        </div>
        <BotaoInteracao icon={Plus} onClick={() => setNovoCard(true)}>
          Novo card
        </BotaoInteracao>
      </header>

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <InputTexto
          id="crm-busca"
          label="Buscar"
          placeholder="Nome do contato"
          value={crm.busca}
          onChange={crm.setBusca}
        />
        {crm.lojasDisponiveis.length > 1 ? (
          <InputComboboxMultiplo
            id="crm-lojas"
            label="Lojas"
            placeholder="Todas as minhas lojas"
            value={crm.idsValidos}
            opcoes={crm.lojasDisponiveis.map((loja) => ({ value: loja.id, label: loja.nome }))}
            onChange={crm.escolherLojas}
          />
        ) : null}
      </div>

      {crm.erro ? (
        <p role="alert" className="mb-3 text-sm font-medium text-red-700 dark:text-red-300">
          {crm.erro}
        </p>
      ) : null}

      {crm.carregando ? (
        <Esqueleto />
      ) : (
        <>
          {semCards && crm.busca.trim() ? (
            <EstadoVazio
              icone={SearchX}
              titulo="Nenhum card encontrado"
              descricao="Tente outro nome ou limpe a busca."
            />
          ) : (
            <div aria-busy={crm.atualizando}>
              {semCards ? (
                <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">
                  Ainda não há cards. Crie o primeiro em “Novo card”; contatos novos de WhatsApp
                  também entram sozinhos na primeira coluna.
                </p>
              ) : null}
              <CrmQuadro
                colunas={crm.colunas}
                movendoId={crm.movendoId}
                multiLoja={crm.multiLoja}
                onAbrir={setFichaDoCard}
                onMover={crm.moverCard}
              />
            </div>
          )}
        </>
      )}

      {novoCard ? (
        <CrmNovoCardModal
          lojas={crm.lojasDisponiveis}
          lojaInicial={crm.idsValidos[0]}
          onFechar={() => setNovoCard(false)}
          onCriado={() => {
            setNovoCard(false);
            crm.recarregar();
          }}
        />
      ) : null}

      {fichaDoCard ? (
        <CrmFichaModal
          card={fichaDoCard}
          onAlterado={crm.recarregar}
          onFechar={() => setFichaDoCard(null)}
        />
      ) : null}

      {crm.pendencia ? (
        <CrmConcluirModal
          pendencia={crm.pendencia}
          onCancelar={crm.cancelarPendencia}
          onConfirmar={crm.confirmarPendencia}
        />
      ) : null}
    </div>
  );
}
