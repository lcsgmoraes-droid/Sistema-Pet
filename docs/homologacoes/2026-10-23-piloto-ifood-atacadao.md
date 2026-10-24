# Piloto assistido iFood — Atacadão

| Campo | Valor |
|---|---|
| Data | 23/10/2026, horário de Brasília |
| Situação | Conexão e prévia corrigida validadas em produção; SKU piloto selecionado; integração da empresa desativada, sem anúncio enviado; vínculo e estoque automático pendentes |
| Escopo | Jornada de implantação e conferência do SKU `018631.1` |
| CorePet | Empresa Atacadão das Rações Pet |
| iFood | Loja Atacadão das Rações Avenida Brasil |
| Método atual informado | Atualização manual pelo Portal do Parceiro ou aplicativo |
| Integração alvo | Aplicativo próprio CorePet, criado no iFood Developer |
| Guia público em preparação | [Guia de integração](../GUIA_INTEGRACAO_IFOOD.md) |

## Limites do registro

Este documento registra fatos observados durante a navegação e as pendências
do piloto. A autorização do aplicativo CorePet pela loja foi concluída. A
conexão do ERP foi validada pela própria tela após a correção registrada abaixo.
Essa validação não comprova vínculo de produto, envio ou estoque integrado.

Não foram publicados produtos ou criados vínculos nesta etapa. Foi salva apenas
a seleção local do SKU piloto para o canal, preservando seus preços e demais
campos. A ativação no iFood não comprova sincronização ou operação automática
do ERP. A configuração da integração no ERP foi corrigida e salva desativada,
conforme registrado adiante.

O documento não contém credenciais, identificadores da loja na API, nomes de
usuários, contatos pessoais, custos ou outros dados financeiros reais. Capturas
originais ficam fora do Git.

## Separação entre produção e DEV

| Frente | Ambiente | Situação comprovada |
|---|---|---|
| Credenciais do aplicativo | Produção | Manutenção autorizada executada, sem deploy de código por essa ação |
| Autorização e conexão do ERP | Produção | Autorização concluída e teste de conexão bem-sucedido; configuração da empresa desativada |
| Seleção do piloto | Produção | Somente intenção local do SKU salva; nenhum anúncio enviado |
| Correção de código da prévia | DEV | Implementada; testes focados, gate completo e revisão independente aprovados |
| Conferência visual da prévia corrigida | DEV isolado, dados fictícios | Produto apto no início da prévia e selecionado, mesmo após catálogo grande de rejeitados |
| Publicação da correção da prévia | Produção | PR 1549 integrado e deploy oficial concluído em a75cba5a1 |
| Conferência da prévia após deploy | Produção | SKU piloto primeiro, selecionado e único habilitado; conexão revalidada e integração da empresa desativada |
| Integração financeira | Ainda não implementada | Financial e apuração posterior das cobranças continuam pendentes |

## Observações confirmadas até o momento

1. O acesso ao iFood estava autenticado no perfil Chrome da loja, com o Gestor
   de Pedidos exibindo **Atacadão das Rações Avenida Brasil**.
2. A área **Cardápio** mostrou **Nenhum restaurante disponível**.
3. Foi seguido o caminho **Portal do Parceiro → Catálogo**. A transição usou
   autenticação automática, sem informar credenciais durante essa navegação.
4. O Portal apresentou o catálogo da operação de pet shop/mercado, com **Gestão
   de Catálogo** e **Acompanhamento de integrações**, e situações de produtos
   ativos, inativos, em análise e para cadastrar.
5. Em **Serviços e soluções → Integrações**, apareceu **Bling PDV — Ativo**.
   Isso não comprova que preço ou estoque estejam sendo sincronizados. O
   usuário informou que a atualização atual é manual. O Bling foi somente
   inventariado como integração preexistente, sem alteração. A integração alvo
   do piloto é o aplicativo próprio **CorePet** no iFood Developer, conforme
   orientação expressa do usuário.
6. O CorePet inicialmente estava em outra empresa. Antes de continuar, o acesso
   foi corrigido para **Atacadão das Rações Pet**.
7. Na empresa correta, o caminho **Central do iFood → Buscar produto existente**
   encontrou o SKU `018631.1`, identificado como **MGZ EXT CALOPSITAS E PERIQUIT
   PM13 900G**. A pesquisa feita na empresa anterior não é evidência de ausência
   desse produto.
8. Na consulta inicial, o produto estava **fora da seleção**, com estoque disponível, contribuição
   **Não calculada** e uma orientação. Preço e saldo numérico não são registrados
   neste documento.
9. O menu de ações oferece **Simular preço e margem**, **Editar no cadastro** e
   **Selecionar para iFood**. A tentativa de **Editar no cadastro** redirecionou
   inicialmente à página pública/login, sem carregar os campos. Foi solicitada
   nova autenticação ao usuário. A retomada e a consulta posterior do cadastro
   estão registradas adiante; nenhum produto foi salvo.
