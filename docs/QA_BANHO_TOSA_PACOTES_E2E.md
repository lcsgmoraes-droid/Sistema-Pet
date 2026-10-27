# Pacote de quatro banhos: aceite reexecutável em DEV

A suíte usa frontend, backend e banco reais de desenvolvimento. O Chrome é
isolado e headless; não usa o perfil ou o login do Lucas. Não há respostas
simuladas para saldo, agenda ou financeiro.

## Executar

Com o frontend local na porta 5173 e o backend DEV na porta 8000:

```powershell
Set-Location C:\Users\lcs_g\Sistema-Pet\frontend
$env:E2E_CREATE_TEST_IDENTITY = "1"
npm run test:e2e:banho-tosa
```

Para portas diferentes, defina `E2E_BASE_URL` e `E2E_BT_API_URL` com origens
HTTP locais e porta explícita. URLs remotas, HTTPS, credenciais na URL e caminhos
adicionais são recusados antes de iniciar o teste. Não existe opção de liberar
produção. A suíte também exige o health detalhado que o backend protege em
produção/staging. Sem a autorização de criar identidade, a execução geral do
Playwright pula esta suíte, e o comando específico informa a variável necessária.

Cada execução cadastra sua própria empresa, operador, tutor, dois pets, serviços,
box, caixa e forma de recebimento. Os nomes começam com `QA BT` e um identificador
único. A senha é gerada em memória; o teste não lê credenciais existentes nem
grava senhas/tokens no relatório. Não seleciona a primeira empresa: confere o
nome e o ID da empresa que acabou de criar.

As chamadas `/api` da interface passam diretamente ao backend DEV informado,
preservando suas respostas reais. Assim, uma configuração acidental do proxy
do Vite não leva o teste à produção. A navegação bloqueia origens remotas.

## Cenários

1. Cadastrar o pacote de quatro banhos pela interface e vinculá-lo ao pet,
   gerando a cobrança de R$ 200 em aberto.
2. Agendar pela interface: quatro disponíveis viram três disponíveis e um
   reservado. Cancelar devolve quatro. Novo agendamento/check-in confirma um
   usado; cancelar o atendimento pela ficha devolve o saldo sem cancelar a
   cobrança do pacote.
3. Abrir a venda pelo menu do pacote e receber R$ 80 no PDV. Confirmar estado
   parcial, reabrir a mesma venda e receber R$ 120 em uma segunda confirmação.
   A situação passa a paga e os quatro créditos continuam disponíveis. O segundo
   recebimento preserva o snapshot da venda parcial, sem enviar `PUT`. Ao voltar
   à aba dos pacotes, o recebimento aparece sem clicar em Atualizar.
4. Agendar outro pet do mesmo tutor e um serviço não incluído: ambos seguem
   avulsos, sem consumir o pacote. Esses casos usam a API real para preparar
   agendas e conferem também a lista de pacotes na interface.
5. Reservar quatro banhos; o quinto fica avulso. Cancelar os agendamentos
   restaura quatro disponíveis, com o pagamento preservado.

Asserções de saldo consultam a API real após cada transição. A cobrança não é
considerada recebida apenas porque uma venda foi criada.

No cenário de retorno do PDV, a suíte desliga a emulação de foco que o Playwright
ativa por padrão. A troca real de abas passa a emitir os eventos nativos de foco
e visibilidade. O teste não dispara eventos falsos nem força uma atualização da
lista: exige que o aplicativo consulte os dados reais ao voltar.

## Evidências e dados criados

O Playwright salva capturas em `frontend/test-results/` e anexa IDs sintéticos
da empresa, tutor, pet, pacote, contratação e venda. O rastreamento de rede está
desligado para não registrar tokens de sessão. Os diretórios de resultado não
devem ser versionados.

A suíte cancela seus agendamentos, preservando histórico financeiro e de saldo.
Ela não apaga empresas ou vendas para fingir que o teste nunca aconteceu. Uma
falha pode deixar dados prefixados para investigação; a próxima execução usa
outro identificador e não depende de limpar os anteriores.

Teste isolado das guardas, sem backend/navegador:

```powershell
node --test scripts/test-banho-tosa-e2e-guardas.mjs
```

