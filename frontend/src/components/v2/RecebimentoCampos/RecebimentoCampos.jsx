import { useEffect, useId, useMemo, useState } from "react";
import api from "../../../api";
import { safeArray } from "../../../utils/safeArray";
import { obterBandeirasDisponiveis, obterParcelasDisponiveis } from "../../modalPagamentoUtils";
import SeletorFormaRecebimento from "../SeletorFormaRecebimento/SeletorFormaRecebimento";
import CamposCartaoRecebimento from "../CamposCartaoRecebimento/CamposCartaoRecebimento";
import SeletorCaixaRecebimento from "../SeletorCaixaRecebimento/SeletorCaixaRecebimento";
import InputMoeda from "../InputMoeda/InputMoeda";
import InputData from "../InputData/InputData";
import InputTextoLongo from "../InputTextoLongo/InputTextoLongo";
import InputCombobox from "../InputCombobox/InputCombobox";

export default function RecebimentoCampos({
  value,
  onChange,
  onDataChange,
  formas: formasProp,
  disabled = false,
  mostrarValor = true,
  mostrarData = true,
}) {
  const baseId = useId();
  const [formas, setFormas] = useState(formasProp || []);
  const [operadoras, setOperadoras] = useState([]);
  const [taxas, setTaxas] = useState([]);
  const [bancos, setBancos] = useState([]);
  const [erro, setErro] = useState("");
  const atualizar = (patch) => onChange((atual) => ({ ...atual, ...patch }));
  useEffect(() => {
    let ativo = true;
    Promise.allSettled([
      api.get("/financeiro/formas-pagamento", { params: { apenas_ativas: true } }),
      api.get("/operadoras-cartao", { params: { apenas_ativas: true } }),
      api.get("/contas-bancarias", { params: { apenas_ativas: true } }),
    ]).then(([f, o, b]) => {
      if (!ativo) return;
      if (f.status === "fulfilled") setFormas(safeArray(f.value.data));
      else setErro("Não foi possível consultar as formas de recebimento.");
      if (o.status === "fulfilled") setOperadoras(safeArray(o.value.data));
      if (b.status === "fulfilled") setBancos(safeArray(b.value.data));
    });
    return () => {
      ativo = false;
    };
  }, []);
  useEffect(() => {
    let ativo = true;
    setTaxas([]);
    if (value.operadora_id)
      api
        .get(`/operadoras-cartao/${value.operadora_id}/taxas`, { params: { apenas_ativas: true } })
        .then(({ data }) => {
          if (ativo) setTaxas(safeArray(data));
        })
        .catch(() => {
          if (ativo) setErro("Não foi possível consultar as taxas da operadora.");
        });
    return () => {
      ativo = false;
    };
  }, [value.operadora_id]);
  const forma = formas.find((f) => Number(f.id) === Number(value.forma_pagamento_id));
  const cartao = ["cartao_credito", "cartao_debito", "link_pagamento"].includes(forma?.tipo);
  const modalidade = forma?.tipo === "cartao_debito" ? "debito" : "credito";
  const op = operadoras.find((o) => Number(o.id) === Number(value.operadora_id));
  const bandeiras = useMemo(
    () => obterBandeirasDisponiveis({ taxas, modalidade }),
    [taxas, modalidade],
  );
  const parcelas = useMemo(
    () =>
      obterParcelasDisponiveis({
        taxas,
        modalidade,
        bandeira: value.bandeira,
        maxParcelas: Math.min(
          Number(op?.max_parcelas || 12),
          Number(forma?.parcelas_maximas || 12),
        ),
      }),
    [taxas, modalidade, value.bandeira, op, forma],
  );
  return (
    <div className="space-y-4 text-slate-900 dark:text-slate-100">
      {erro && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-400">
          {erro}
        </p>
      )}
      <SeletorCaixaRecebimento
        value={value.caixa_id}
        onChange={(caixa_id) => atualizar({ caixa_id })}
        disabled={disabled}
      />
      <SeletorFormaRecebimento
        formas={formas.filter(
          (f) => !["crediario", "boleto", "cashback", "credito_cliente"].includes(f.tipo),
        )}
        value={value.forma_pagamento_id}
        disabled={disabled}
        onChange={(f) =>
          atualizar({
            forma_pagamento_id: f.id,
            forma_pagamento: f.tipo,
            numero_parcelas: 1,
            bandeira: "",
            nsu_cartao: "",
            conta_bancaria_id: null,
            operadora_id: operadoras.find((o) => o.padrao)?.id || operadoras[0]?.id || null,
          })
        }
      />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {mostrarValor && (
          <InputMoeda
            label="Valor do pagamento"
            value={value.valor_recebido}
            onChange={(valor_recebido) => atualizar({ valor_recebido, quitar: false })}
            disabled={disabled}
            required
          />
        )}
        {mostrarData && (
          <InputData
            label="Data do recebimento"
            value={value.data_recebimento}
            onChange={(data_recebimento) =>
              onDataChange ? onDataChange(data_recebimento) : atualizar({ data_recebimento })
            }
            disabled={disabled}
            required
          />
        )}
      </div>
      {cartao && (
        <CamposCartaoRecebimento
          operadoras={operadoras}
          operadoraId={value.operadora_id}
          onOperadoraChange={(operadora_id) =>
            atualizar({ operadora_id, bandeira: "", numero_parcelas: 1 })
          }
          bandeiras={bandeiras}
          bandeira={value.bandeira}
          onBandeiraChange={(bandeira) => atualizar({ bandeira, numero_parcelas: 1 })}
          nsu={value.nsu_cartao}
          onNsuChange={(nsu_cartao) => atualizar({ nsu_cartao })}
          parcelas={parcelas}
          numeroParcelas={value.numero_parcelas || 1}
          valor={value.valor_recebido || 0}
          onParcelasChange={(numero_parcelas) => atualizar({ numero_parcelas })}
          disabled={disabled}
          permiteParcelamento={forma.tipo !== "cartao_debito"}
        />
      )}
      {!cartao && forma?.tipo !== "dinheiro" && (
        <InputCombobox
          id={`${baseId}-conta-bancaria`}
          label="Conta bancária de destino"
          value={value.conta_bancaria_id}
          opcoes={bancos.map((b) => ({ value: b.id, label: b.nome }))}
          disabled={disabled}
          onChange={(id) => atualizar({ conta_bancaria_id: Number(id) || null })}
        />
      )}
      <InputTextoLongo
        label="Observações"
        value={value.observacoes || ""}
        onChange={(observacoes) => atualizar({ observacoes })}
        disabled={disabled}
        linhas={2}
      />
    </div>
  );
}
