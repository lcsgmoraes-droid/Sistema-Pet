import { useEffect, useState } from "react";
import api from "../../api";
import InputRadio from "../../components/v2/InputRadio/InputRadio";
import InputTexto from "../../components/v2/InputTexto/InputTexto";

// Busca uma pessoa cadastrada da loja (por nome ou telefone) para criar ou vincular um card.
// Quem já tem card não aparece para escolha, só é contado no aviso.
export default function CrmBuscaTutor({ error = "", id, lojaId, onEscolher, value }) {
  const [busca, setBusca] = useState("");
  const [resultados, setResultados] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [falhou, setFalhou] = useState(false);

  useEffect(() => {
    const termo = busca.trim();
    if (termo.length < 2) {
      setResultados([]);
      return undefined;
    }
    let ativo = true;
    const espera = setTimeout(async () => {
      setBuscando(true);
      try {
        const { data } = await api.get("/crm/tutores", {
          params: { busca: termo, loja_id: lojaId || undefined },
        });
        if (ativo) {
          setResultados(data);
          setFalhou(false);
        }
      } catch {
        if (ativo) setFalhou(true);
      } finally {
        if (ativo) setBuscando(false);
      }
    }, 300);
    return () => {
      ativo = false;
      clearTimeout(espera);
    };
  }, [busca, lojaId]);

  const livres = resultados.filter((pessoa) => !pessoa.tem_card);
  const comCard = resultados.length - livres.length;
  const termoCurto = busca.trim().length < 2;

  let ajuda = "Digite pelo menos 2 letras do nome ou parte do telefone.";
  if (falhou) ajuda = "Não foi possível buscar agora. Tente de novo.";
  else if (buscando) ajuda = "Buscando…";
  else if (!termoCurto && resultados.length === 0) ajuda = "Nenhuma pessoa encontrada.";
  else if (comCard > 0)
    ajuda = `${comCard} pessoa(s) encontrada(s) já têm card e não aparecem na lista.`;

  return (
    <div className="space-y-3">
      <InputTexto
        id={id}
        label="Buscar pessoa cadastrada"
        value={busca}
        onChange={setBusca}
        help={ajuda}
        error={error}
        required
      />
      {livres.length > 0 ? (
        <InputRadio
          name={`${id}-resultado`}
          label="Escolha a pessoa"
          value={value}
          onChange={onEscolher}
          opcoes={livres.map((pessoa) => ({
            value: pessoa.id,
            label: pessoa.telefone ? `${pessoa.nome} · ${pessoa.telefone}` : pessoa.nome,
          }))}
        />
      ) : null}
    </div>
  );
}
