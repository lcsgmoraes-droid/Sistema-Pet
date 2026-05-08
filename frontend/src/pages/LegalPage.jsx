import { Link } from 'react-router-dom';
import { PawPrint } from 'lucide-react';

const sections = {
  termos: {
    title: 'Termos de Uso',
    version: 'Versao 2026-05-08',
    intro:
      'Estes termos regulam o acesso ao Pet Shop Pro, plataforma de gestao para operacoes de pet shop, clinica, estoque, vendas, entregas e canais digitais.',
    items: [
      ['Uso da plataforma', 'O usuario deve fornecer informacoes verdadeiras, manter suas credenciais em seguranca e usar o sistema apenas para fins licitos e relacionados a sua operacao.'],
      ['Conta e tenant', 'Cada empresa cadastrada possui um ambiente proprio. O administrador inicial e responsavel por usuarios, permissoes e dados inseridos no sistema.'],
      ['Dados operacionais', 'Pedidos, vendas, clientes, pets, estoque, financeiro e integracoes devem ser conferidos pelo usuario responsavel antes de decisoes comerciais ou fiscais.'],
      ['Integracoes', 'Conexoes com marketplaces, ERP, emissores fiscais, WhatsApp, meios de pagamento e outros servicos dependem de disponibilidade e regras dos respectivos provedores.'],
      ['Seguranca', 'O usuario deve proteger senha, dispositivos e acessos. Atividades suspeitas devem ser comunicadas ao suporte para bloqueio ou revisao.'],
      ['Alteracoes', 'Estes termos podem ser atualizados. Quando houver mudanca relevante, o sistema podera solicitar novo aceite.'],
    ],
  },
  privacidade: {
    title: 'Politica de Privacidade',
    version: 'Versao 2026-05-08',
    intro:
      'Esta politica resume como dados pessoais sao tratados no Pet Shop Pro para autenticacao, operacao da loja, atendimento, entregas, comunicacoes e seguranca.',
    items: [
      ['Dados tratados', 'Podemos tratar nome, e-mail, telefone, CPF/CNPJ, endereco, dados de compra, dados de pets, registros de atendimento, logs de acesso e dados necessarios para operacao.'],
      ['Finalidades', 'Os dados sao usados para login, gestao operacional, vendas, entregas, suporte, prevencao a fraude, auditoria, integracoes contratadas e cumprimento de obrigacoes legais.'],
      ['Compartilhamento', 'Dados podem ser compartilhados com provedores necessarios a operacao, como hospedagem, e-mail, pagamentos, fiscal, ERP, marketplace, entrega e suporte.'],
      ['Direitos do titular', 'O titular pode solicitar confirmacao de tratamento, acesso, correcao, eliminacao quando aplicavel, portabilidade e informacoes sobre compartilhamento.'],
      ['Retencao', 'Dados operacionais e fiscais podem ser mantidos pelo periodo necessario para execucao do contrato, obrigacoes legais, auditoria e defesa de direitos.'],
      ['Seguranca', 'Aplicamos controles de acesso, autenticacao, logs, segregacao por tenant e medidas tecnicas para reduzir riscos de acesso indevido.'],
    ],
  },
};

const LegalPage = ({ type = 'termos' }) => {
  const content = sections[type] || sections.termos;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <main className="mx-auto max-w-3xl px-6 py-10">
        <Link to="/login" className="inline-flex items-center gap-2 text-sm font-semibold text-blue-700 hover:text-blue-800">
          <PawPrint className="h-4 w-4" />
          Pet Shop Pro
        </Link>

        <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="mb-8">
            <div className="text-xs font-bold uppercase tracking-wide text-blue-700">{content.version}</div>
            <h1 className="mt-2 text-3xl font-bold">{content.title}</h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">{content.intro}</p>
          </div>

          <div className="space-y-6">
            {content.items.map(([title, text]) => (
              <section key={title}>
                <h2 className="text-base font-semibold text-slate-900">{title}</h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">{text}</p>
              </section>
            ))}
          </div>

          <div className="mt-8 rounded-xl bg-blue-50 p-4 text-sm leading-6 text-blue-900">
            Este texto e uma base operacional inicial e deve ser revisado juridicamente antes de uso comercial em larga escala.
          </div>
        </div>
      </main>
    </div>
  );
};

export default LegalPage;