10. Em **iFood Developer → Meus aplicativos**, foi encontrado o aplicativo
    **CorePet**, identificado como **Centralizado**, **Merchant**, com status
    **Parcialmente homologado**. A consulta ocorreu no acesso autenticado
    indicado pelo usuário, em aba própria do perfil Chrome CorePet.
11. Os detalhes do aplicativo mostram a categoria **GROCERIES**. Os módulos
    **Order**, **Item**, **Picking**, **Events** e **Merchant** aparecem
    selecionados; **Promotion** não está selecionado. A seleção desses campos
    não comprova a homologação individual de cada módulo.
12. Na primeira consulta de **Permissões**, o Portal informou **O aplicativo
    ainda não foi autorizado por nenhum merchant**. Foi aberto inicialmente
    apenas o modal **Pedir autorização**, que solicita identificação da loja
    por ID/CNPJ e prevê uma busca antes da ação final.
13. Em **Portal do Parceiro → Configurações → Perfil da loja**, foi localizado
    e conferido o identificador da loja para preparar a busca exata do mesmo
    estabelecimento no Developer. Seu valor não é reproduzido neste registro;
    a solicitação e a aprovação posteriores estão registradas adiante.
14. Na Gestão de Catálogo, a busca por nome **calopsitas**, sem restringir a
    produtos ativos ou inativos, não retornou item. Isso ainda é insuficiente
    para concluir que o produto está ausente. A consulta posterior pelo EAN
    está registrada adiante; a correspondência remota continua não comprovada.
15. O responsável confirmou expressamente os aceites e as responsabilidades,
    assim como o envio da solicitação de autorização. Depois do envio, o
    Developer passou a **Aguardando Ativação** e o cartão CorePet no Portal
    apresentou **Permissão pendente**.
