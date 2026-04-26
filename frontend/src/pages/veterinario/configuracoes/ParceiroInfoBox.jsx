export default function ParceiroInfoBox() {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 text-sm text-amber-800 space-y-2">
      <p className="font-semibold">Como funciona o veterinário parceiro?</p>
      <ul className="list-disc pl-5 space-y-1">
        <li>
          O veterinário parceiro tem sua <strong>própria conta no sistema</strong> (tenant independente).
        </li>
        <li>
          Prontuários, financeiro e estoque ficam <strong>separados</strong> por conta.
        </li>
        <li>
          A loja vê apenas o resumo do pet (vacinas, alergias, peso) - não o prontuário completo.
        </li>
        <li>A comissão configurada é calculada sobre os procedimentos realizados pelo veterinário.</li>
        <li>
          Para o veterinário se cadastrar como parceiro, ele precisa criar uma conta própria no sistema
          com tipo de organização &quot;Clínica Veterinária&quot;.
        </li>
      </ul>
    </div>
  );
}
