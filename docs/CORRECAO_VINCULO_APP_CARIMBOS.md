# Correção assistida do vínculo de app e carimbos

Preparado em 26/10/2026. Nenhuma fusão ou alteração de vínculo foi executada em produção.

## Diagnóstico do caso informado

No tenant do login legado `james_dionizio`, a pessoa de código público **2061**
(referência técnica 47188) possui o carimbo manual. O acesso do app está ligado
à pessoa de código público **10851** (referência técnica 50401), sem esse saldo.
O usuário de app relacionado é a referência técnica 84.

O tenant cadastrado é **Atacadão das Rações Pet Loja1**, referência
`c06e62ae-127c-4bf1-adb8-eeabf5d04596`. A leitura autorizada confirmou o
carimbo manual disponível e a duplicata; a causa nos dados está comprovada.
O teste no aparelho físico da cliente ainda não foi realizado.

A conta foi criada por telefone e tem `login_phone`, mas os campos de telefone,
e-mail e CPF do perfil estão vazios. O resolvedor não considerava `login_phone`.
O código agora o usa como alternativa quando o telefone do perfil está vazio.
Um vínculo explícito já existente continua preservado: a prevenção não funde
cadastros nem troca a pessoa de uma conta durante login ou consulta de benefícios.

## Prévia para revisão administrativa

Usar a fusão de pessoas existente, com o tenant correto autenticado e permissão
administrativa. A direção proposta é **2061 como principal** e **10851 como
duplicado**. A prévia deve exibir os códigos públicos, dados cadastrais,
referências vinculadas, soma de crédito e eventuais bloqueios de contas de app.

A duplicata também possui **seis perfis de acesso e 306 referências de vendas
como vendedora**. Isso indica uso como colaboradora e deve fazer parte da
revisão: confirmar que os dois cadastros representam a mesma pessoa, manter
todos os perfis ativos, flags de funcionária/veterinária/entregadora existentes,
cargo da conta e referências de comissão/vendas. Ambos os créditos estão em
zero; a correção não deve alterar cobrança nem permissão de acesso.

Contrato de prévia, sem executar a fusão:

```http
POST /clientes/fusao/preview
Content-Type: application/json

{
  "pessoa_principal_id": 47188,
  "pessoa_duplicada_id": 50401
}
```

Revisar os dados, confirmar que se trata da mesma pessoa e que há somente uma
conta de app. O serviço bloqueia a fusão de cadastros ligados a contas diferentes.
Guardar a prévia fora do Git e registrar a autorização específica do Lucas antes
de executar qualquer alteração de produção.

## Aplicação após autorização

Usar o fluxo de fusão da tela de Pessoas com os mesmos cadastros e as decisões
de campo aprovadas. O endpoint correspondente é `/clientes/fusao/executar`;
somente preparar o corpo não autoriza enviá-lo.

```json
{
  "pessoa_principal_id": 47188,
  "pessoa_duplicada_id": 50401,
  "decisoes_campos": {},
  "observacao": "Correção do vínculo do app e preservação do carimbo manual; autorização de Lucas registrada antes da execução."
}
```

Substituir as decisões vazias pelas escolhas revisadas se a prévia apontar
conflitos. A fusão transfere o vínculo de acesso ao principal, preserva as
referências financeiras e campanhas, inativa o duplicado com `merged_into_id`
e registra o histórico administrativo. Não lançar outro carimbo para compensar
o vínculo, nem marcar cobranças como pagas durante essa correção.

O serviço aplica união das flags operacionais, independentemente da escolha
de campos textuais, e une os perfis ativos no cadastro principal. O vínculo
`UserTenant.role_id`, o usuário e seu estado ativo não são trocados pela fusão.
Antes da aplicação autorizada, revisar os seis perfis reais e guardar a prévia
e os valores anteriores para a conferência posterior.

Os registros de permissão são preservados: quando não há o mesmo perfil no
principal, a fusão muda somente o vínculo de pessoa e sincroniza o acesso,
mantendo ID, data de criação, notas e concedente. Perfis revogados continuam
revogados, salvo quando a união das flags cadastrais já concede aquele perfil.
Se os dois cadastros têm o mesmo perfil, o registro do principal permanece e
recebe a união do acesso; o registro conflitante é conservado no duplicado,
inativo, com suas notas/datas. Nenhum grant é apagado. O estado anterior
completo, incluindo IDs, notas, datas e estado ativo, fica no histórico da
fusão; o resultado identifica cada grant transferido ou conservado no
duplicado. Assim, um conflito não descarta metadados históricos nem cria
permissão adicional para a pessoa inativada.

Conferir depois no gestor e no app autenticado: pessoa 2061, mesmo saldo de
carimbos, cartão atualizado ao voltar à tela e ausência de nova duplicata.

## Ensaio seguro em DEV

`backend/tests/integration/test_vinculo_app_carimbo_merge_local.py` cria usuário,
pessoas e carimbo fictícios numa transação local. Exercita o resolvedor, a prévia,
a fusão administrativa e o saldo do app antes/depois. Sempre executa rollback;
não usa os IDs nem os dados pessoais do caso real. O teste só aceita URL local
e banco com sufixo `_dev`, via `COREPET_TEST_POSTGRES_URL`.

Os testes unitários de identidade verificam que o fallback de telefone evita
nova duplicata sem sobrepor vínculo explícito nem tomar cadastro de outra conta.

Resultado do ensaio local: **passou**, com seis perfis ativos, flags de
funcionária/veterinária/entregadora e 306 vendas fictícias como vendedora. A
prévia não emitiu `FOR UPDATE`; a execução manteve o bloqueio de linhas. A
fusão preservou perfis, cargo e conta ativa, transferiu as 306 referências e
mudou o saldo do app de zero para um. Ao final, rollback confirmado e nenhum
usuário fictício persistido. Nenhuma alteração foi executada em produção.

O ensaio foi repetido com o algoritmo que conserva os registros: **dois
cenários PostgreSQL aprovados**, com e sem perfil já existente no principal.
Em ambos, IDs, criação, notas e concedente de todos os grants foram
preservados, inclusive na colisão entre um perfil revogado do principal e
um ativo do duplicado. A auditoria foi conferida, assim como seis perfis
ativos finais, cargo, conta ativa, 306 vendas e carimbo. O teste unitário
também cobre grant revogado sem colisão e sua permanência como revogado.

Após acrescentar a vigência das comissões, outro ensaio PostgreSQL confirmou
que a fusão também transfere a FK de funcionário das versões históricas das
regras. A regra de R$ 3,00 de uma venda anterior continua sendo encontrada
depois da fusão no principal. O JSON original da versão é preservado, e a
referência técnica de criação da venda permanece imutável. A cobertura está
em `backend/tests/integration/test_comissoes_vigencia_limites_local.py`, com
rollback obrigatório e execução prevista também nos bancos efêmeros do CI.

A prévia antiga chamava a leitura com bloqueio de linhas e foi recusada numa
transação de produção marcada `READ ONLY`, sem escrever dados. O código DEV
agora usa `bloquear=False` somente na prévia; a execução mantém o padrão de
bloqueio e recarrega os dados antes de fundir.