16. Em **Portal do Parceiro → Integrações → CorePet → Mais Ações → Permitir**,
    foi aberta a confirmação com os acessos **Pedidos, Item, Eventos e
    Merchant** e os [Termos de Uso do
    iFood](https://developer.ifood.com.br/pt-BR/terms-of-use/partner).
17. O responsável confirmou os acessos e, depois, o aceite final dos termos.
    Foi acionado **Autorizar**. O Portal respondeu **Integração autorizada** e
    o cartão **CorePet** passou a **Ativo**. Isso comprova a autorização da loja
    para o aplicativo, ainda não a conexão ou a sincronização do ERP.
18. A sessão do CorePet foi retomada e o cadastro canônico do produto carregou.
    Foram conferidos EAN principal, comercial e fiscal consistentes, unidade
    **UN**, tipo **Produto simples**, embalagem **900 g**, descrição preenchida
    e imagens com uma principal. Não foram salvas alterações no produto.
19. A pesquisa pelo EAN na Gestão de Catálogo sem filtro de situação, abrangendo
    ativos/inativos, não retornou item. As consultas nas áreas **Em análise** e
    **Para cadastrar** também não retornaram item. O produto **não foi localizado
    nessas consultas**; isso não é prova absoluta de ausência no iFood.
20. Em **CorePet → Configurações → Integrações → Abrir integração iFood**, havia
    um Merchant ID diferente do conferido para a loja e a opção de ativação
    estava marcada. O identificador foi corrigido para o da loja autorizada e
    a configuração foi salva com a integração **desativada**. Fonte, acréscimo
    e reserva foram preservados; seus valores não são reproduzidos aqui.
21. O botão **Testar conexão** falhou nas duas tentativas. A segunda foi
    acompanhada pelo diagnóstico da própria chamada da tela: **HTTP 502**, JSON
    com `error=internal_server_error` e mensagem genérica **Erro interno no
    servidor**. O ERP apresentou **Requer atenção**. Naquele momento, a resposta
    genérica não permitia concluir a causa. O diagnóstico posterior está
    registrado abaixo.
22. Até a autorização operacional posterior, nenhuma consulta ou comando no
    servidor de produção havia sido executado, conforme as regras do
    repositório. A autorização no iFood estava concluída; conexão do ERP,
    prévia e envio permaneciam sem validação.
23. O responsável autorizou expressamente um diagnóstico **somente leitura**
    no servidor de produção. A consulta foi executada e confirmou que o runtime
    utiliza um aplicativo centralizado de **teste**, diferente do aplicativo
    **CorePet de produção** autorizado pela loja. O Client ID foi comparado
    somente por resultados booleanos, sem exibir seus valores. O `last_error`
    sanitizado foi **Merchant ID informado não está vinculado ao aplicativo
    CorePet**.
24. A consulta somente leitura também mostrou as flags de escrita de catálogo
    e operações de pedidos habilitadas e o polling desabilitado. O agregado de
    configurações iFood mostrou somente uma configuração, sem nenhuma ativa.
    Esses dados não incluem identificadores de empresas e não comprovam envio
    ou sincronização.
25. Depois do diagnóstico, o responsável autorizou expressamente copiar as
    credenciais do aplicativo **CorePet de produção** para a configuração
    protegida do servidor e recriar somente o backend usando **a mesma imagem**,
    para carregá-las. A execução posterior está registrada abaixo; nenhum valor
    de credencial, identificador ou conteúdo de backup é incluído neste registro.
26. A correção autorizada foi **executada com sucesso**: somente as duas
    credenciais iFood foram trocadas do aplicativo de teste para o CorePet de
    produção, na configuração protegida do servidor. As demais linhas do arquivo
    foram preservadas. Somente o backend foi recriado, usando **a mesma imagem
    que já estava em produção**, sem deploy de código por essa manutenção.
    Contêineres de banco, nginx e workers não foram alterados por essa ação.
27. Após a manutenção, o polling permaneceu desabilitado; a saúde do backend e
    a API pública responderam normalmente. O backup seguro permanece fora do
    Git. O transporte temporário criptografado de credenciais, incluindo chave
    privada, payload e pasta temporária, foi removido. Nenhum segredo foi
    incluído nas mídias ou no Git.
28. Uma tentativa de selecionar o SKU na central não concluiu a atualização
    durante um deploy externo. A recarga posterior confirmou **Selecionados: 0**.
    Nenhum produto havia sido salvo até esse ponto; isso não é registrado como
    seleção bem-sucedida.
29. Após a correção, na empresa **Atacadão das Rações Pet**, o caminho
    **Configurações → Integrações → iFood → Testar conexão** retornou o selo
    **Conexão validada** e a mensagem **Loja localizada e conexão validada no
    iFood.** A opção de ativar a integração para a empresa permaneceu desmarcada.
    Isso comprova o teste de conexão do ERP; vínculo de produto, envio e estoque
    automático continuam pendentes. Nenhum anúncio foi enviado nem produto salvo
    até este marco da preparação.
30. Em seguida, foi selecionado **somente o SKU `018631.1`** na Central do iFood,
    salvando `anunciar_ifood=true`. A tela mostrou **Produto selecionado**,
    **Selecionados: 1** e o status **Pronto para envio**. Preço, regras e demais
    campos do produto foram preservados. A configuração da empresa permanece
    desativada; essa seleção não enviou o produto ao iFood.
31. A orientação de rentabilidade permanece porque as taxas ainda são
    desconhecidas. A contribuição não foi calculada; nenhum valor estimado é
    tratado como comprovado.
32. Em **Configurações → Integrações → iFood → Conferir produtos**, o contador
    confirmou um produto pronto, mas a prévia exibiu uma lista limitada com
    todos os controles de seleção desabilitados e sem o SKU piloto. Foi
    identificado que o limite era aplicado antes de priorizar os produtos aptos.
    Essa limitação impede preparar a prévia do piloto pela tela; não houve envio.
33. A correção da prévia foi encaminhada primeiro para **DEV**, no worktree
    `ifood-piloto-publicacao`, branch `codex/ifood-piloto-publicacao`, com mudança
    de backend e testes. Os documentos deste piloto foram movidos para esse
    worktree; o worktree anterior das taxas temporárias voltou a ficar limpo.
34. A correção foi implementada em **DEV**, priorizando os produtos aptos antes
    de aplicar o limite da lista, preservando os grupos e o filtro de pendências.
    **91 testes iFood passaram**, incluindo oito casos novos e doze casos no
    arquivo de contratos alterado. A cobertura inclui catálogo grande, limites,
    filtro, resultado vazio e ordem dos grupos.
35. A revisão técnica independente terminou **sem achados** e as verificações
    de lint e formato Ruff passaram. O gate completo **FLUXO_UNICO release-check**
    terminou com **exit 0**, no commit `d42fbfacb`: 274 testes de faturamento,
    131 de billing, 91 iFood, 203 root, 769 multitenant, 58 frontend iFood e 104
    mobile, com os skips esperados registrados pelo gate (6/2/22). Lint, formato,
    build, auditorias e typecheck mobile passaram. No mesmo commit
    `d42fbfacb`, os **11 checks do PR 1549 foram aprovados**.
36. A conferência visual foi realizada no **DEV isolado da porta 18083**, com
    empresa e produtos fictícios. O catálogo continha 61 produtos: 60 rejeitados
    antes de um único apto, identificado na massa fictícia como produto 61. Na
    prévia com limite de 50, o apto apareceu primeiro e selecionado. As consultas
    de API com limites 1, 50 e 200 e o filtro `only_issues` também passaram.
37. O dry-run legado retornou **403** para o usuário fictício sem a flag global
    `is_admin`. Não foram alteradas permissões para contornar essa proteção.
    O DEV usou credenciais vazias, flags iFood desabilitadas e rede interna;
    nenhuma operação externa foi executada.
38. Antes do deploy registrado adiante, a correção da prévia estava validada
    somente em DEV. A manutenção de credenciais foi uma etapa operacional
    distinta da posterior publicação de código. Nenhum anúncio foi enviado.
39. Após a dúvida do usuário sobre taxas e resultado financeiro, ficou
    registrada uma pendência separada: a integração atual não utiliza
    **Financial**. A documentação oficial confirma o módulo para Groceries e
    sua homologação em processo separado dos módulos operacionais. A proposta
    futura é distinguir estimativa antes da venda de apuração depois, reunindo
    cobranças efetivas do iFood e os custos correspondentes do ERP. Nada dessa
    apuração foi implementado ou validado neste piloto, e nenhum dado financeiro
    privado foi copiado.
40. Foi consultado **somente em leitura** o Financeiro de setembro no Portal do
    Parceiro. A consulta permitiu distinguir componentes de comissão, pagamento,
    promoção custeada pela loja e taxas cobradas ao consumidor, sem reproduzir
    valores neste documento. Isso comprova a disponibilidade **manual no Portal**,
    não o recebimento desses dados por API no CorePet.
41. O **PR 1549 foi integrado** e o deploy oficial terminou com **exit 0**, da
    baseline `7fed` para o commit `a75cba5a1`. A baseline já continha outra
    correção publicada separadamente, fora desta entrega. O gate completo passou
    em `552fc9b11`, e os oito checks obrigatórios do commit `a75cba5a1` foram
    aprovados. O status oficial mostrou os cinco serviços saudáveis, a API com
    saúde OK e o watchdog saudável.
42. Após o deploy, a conferência em uma nova aba autenticada, na empresa correta,
    mostrou **7.145 produtos, um apto e 7.144 com impedimentos**. A prévia de 50
    opções exibiu **somente uma habilitada**, com o **SKU `018631.1` primeiro e
    selecionado**. A opção de ativar a integração permaneceu desmarcada, e
    **Testar conexão** confirmou novamente **Loja localizada e conexão validada
    no iFood.** Não houve POST/PATCH de catálogo, reset, polling ou anúncio
    enviado.
43. Na pendência financeira, foi distinguida a consulta da **comissão contratada
    para previsão** das **cobranças efetivas via Financial**. A publicação no
    módulo Item recebe dados de produto e não retorna cotação de comissão ou
    taxas. Nenhuma taxa real, informação bancária ou dado de pedido é incluído
    neste registro.

## Registro incremental da jornada

| Etapa | Ambiente / caminho | Ação e resultado observado | Efeito externo | Evidência / situação |
|---|---|---|---|---|
| Identificar loja iFood | Gestor de Pedidos | Loja Atacadão das Rações Avenida Brasil exibida | Consulta | Tela observada; imagem inicial fornecida pelo usuário |
| Consultar Cardápio | Gestor de Pedidos → Cardápio | Mensagem Nenhum restaurante disponível | Consulta | Navegação observada; captura específica não inventariada |
| Abrir catálogo correto | Portal do Parceiro → Catálogo | Transição autenticada e Gestão de Catálogo disponível | Consulta | Navegação observada; captura específica não inventariada |
| Inventariar integração preexistente | Serviços e soluções → Integrações | Bling PDV aparece Ativo; não é o aplicativo alvo do piloto | Consulta; nenhuma mudança na integração | Navegação observada; sincronização não comprovada |
| Corrigir contexto CorePet | Empresa selecionada | Acesso corrigido para Atacadão das Rações Pet | Troca de contexto de acesso | Observado; nenhum cadastro ou produto alterado por essa conferência |
| Localizar SKU piloto | Central do iFood → Buscar produto existente | SKU 018631.1 encontrado como MGZ EXT CALOPSITAS E PERIQUIT PM13 900G | Consulta; nenhuma publicação | Confirmado na empresa correta |
| Conferir situação local inicial | Central do iFood | Produto inicialmente fora da seleção, estoque disponível, contribuição Não calculada e uma orientação | Consulta; nenhuma alteração salva naquele momento | Observado; preço e saldo numérico omitidos |
| Tentar abrir cadastro canônico | Ações → Editar no cadastro | Primeiro acesso redirecionou à página pública/login; campos não carregaram | Nenhum salvamento ou envio | Ocorrência inicial; sessão retomada posteriormente |
| Conferir cadastro após autenticação | Cadastro canônico do produto | EANs consistentes, UN, produto simples, embalagem 900 g, descrição e imagens com principal | Consulta; produto não salvo | Campos carregados e conferidos |
| Acessar aplicativo próprio | iFood Developer → Meus aplicativos | CorePet, Centralizado, Merchant, Parcialmente homologado | Consulta; nenhuma alteração | Confirmado; situação por módulo não inferida |
| Consultar categoria e módulos | Detalhes do aplicativo CorePet | GROCERIES; Order, Item, Picking, Events e Merchant selecionados; Promotion não selecionado | Consulta; nenhuma alteração | Seleção observada; não é prova de homologação individual |
| Conferir autorização inicial | Aplicativo CorePet → Permissões | Inicialmente nenhum merchant havia autorizado o aplicativo | Consulta | Situação anterior à solicitação e aprovação registradas abaixo |
| Preparar pedido de autorização | Permissões → Pedir autorização | Modal com ID/CNPJ e busca da loja antes da ação final | Inicialmente somente consulta | Preparação concluída; solicitação posterior registrada abaixo |
| Conferir identificação da loja | Portal do Parceiro → Configurações → Perfil da loja | Identificador localizado para a busca exata no Developer | Consulta; valor omitido do registro | Conferido antes da solicitação |
| Enviar solicitação CorePet | Developer → Permissões | Aceites e envio expressamente confirmados pelo responsável; Aguardando Ativação no Developer e Permissão pendente no Portal | Solicitação de autorização enviada | Não equivale a grant nem a envio de produto |
| Revisar concessão | Portal → Integrações → CorePet → Mais Ações → Permitir | Confirmação com Pedidos, Item, Eventos, Merchant e Termos de Uso | Revisão antes da concessão | Acessos e aceite final expressamente confirmados |
| Autorizar aplicativo | Confirmação → Autorizar | Resposta Integração autorizada; cartão CorePet Ativo | Autorização da loja concedida ao aplicativo CorePet | Concluído; conexão do ERP não comprovada |
| Pesquisar item remoto por nome | Gestão de Catálogo | Busca calopsitas sem filtro ativo/inativo não retornou item | Consulta; nenhuma alteração | Busca textual inconclusiva; consulta posterior por EAN registrada abaixo |
| Pesquisar item remoto por EAN | Gestão de Catálogo, sem filtro ativo/inativo; Em análise; Para cadastrar | Nenhum item retornado nessas consultas | Consulta; nenhuma alteração | Produto não localizado nessas consultas; ausência absoluta não comprovada |
| Corrigir identificação no ERP | Configurações → Integrações → Abrir integração iFood | Merchant ID corrigido para a loja autorizada e configuração salva desativada | Configuração local da integração alterada; nenhum envio de produto | Fonte, acréscimo e reserva preservados; valores omitidos |
| Testar conexão do ERP | Testar conexão | Duas tentativas falharam; diagnóstico da segunda chamada HTTP 502, internal_server_error, mensagem genérica | Teste pela tela; nenhum anúncio enviado | ERP Requer atenção; causa genérica inicialmente, diagnóstico posterior registrado abaixo |
| Diagnosticar servidor de produção | Consulta somente leitura expressamente autorizada | Runtime identificado com aplicativo centralizado de teste, diferente do CorePet de produção autorizado | Somente leitura; credenciais comparadas por booleanos, sem exibir valores | Divergência confirmada; last_error sanitizado indica loja não vinculada ao aplicativo usado |
| Conferir estado operacional agregado | Diagnóstico somente leitura | Escrita de catálogo e operações de pedidos habilitadas; polling desabilitado; uma configuração iFood e nenhuma ativa | Somente leitura; sem identificadores de empresas | Não comprova operação externa ou sincronização |
| Corrigir aplicativo no servidor | Manutenção expressamente autorizada após diagnóstico | Somente duas credenciais corrigidas; backend recriado com a mesma imagem; demais linhas preservadas | Manutenção operacional executada; sem deploy de código por essa ação | Banco, nginx e workers preservados; polling desligado e serviços saudáveis |
| Encerrar transporte temporário | Manutenção autorizada | Chave privada, payload criptografado e pasta temporária removidos; backup protegido fora do Git | Limpeza dos artefatos temporários da manutenção | Nenhum segredo em mídias ou no Git |
| Tentar selecionar produto na central | Central do iFood | Atualização não concluída durante deploy externo; recarga posterior confirmou Selecionados: 0 | Nenhuma seleção confirmada ou produto salvo até esse ponto | Preparação do SKU continua |
| Validar conexão após correção | Empresa correta → Configurações → Integrações → iFood → Testar conexão | Selo Conexão validada e mensagem Loja localizada e conexão validada no iFood. | Consulta de conexão bem-sucedida; sem envio de anúncio | Comprovado; opção de ativação da empresa segue desmarcada |
| Selecionar somente o piloto | Central do iFood → Selecionar para iFood | SKU 018631.1 selecionado; confirmação Produto selecionado, contador 1 e status Pronto para envio | Somente intenção local salva; demais campos preservados | Concluído; integração da empresa segue desativada e nada enviado ao iFood |
| Conferir orientação de rentabilidade | Central do iFood | Taxas desconhecidas mantêm uma orientação e contribuição Não calculada | Consulta | Nenhuma contribuição estimada comprovada |
| Conferir prévia inicial | Configurações → Integrações → iFood → Conferir produtos | Contador indicava um pronto; lista limitada sem SKU piloto e com seleção desabilitada | Consulta; nenhum envio de produto | Problema inicial, posteriormente corrigido no deploy registrado abaixo |
| Implementar correção da prévia em DEV | DEV, branch codex/ifood-piloto-publicacao | Produtos aptos antes do limite, preservando grupos e filtro de pendências | Implementação e testes antes do deploy registrado abaixo | 91 testes iFood aprovados, incluindo oito novos e doze no arquivo alterado |
| Revisar e concluir checks da correção | DEV e PR 1549, commit d42fbfacb | Revisão independente sem achados, Ruff, gate completo e 11 checks do PR aprovados | Nenhum envio | Concluído; release-check exit 0 |
| Conferir visualmente a prévia corrigida | DEV isolado 18083, empresa fictícia | Único apto apareceu primeiro e selecionado na prévia de 50, após 60 rejeitados na massa | Somente dados fictícios e rede interna | Comprovado; APIs de limites 1/50/200 e filtro only_issues também aprovadas |
| Conferir limite de permissão do dry-run | DEV isolado, usuário fictício | Dry-run legado negado com 403 por ausência da flag global is_admin | Permissões preservadas; nenhum envio | Não tratado como dry-run concluído nem como falha da correção da prévia |
| Publicar correção da prévia | Produção, a75cba5a1 | PR 1549 integrado e deploy oficial exit 0, após gate 552fc9b11 e oito checks obrigatórios aprovados | Código publicado; nenhum envio de produto | Cinco serviços saudáveis; API e watchdog OK |
| Conferir prévia e conexão após deploy | Produção, empresa correta | SKU piloto primeiro, selecionado e único habilitado na prévia de 50; conexão revalidada | Consulta; integração da empresa desativada | Comprovado; sem POST/PATCH de catálogo, reset, polling ou anúncio |
| Vincular produto existente | Fluxo ainda em validação | Nenhum vínculo criado | Não executado | Pendente |
| Solicitar envio de um item | Fluxo ainda em validação | Nenhuma solicitação enviada | Não executado | Pendente |
| Conferir publicação | CorePet, Portal e canal iFood | Nenhuma publicação conferida neste piloto | Não executado | Pendente |
| Validar estoque integrado | CorePet e iFood | Nenhum ciclo de atualização conferido | Não executado | Pendente |
| Planejar apuração financeira | Integração futura Financial | Separar estimativa de contribuição e apuração das cobranças efetivas com custos ERP | Nenhuma implementação ou cópia de dados financeiros privados | Pendente; exige escopo, implementação e homologação próprios |
| Consultar financeiro manual | Portal do Parceiro → Financeiro, setembro | Componentes de comissão, pagamento, promoção da loja e taxas ao consumidor distinguidos | Somente leitura; valores não reproduzidos | Disponibilidade manual comprovada; nenhuma integração Financial por API no CorePet |

## Inventário de evidências locais

| Arquivo | Origem | O que documenta | Restrição |
|---|---|---|---|
| `codex-clipboard-3e39bd5e-e433-403e-849e-880f98b46cda.png` | Anexo fornecido pelo usuário | Tela inicial do Gestor de Pedidos com a loja selecionada | Original fora do Git; revisar e anonimizar antes de qualquer uso público |
| `2026-10-23-ifood-corepet-modulos.png` | Captura da navegação assistida, fora do Git | Categoria e módulos selecionados do aplicativo CorePet | Sem credenciais; revisar antes de qualquer uso público |
| `2026-10-23-ifood-corepet-autorizacao-atacadao.png` | Captura da navegação assistida, fora do Git | Etapa de solicitação de autorização para a loja | Evidência operacional; revisar e anonimizar antes de qualquer uso público |
| `2026-10-23-ifood-corepet-permissao-pendente.png` | Captura da navegação assistida, fora do Git | Solicitação aguardando aprovação no Portal do Parceiro | Evidência operacional; revisar e anonimizar antes de qualquer uso público |
| `2026-10-23-ifood-corepet-aceite-final.png` | Captura da navegação assistida, fora do Git | Confirmação final dos acessos e termos apresentados | Evidência operacional; revisar e anonimizar antes de qualquer uso público |
| `2026-10-23-ifood-corepet-autorizado.png` | Captura da navegação assistida, fora do Git | Autorização concluída e integração CorePet ativa no Portal | Evidência operacional; revisar e anonimizar antes de qualquer uso público |
| `2026-10-23-ifood-corepet-conexao-requer-atencao.png` | Captura da navegação assistida, fora do Git | Estado Requer atenção após o teste de conexão do ERP | Evidência operacional; revisar e anonimizar antes de qualquer uso público |
| `2026-10-23-ifood-credentials-maintenance.jsonl` | Registro operacional da manutenção, fora do Git | Diagnóstico e manutenção autorizados, sem valores de credenciais | Registro restrito; conteúdo não reproduzido neste documento |
| `2026-10-23-ifood-corepet-conexao-validada.png` | Captura da navegação assistida, fora do Git | Selo e mensagem de conexão validada após a correção | Evidência operacional; revisar e anonimizar antes de qualquer uso público |
| `2026-10-23-ifood-sku018631-pronto-local.png` | Captura da navegação assistida, fora do Git | SKU piloto selecionado localmente e Pronto para envio | Evidência operacional; revisar e anonimizar antes de qualquer uso público |
| `2026-10-23-ifood-previa-prioridade-dev.png` | Captura da conferência visual no DEV isolado, fora do Git | Produto fictício apto priorizado e selecionado na prévia limitada | Dados fictícios; sem credenciais ou envio externo |
| `2026-10-23-ifood-previa-producao-sku018631.png` | Captura da conferência após deploy, fora do Git | SKU piloto primeiro e selecionado na prévia corrigida de produção | Evidência operacional; revisar e anonimizar antes de qualquer uso público |

As demais observações foram relatadas durante a navegação assistida. Nenhum
nome de captura é considerado existente sem o arquivo correspondente. Acrescentar
novas evidências ao inventário conforme forem produzidas, sem incluir os
arquivos originais neste repositório.

## Próximas conferências

- [x] Localizar o SKU `018631.1` no CorePet da empresa correta.
- [x] Retomar a autenticação no CorePet, confirmar a empresa e abrir os dados do
  produto para conferir identificação e pendências.
- [x] Conferir identificação, apresentação, descrição e imagens no cadastro,
  sem salvar o produto.
- [ ] Conferir identidade, apresentação, EAN e situação do produto no iFood.
- [x] Consultar o EAN sem filtro ativo/inativo e nas áreas Em análise e Para
  cadastrar, registrando somente que o produto não foi localizado nessas consultas.
- [ ] Determinar se o primeiro caso será vínculo/atualização de item existente
  ou criação de um item realmente ausente.
- [x] Conferir o aplicativo próprio CorePet no iFood Developer, sua categoria,
  seleção de módulos e situação geral de homologação.
- [x] Consultar a situação atual de autorização e localizar a identificação da
  loja na origem, sem reproduzir seu valor.
- [x] Conferir a loja na solicitação de autorização.
- [x] Concluir e comprovar a autorização da loja para o aplicativo CorePet,
  após confirmações expressas dos acessos e termos.
- [x] Corrigir o Merchant ID do ERP para o da loja autorizada e salvar a
  configuração desativada, preservando as demais regras.
- [x] Executar o teste de conexão pela tela e registrar a falha observada.
- [x] Obter autorização e executar diagnóstico somente leitura no servidor,
  sem exibir credenciais ou identificadores.
- [x] Identificar a divergência entre o aplicativo de teste usado pelo runtime
  e o CorePet de produção autorizado pela loja.
- [x] Obter autorização explícita para corrigir a configuração protegida e
  recriar somente o backend com a mesma imagem.
- [x] Executar a correção autorizada, sem registrar
  conteúdo de credenciais ou backups nos documentos.
- [x] Repetir o teste de conexão após a correção e comprovar o resultado.
- [x] Concluir a conferência da conexão do ERP com a mesma loja autorizada,
  mantendo a opção de ativação desmarcada.
- [x] Selecionar somente o SKU piloto para o canal e conferir Pronto para envio,
  preservando preço, regras e demais campos.
- [x] Conferir que a orientação de rentabilidade continua sem inventar taxas ou
  contribuição.
- [x] Implementar e testar em DEV a priorização de produtos aptos antes do
  limite, preservando grupos e filtro de pendências; 91 testes iFood aprovados.
- [x] Concluir revisão independente, lint/formato e gate completo da correção,
  aprovado no commit d42fbfacb, com os 11 checks do PR 1549 aprovados.
- [x] Conferir visualmente a prévia corrigida no DEV isolado e com dados
  fictícios, preservando as permissões e sem operação externa.
- [x] Publicar a correção da prévia pelo deploy oficial após as validações e
  autorização aplicáveis; produção no commit a75cba5a1.
- [x] Conferir em produção a prioridade e a seleção do SKU piloto, revalidar a
  conexão e manter a integração da empresa desativada, sem enviar produtos.
- [ ] Confirmar as permissões e a homologação efetivas do módulo necessário ao
  envio, sem inferi-las dos campos selecionados.
- [ ] Esclarecer o papel operacional da integração preexistente Bling PDV
  somente para evitar concorrência, sem usá-la para a conexão CorePet ou alterar
  seu estado.
- [ ] Definir os campos do teste e registrar a situação anterior.
- [ ] Preparar a prévia de somente um item, sem reset do catálogo.
- [ ] Registrar a decisão e a execução de vínculo, ativação ou envio somente
  quando essas etapas realmente ocorrerem.
- [ ] Distinguir solicitação aceita de publicação conferida.
- [ ] Validar estoque e demais rotinas em etapas próprias antes de automatizar
  os itens já publicados.
- [ ] Definir o escopo de Financial e a apuração posterior das cobranças do
  iFood com os custos ERP, sem confundir essa etapa futura com a margem estimada.

## Pendência de integração financeira

O piloto operacional atual não inclui o módulo **Financial**. A autorização do
aplicativo e a preparação de catálogo não comprovam acesso a conciliação,
taxas efetivas ou repasses. As taxas ainda desconhecidas não foram preenchidas
com valores inventados.

A consulta somente leitura ao Financeiro de setembro no Portal permitiu separar
os componentes de comissão, pagamento, promoção custeada pela loja e cobranças
ao consumidor. Nenhum valor é reproduzido aqui. A consulta manual não é evidência
de importação, conciliação ou apuração automática pelo CorePet.

As referências oficiais consultadas em 23/10/2026 confirmam Financial para
Groceries e homologação separada dos módulos operacionais:

- [Categorias e módulos disponíveis](https://developer.ifood.com.br/en-US/docs/getting-started/homologation/categories).
- [Homologação do módulo Financial](https://developer.ifood.com.br/en-US/docs/food/guides/modules/financial/homologation).

A comissão contratada serve como premissa da previsão; a cobrança efetiva exige
a conferência financeira posterior. Publicar pelo módulo Item não fornece uma
cotação de comissão ou taxas. [Endpoints oficiais do módulo Item](https://developer.ifood.com.br/en-US/docs/groceries/guides/modules/item/endpoints).

A proposta registrada é **contribuição estimada antes da venda** e **apuração
depois da venda**, combinando cobranças efetivas do iFood com os custos ERP
correspondentes, sem duplicar componentes ou tratar repasse como margem. Essa
proposta exige definição e validação próprias; não constitui funcionalidade
entregue neste piloto. Nenhum valor financeiro real ou extrato privado foi
incluído neste documento.

## Aprendizados para a Central de Ajuda

- Sempre começar pela empresa selecionada no CorePet e pela loja selecionada
  no iFood.
- Não concluir que um produto está ausente a partir de consulta em outra empresa.
- Diferenciar o catálogo de pet shop/mercado da área de Cardápio de restaurantes.
- Orientar a verificar itens existentes antes de criar anúncios novos.
- Não apresentar integrador ativo como prova de sincronização de preço/estoque.
- Nomear o aplicativo próprio CorePet como alvo da conexão, sem confundi-lo com
  integrações preexistentes inventariadas na loja.
- Separar seleção de módulos, homologação do aplicativo, solicitação de
  autorização e concessão pela loja; nenhuma dessas etapas comprova as outras.
- Separar as ações do integrador no Developer da aprovação do lojista no Portal
  do Parceiro; o lojista comum não precisa entrar na conta Developer do CorePet.
- Autorização do aplicativo e cartão Ativo no Portal não comprovam conexão do
  ERP, envio de produtos ou sincronização de estoque.
- Conferir o Merchant ID da configuração do ERP contra a mesma loja autorizada;
  durante a validação, preservar as regras existentes e manter a rotina desativada.
- Registrar Requer atenção e a resposta observada sem atribuir causa a um erro
  genérico antes de obter diagnóstico.
- Quando a autorização estiver ativa e a conexão falhar, o suporte deve conferir
  se o ERP usa o mesmo aplicativo CorePet que a loja autorizou. A verificação
  técnica deve preservar segredos e ser separada do manual destinado ao lojista.
- Não concluir ausência de produto somente por busca textual sem conferir seu
  identificador e sua apresentação.
- Se a edição redirecionar ao login, retomar a autenticação e só registrar a
  conferência do cadastro depois que seus campos carregarem.
- Explicar que seleção e preparação local não comprovam publicação.
- Confirmar separadamente o contador de produtos aptos e a presença do produto
  piloto na prévia antes de qualquer envio. Um contador correto não comprova que
  a seleção da prévia esteja operacional.
- Inserir somente passos de conexão e envio que tenham sido executados e
  conferidos. Não prometer botões ou estados ainda inexistentes na interface.

O guia público permanece em rascunho. Não foi criado artigo na Central de Ajuda,
item de Novidades ou material público com os dados deste piloto.
