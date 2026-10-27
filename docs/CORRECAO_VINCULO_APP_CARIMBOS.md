# Correção assistida do vínculo de app e carimbos

Preparado em 26/10/2026. Fusão autorizada concluída em produção em
**26/10/2026 às 22:38:01 BRT**, auditoria **227**. O registro confirmado está ao
final; a preparação e os ensaios abaixo são históricos, não etapas a repetir.

## Diagnóstico anterior à correção — 26/10/2026

No tenant do login legado `james_dionizio`, a pessoa de código público **2061**
(referência técnica 47188) possui o carimbo manual. O acesso do app estava ligado
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

## Preparação da prévia administrativa — antes da execução

Usar a fusão de pessoas existente, com o tenant correto autenticado e permissão
administrativa. A direção proposta é **2061 como principal** e **10851 como
duplicado**. A prévia deve exibir os códigos públicos, dados cadastrais,
referências vinculadas, soma de crédito e eventuais bloqueios de contas de app.

A duplicata também possuía **seis perfis de acesso e 306 referências de vendas
como vendedora**. Isso indicava uso como colaboradora e fez parte da
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

## Procedimento preparado para a aplicação autorizada

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
usuário fictício persistido. Até o término desse ensaio, nenhuma alteração havia
sido executada em produção; a aplicação real posterior está registrada abaixo.

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

A fusão adquire o bloqueio da vigência por empresa antes de bloquear as pessoas
e transferir regras. A mesma ordem é usada pela criação de vendas e alteração
de regras, evitando um ciclo entre o vínculo do funcionário da venda e a fusão.
As vendas compartilham o bloqueio entre si; só alterações de regra/fusão
precisam aguardar o término das inclusões já iniciadas na mesma empresa.

A prévia antiga chamava a leitura com bloqueio de linhas e foi recusada numa
transação de produção marcada `READ ONLY`, sem escrever dados. A correção,
validada em DEV e publicada, usa `bloquear=False` somente na prévia; a execução
mantém o padrão de bloqueio e recarrega os dados antes de fundir.

## Aplicação e conferência confirmadas em produção — 26/10/2026

O deploy oficial terminou às **22:35:49 BRT**, no commit
`3f2e78f34ecfae558431008832452fa9ad22dfb6` da `main` (PR **#1567**), com head
`zzzzzb20261027a1`. Os cinco containers, o health público, o watchdog e a revisão
servida foram conferidos. O backend com a proteção de vínculo e a fusão revisada
está publicado.

A operação autorizada ocorreu às **22:38:01 BRT**, com a seguinte conferência:

- Principal: referência técnica **47188**, código público **2061**.
- Duplicado: referência técnica **50401**, código público **10851**, inativo e com
  `merged_into_id` apontando ao principal. Auditoria administrativa **227**.
- Conta de app **84** e cargos de `UserTenant` preservados. Mantidos
  `is_cliente=true`, `is_funcionario=true` e crédito **zero**.
- As **306 vendas** conservaram IDs, números, status e totais.
- Carimbo manual **13739** preservado, sem lançamento compensatório. O handler
  `meus_beneficios` passou a retornar **um carimbo disponível, meta 12**, no
  principal correto.
- Os seis grants **391–396** foram transferidos ao principal, preservando IDs,
  datas de criação, notas e concedentes. O total final é de **sete perfis**:
  a sincronização também materializou o perfil `funcionario`, derivado da flag
  legada já existente. Esse grant **458** foi auditado com ator **83**. Não foi
  alteração do cargo da conta nem perda dos seis grants originais.
- A conferência posterior somente de leitura passou. Sua contagem permite
  exclusivamente o perfil de funcionário derivado e auditado, além dos grants
  originais; não trata qualquer perfil adicional como aceitável.

As OTAs do mesmo commit e JavaScript/assets foram publicadas com saída zero no
canal `production`, para Android e iOS: runtime **1.0.4**, grupo
`9e3a71b4-8882-4a7d-a778-0e8fbaffa060` às **22:36:47 BRT**; runtime **1.0.3**,
grupo `b736b409-f55d-41e7-aad1-348339ee6c99` às **22:37:02 BRT**. Versões,
runtimes e configurações dos binários foram preservados.

Prévias, resultados, auditoria conferida e resumo das OTAs permanecem em
`runtime/tarefas-melhorias-20261026/`, ignorado pelo Git. Os backups da operação
estão registrados na [ficha da entrega](entregas/2026-10-26-melhorias-operacionais.md).

- [x] Código, publicação e correção real do vínculo concluídos.
- [x] Saldo do benefício e preservação das referências conferidos em produção.
- [x] OTA publicada para os dois runtimes, nas duas plataformas.
- [ ] Conferência humana no aparelho físico da cliente, incluindo voltar à tela
      de benefícios. Essa pendência de acompanhamento não bloqueia a entrega técnica.
