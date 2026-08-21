import { useMemo, useState } from "react";
import CurrencyInput from "../CurrencyInput";

export const BANDEIRAS_TAXA = [
  { codigo: "visa", nome: "Visa" },
  { codigo: "mastercard", nome: "Mastercard" },
  { codigo: "elo", nome: "Elo" },
  { codigo: "amex", nome: "American Express" },
  { codigo: "hipercard", nome: "Hipercard" },
  { codigo: "outros", nome: "Outras bandeiras (fallback)" },
];

const novaTaxa = (bandeira, modalidade, parcelas) => ({
  bandeira,
  modalidade,
  parcelas,
  taxa_percentual: 0,
  taxa_fixa: 0,
  prazo_recebimento_dias: modalidade === "debito" ? 1 : 30,
});

const chaveTaxa = (taxa) => `${taxa.bandeira}:${taxa.modalidade}:${taxa.parcelas}`;

export default function OperadoraCartaoTaxasEditor({ formData, setFormData, taxas, setTaxas }) {
  const [bandeirasSelecionadas, setBandeirasSelecionadas] = useState(["visa", "mastercard"]);
  const [modalidade, setModalidade] = useState("credito");
  const maxParcelas = modalidade === "debito" ? 1 : Math.max(1, formData.max_parcelas || 1);
  const parcelas = useMemo(
    () => Array.from({ length: maxParcelas }, (_, index) => index + 1),
    [maxParcelas],
  );

  const alternarBandeira = (codigo) => {
    setBandeirasSelecionadas((atuais) => {
      if (atuais.includes(codigo)) {
        return atuais.length === 1 ? atuais : atuais.filter((item) => item !== codigo);
      }
      return [...atuais, codigo];
    });
  };

  const regrasDaParcela = (numero) =>
    bandeirasSelecionadas.map((bandeira) =>
      taxas.find(
        (taxa) =>
          taxa.bandeira === bandeira &&
          taxa.modalidade === modalidade &&
          Number(taxa.parcelas) === numero,
      ),
    );

  const aplicarNasBandeiras = (numero, atualizacao, configurar = true) => {
    setTaxas((atuais) => {
      const mapa = new Map(atuais.map((taxa) => [chaveTaxa(taxa), { ...taxa }]));
      bandeirasSelecionadas.forEach((bandeira) => {
        const key = `${bandeira}:${modalidade}:${numero}`;
        if (!configurar) {
          mapa.delete(key);
          return;
        }
        mapa.set(key, {
          ...(mapa.get(key) || novaTaxa(bandeira, modalidade, numero)),
          ...atualizacao,
          bandeira,
          modalidade,
          parcelas: numero,
        });
      });
      return [...mapa.values()].sort((a, b) => chaveTaxa(a).localeCompare(chaveTaxa(b)));
    });
  };

  return (
    <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50/50 p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Tabela de taxas</h3>
        <p className="mt-1 text-sm text-gray-600">
          Selecione uma ou mais bandeiras. Alterar um valor aplica a mesma taxa a todas as
          selecionadas.
        </p>
      </div>

      <div className="mb-4">
        <span className="mb-2 block text-sm font-medium text-gray-700">Bandeiras</span>
        <div className="flex flex-wrap gap-2">
          {BANDEIRAS_TAXA.map((item) => {
            const selecionada = bandeirasSelecionadas.includes(item.codigo);
            return (
              <button
                key={item.codigo}
                type="button"
                onClick={() => alternarBandeira(item.codigo)}
                className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
                  selecionada
                    ? "border-blue-600 bg-blue-600 text-white"
                    : "border-gray-300 bg-white text-gray-700 hover:border-blue-400"
                }`}
              >
                {item.nome}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mb-4 grid gap-4 md:grid-cols-2">
        <div>
          <span className="mb-2 block text-sm font-medium text-gray-700">Modalidade</span>
          <div className="flex gap-2">
            {[
              ["credito", "Credito"],
              ["debito", "Debito"],
            ].map(([codigo, nome]) => (
              <button
                key={codigo}
                type="button"
                onClick={() => setModalidade(codigo)}
                className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium ${
                  modalidade === codigo
                    ? "border-emerald-600 bg-emerald-600 text-white"
                    : "border-gray-300 bg-white text-gray-700"
                }`}
              >
                {nome}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700">
            Bandeira padrao no PDV (opcional)
          </label>
          <select
            value={formData.bandeira_padrao || ""}
            onChange={(event) =>
              setFormData({ ...formData, bandeira_padrao: event.target.value || null })
            }
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2"
          >
            <option value="">Pedir a bandeira em cada venda</option>
            {BANDEIRAS_TAXA.filter((item) => item.codigo !== "outros").map((item) => (
              <option key={item.codigo} value={item.codigo}>
                {item.nome}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-500">
            Se houver duvida, deixe sem padrao para nao registrar a bandeira errada.
          </p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left">Parcelas</th>
              <th className="px-3 py-2 text-left">Configurada</th>
              <th className="px-3 py-2 text-left">Taxa %</th>
              <th className="px-3 py-2 text-left">Taxa fixa</th>
              <th className="px-3 py-2 text-left">Receber em</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {parcelas.map((numero) => {
              const regras = regrasDaParcela(numero);
              const configuradas = regras.filter(Boolean);
              const todasConfiguradas = configuradas.length === bandeirasSelecionadas.length;
              const primeira = configuradas[0] || novaTaxa("", modalidade, numero);
              const valoresDiferentes = configuradas.some(
                (regra) =>
                  Number(regra.taxa_percentual) !== Number(primeira.taxa_percentual) ||
                  Number(regra.taxa_fixa) !== Number(primeira.taxa_fixa) ||
                  Number(regra.prazo_recebimento_dias) !== Number(primeira.prazo_recebimento_dias),
              );
              return (
                <tr key={numero}>
                  <td className="whitespace-nowrap px-3 py-2 font-semibold">{numero}x</td>
                  <td className="px-3 py-2">
                    <label className="flex items-center gap-2 whitespace-nowrap">
                      <input
                        type="checkbox"
                        checked={todasConfiguradas}
                        onChange={(event) => aplicarNasBandeiras(numero, {}, event.target.checked)}
                      />
                      {configuradas.length > 0 && !todasConfiguradas
                        ? `${configuradas.length}/${bandeirasSelecionadas.length}`
                        : todasConfiguradas
                          ? "Sim"
                          : "Nao"}
                    </label>
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.0001"
                      disabled={!configuradas.length}
                      value={valoresDiferentes ? "" : primeira.taxa_percentual}
                      placeholder={valoresDiferentes ? "Diferentes" : "0"}
                      onChange={(event) =>
                        aplicarNasBandeiras(numero, {
                          taxa_percentual: Number(event.target.value || 0),
                        })
                      }
                      className="w-28 rounded border border-gray-300 px-2 py-1.5 disabled:bg-gray-100"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <CurrencyInput
                      value={valoresDiferentes ? 0 : primeira.taxa_fixa}
                      disabled={!configuradas.length}
                      onChange={(value) =>
                        aplicarNasBandeiras(numero, { taxa_fixa: Number(value || 0) })
                      }
                      className="w-28 rounded border border-gray-300 px-2 py-1.5 disabled:bg-gray-100"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min="0"
                        max="365"
                        disabled={!configuradas.length}
                        value={valoresDiferentes ? "" : primeira.prazo_recebimento_dias}
                        placeholder={valoresDiferentes ? "-" : "0"}
                        onChange={(event) =>
                          aplicarNasBandeiras(numero, {
                            prazo_recebimento_dias: Number(event.target.value || 0),
                          })
                        }
                        className="w-20 rounded border border-gray-300 px-2 py-1.5 disabled:bg-gray-100"
                      />
                      <span className="text-gray-500">dias</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
