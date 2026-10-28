import { useEffect, useRef, useState } from "react";
import { Pencil, Search } from "lucide-react";
import { api } from "../../../services/api";
import BotaoCancelar from "../../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../../../components/v2/BotaoSalva/BotaoSalva";
import InputCheck from "../../../components/v2/InputCheck/InputCheck";
import InputCombobox from "../../../components/v2/InputCombobox/InputCombobox";
import InputTexto from "../../../components/v2/InputTexto/InputTexto";
import ModalPadrao from "../../../components/v2/ModalPadrao/ModalPadrao";
import { fiscalError, FISCAL_BASE } from "./amazonFiscalUtils";

const emptyMapping = () => ({ seller_sku: "", product_id: "", active: true });

export default function AmazonFiscalMappings({ account, onClose, onChanged }) {
  const [mappings, setMappings] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(emptyMapping);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const operation = useRef(false);
  const searchRequest = useRef(0);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      searchRequest.current += 1;
    };
  }, []);
  useEffect(() => {
    let active = true;
    api
      .get(`${FISCAL_BASE}/mappings`, { params: { account_id: account.id } })
      .then(({ data }) => {
        if (active) setMappings(data.items || []);
      })
      .catch(async (failure) => {
        const text = await fiscalError(failure);
        if (active) setError(text);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [account.id, version]);

  async function search() {
    const request = ++searchRequest.current;
    setSearching(true);
    setError("");
    try {
      const { data } = await api.get(`${FISCAL_BASE}/products`, { params: { q: query.trim() } });
      if (mounted.current && request === searchRequest.current) setProducts(data.items || []);
    } catch (failure) {
      const text = await fiscalError(failure);
      if (mounted.current && request === searchRequest.current) setError(text);
    } finally {
      if (mounted.current && request === searchRequest.current) setSearching(false);
    }
  }

  async function save() {
    if (operation.current) return;
    if (!form.seller_sku.trim() || !form.product_id) {
      setError("Informe o SKU exato da Amazon e selecione um produto ou kit CorePet.");
      return;
    }
    operation.current = true;
    setBusy(true);
    setError("");
    try {
      const payload = {
        account_id: account.id,
        seller_sku: form.seller_sku.trim(),
        product_id: Number(form.product_id),
        active: form.active,
      };
      if (form.id) await api.put(`${FISCAL_BASE}/mappings/${form.id}`, payload);
      else await api.post(`${FISCAL_BASE}/mappings`, payload);
      if (mounted.current) {
        setForm(emptyMapping());
        setVersion((value) => value + 1);
        onChanged();
      }
    } catch (failure) {
      const text = await fiscalError(failure);
      if (mounted.current) setError(text);
    } finally {
      operation.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  const options = products.map((product) => ({
    value: product.id,
    label: `${product.sku || product.id} — ${product.name}${product.product_type === "kit" ? " (kit)" : ""}`,
  }));
  if (
    form.product_id &&
    !options.some((option) => String(option.value) === String(form.product_id))
  )
    options.unshift({
      value: form.product_id,
      label: `${form.product_sku || form.product_id} — ${form.product_name || "Produto vinculado"}`,
    });
  return (
    <ModalPadrao
      titulo={`Mapear SKUs Amazon — ${account.seller_id}`}
      tamanho="ampla"
      onFechar={() => {
        if (!busy) onClose();
      }}
      rodape={
        <BotaoCancelar disabled={busy} onClick={onClose}>
          Concluir
        </BotaoCancelar>
      }
    >
      {loading ? (
        <p role="status">Carregando vínculos de produtos...</p>
      ) : (
        <div className="space-y-4 text-slate-800 dark:text-slate-100">
          <p className="text-sm">
            Vincule o SKU exato do pedido ao produto ou kit já cadastrado. O sistema usa o cadastro
            fiscal CorePet, sem procurar por semelhança de nome.
          </p>
          {error && (
            <p role="alert" className="text-sm text-red-700 dark:text-red-300">
              {error}
            </p>
          )}
          <InputTexto
            label="SKU exato na Amazon"
            value={form.seller_sku}
            onChange={(value) => setForm((current) => ({ ...current, seller_sku: value }))}
            required
            disabled={busy}
            maxLength={100}
          />
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <InputTexto
                label="Buscar produto ou kit CorePet"
                value={query}
                onChange={setQuery}
                disabled={busy}
              />
            </div>
            <BotaoInteracao icon={Search} loading={searching} disabled={busy} onClick={search}>
              Buscar produtos
            </BotaoInteracao>
          </div>
          <InputCombobox
            id="amazon-fiscal-product"
            label="Produto ou kit CorePet"
            value={form.product_id}
            opcoes={options}
            onChange={(value) => setForm((current) => ({ ...current, product_id: value }))}
            disabled={busy || searching}
            required
            help="A busca retorna até 50 resultados. Selecione o item correto, inclusive a quantidade que compõe o kit."
          />
          <div className="flex flex-wrap items-end gap-2">
            <InputCheck
              id="amazon-mapping-active"
              label="Vínculo ativo"
              checked={form.active}
              onChange={(value) => setForm((current) => ({ ...current, active: value }))}
              disabled={busy}
            />
            <BotaoSalva type="button" loading={busy} onClick={save}>
              Salvar vínculo
            </BotaoSalva>
            {form.id && (
              <BotaoCancelar disabled={busy} onClick={() => setForm(emptyMapping())}>
                Novo vínculo
              </BotaoCancelar>
            )}
          </div>
          <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
            <table className="w-full text-left text-sm">
              <thead>
                <tr>
                  <th className="p-3">Ações</th>
                  <th className="p-3">SKU Amazon</th>
                  <th className="p-3">Produto CorePet</th>
                  <th className="p-3">Situação</th>
                </tr>
              </thead>
              <tbody>
                {mappings.map((mapping) => (
                  <tr key={mapping.id} className="border-t border-slate-200 dark:border-slate-700">
                    <td className="p-3">
                      <BotaoInteracao
                        icon={Pencil}
                        tamanho="pequeno"
                        disabled={busy}
                        onClick={() => setForm(mapping)}
                      >
                        Editar vínculo
                      </BotaoInteracao>
                    </td>
                    <td className="p-3">{mapping.seller_sku}</td>
                    <td className="p-3">
                      {mapping.product_sku} — {mapping.product_name}
                    </td>
                    <td className="p-3">{mapping.active ? "Ativo" : "Inativo"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!mappings.length && (
              <p className="p-4 text-sm text-slate-500 dark:text-slate-400">
                Nenhum SKU vinculado nesta conta.
              </p>
            )}
          </div>
        </div>
      )}
    </ModalPadrao>
  );
}
