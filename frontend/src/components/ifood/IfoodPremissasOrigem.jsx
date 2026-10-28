// Um mesmo aviso no cadastro canônico e na calculadora da Central.
export default function IfoodPremissasOrigem({ margem }) {
  const referencia = margem?.rates_reference;
  const vigencia = margem?.rates_valid_from;
  return (
    <p className="v2-texto-ajuda">
      {referencia
        ? `Taxas do contrato informadas pela loja: ${referencia}.`
        : "Premissas informadas pela loja; referência do contrato ainda não registrada."}
      {vigencia ? ` Vigência desde ${vigencia.split("-").reverse().join("/")}.` : ""} As cobranças
      de cada venda são conferidas separadamente no Financeiro.
    </p>
  );
}
