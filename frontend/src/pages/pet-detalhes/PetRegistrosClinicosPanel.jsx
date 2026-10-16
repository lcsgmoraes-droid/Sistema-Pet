import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import BotaoExcluir from "../../components/v2/BotaoExcluir/BotaoExcluir";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputQuantidade from "../../components/v2/InputQuantidade/InputQuantidade";
import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";
import EstadoVazio from "../../components/ui/EmptyState";
import { formatarDataHora } from "./petDetalhesUtils";

// Mesma paleta/estilo já usado nos outros gráficos do sistema (ver
// GraficoProjecoes.jsx) — reaproveitado aqui por consistência visual.
const COR_LINHA = "#3b82f6";
const COR_GRADE = "#e5e7eb";
const COR_EIXO = "#6b7280";

function formatarDataCurta(valor) {
  if (!valor) return "-";
  return new Date(valor).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

function TooltipPeso({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const dado = payload[0].payload;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-lg">
      <p className="text-sm font-medium text-gray-900">{formatarDataHora(dado.registrado_em)}</p>
      <p className="text-sm text-blue-600">
        <strong>{dado.valor} kg</strong>
      </p>
      <p className="text-xs text-gray-500">{dado.loja_nome || "Loja"}</p>
    </div>
  );
}

function GraficoPeso({ registros }) {
  if (registros.length === 0) return null;

  const dados = [...registros]
    .sort((a, b) => new Date(a.registrado_em) - new Date(b.registrado_em))
    .map((registro) => ({ ...registro, data_curta: formatarDataCurta(registro.registrado_em) }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={dados} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COR_GRADE} />
        <XAxis dataKey="data_curta" stroke={COR_EIXO} style={{ fontSize: "12px" }} />
        <YAxis
          stroke={COR_EIXO}
          style={{ fontSize: "12px" }}
          width={48}
          tickFormatter={(valor) => `${valor}kg`}
        />
        <Tooltip content={<TooltipPeso />} />
        <Line
          type="monotone"
          dataKey="valor"
          stroke={COR_LINHA}
          strokeWidth={3}
          dot={{ r: 4, fill: COR_LINHA }}
          name="Peso"
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function ListaRegistros({ registros, renderValor, onExcluir, empty }) {
  if (registros.length === 0) {
    return <p className="py-4 text-center text-sm text-gray-500">{empty}</p>;
  }
  return (
    <ul className="divide-y divide-gray-100">
      {registros.map((registro) => (
        <li key={registro.id} className="flex items-start justify-between gap-3 py-3">
          <div className="min-w-0 flex-1">
            {renderValor(registro)}
            <p className="mt-0.5 text-xs text-gray-500">
              {formatarDataHora(registro.registrado_em)} · {registro.loja_nome || "Loja"}
            </p>
          </div>
          {registro.pode_editar ? (
            <BotaoExcluir
              tamanho="pequeno"
              aria-label="Excluir registro"
              mensagemConfirmacao="Excluir este registro? Essa ação não pode ser desfeita."
              onClick={() => onExcluir(registro.id)}
            >
              {""}
            </BotaoExcluir>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

export default function PetRegistrosClinicosPanel({
  registrosPeso,
  registrosHistorico,
  loading,
  salvando,
  onAdicionarPeso,
  onAdicionarHistorico,
  onExcluirRegistro,
}) {
  const [novoPeso, setNovoPeso] = useState(null);
  const [novoHistorico, setNovoHistorico] = useState("");

  const salvarPeso = async () => {
    if (!novoPeso) return;
    await onAdicionarPeso(novoPeso);
    setNovoPeso(null);
  };

  const salvarHistorico = async () => {
    if (!novoHistorico.trim()) return;
    await onAdicionarHistorico(novoHistorico.trim());
    setNovoHistorico("");
  };

  if (loading) {
    return <p className="py-6 text-center text-sm text-gray-500">Carregando registros...</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 text-sm font-semibold text-gray-900">
          Peso — todas as lojas do grupo registram e leem; cada uma só apaga o que registrou
        </h3>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          {registrosPeso.length > 0 ? (
            <GraficoPeso registros={registrosPeso} />
          ) : (
            <EstadoVazio
              title="Sem pesagens registradas"
              description="Registre a primeira pesagem abaixo."
            />
          )}
          <div className="mt-4 flex items-end gap-3">
            <div className="w-32">
              <InputQuantidade
                id="novo-peso-pet"
                label="Novo peso (kg)"
                value={novoPeso}
                onChange={setNovoPeso}
              />
            </div>
            <BotaoSalva
              tamanho="normal"
              loading={salvando}
              disabled={!novoPeso}
              onClick={salvarPeso}
            >
              Registrar peso
            </BotaoSalva>
          </div>
          <ListaRegistros
            registros={registrosPeso}
            renderValor={(r) => <p className="text-sm text-gray-900">{r.valor} kg</p>}
            onExcluir={onExcluirRegistro}
            empty="Nenhuma pesagem registrada"
          />
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold text-gray-900">
          Histórico clínico — todas as lojas do grupo leem; cada uma só apaga o que registrou
        </h3>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <ListaRegistros
            registros={registrosHistorico}
            renderValor={(r) => (
              <p className="whitespace-pre-line text-sm text-gray-900">{r.texto}</p>
            )}
            onExcluir={onExcluirRegistro}
            empty="Nenhum histórico clínico registrado"
          />
          <div className="mt-4 space-y-2">
            <InputTextoLongo
              id="novo-historico-pet"
              label="Nova anotação"
              linhas={3}
              value={novoHistorico}
              onChange={setNovoHistorico}
            />
            <BotaoSalva
              tamanho="normal"
              loading={salvando}
              disabled={!novoHistorico.trim()}
              onClick={salvarHistorico}
            >
              Registrar anotação
            </BotaoSalva>
          </div>
        </div>
      </div>
    </div>
  );
}
