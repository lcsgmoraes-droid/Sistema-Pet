# Gestão de incidentes e sustentação

Atualizado em: 2026-08-26

Status: fonte oficial para registrar, classificar, tratar e aprender com falhas
do Sistema Pet. Este processo vale para produção, integrações, dados,
segurança e jornadas críticas do usuário.

O objetivo é restaurar o serviço com segurança, preservar evidências e evitar
recorrência. Uma correção rápida não substitui causa raiz, teste de regressão ou
ação preventiva.

## Responsabilidades

Enquanto não houver uma equipe técnica formal, os papéis são:

| Papel | Responsabilidade |
|---|---|
| Responsável pelo negócio | Confirmar impacto e prioridade, definir a comunicação externa e aceitar risco residual. |
| Coordenador do incidente | Manter o registro único, a classificação, a linha do tempo, os responsáveis e a cadência de atualização. |
| Executor técnico | Investigar com evidências, conter, implementar pelo fluxo Git/PR, validar e documentar causa raiz. Pode ser a IA. |
| Operador de produção | Executar somente ações autorizadas e auditáveis no ambiente produtivo. |
| Usuário homologador | Confirmar a recuperação da jornada afetada sem expor dados pessoais desnecessários. |

Uma pessoa pode acumular papéis, mas cada papel deve aparecer no registro. Toda
ação em produção continua exigindo autorização explícita e separada.

## Classificação e primeira resposta

Primeira resposta significa confirmar o recebimento, registrar o impacto,
classificar e informar a próxima atualização. Não significa prazo garantido de
resolução.

| Nível | Critério | Exemplos | Primeira resposta alvo |
|---|---|---|---|
| P0 crítico | Indisponibilidade ampla, acesso entre empresas, perda/corrupção de dados, risco de segurança ou jornada principal bloqueada para vários clientes sem alternativa segura. | Sistema fora do ar; suspeita cross-tenant; venda indisponível para várias empresas. | Até 2 horas corridas. |
| P1 alto | Jornada crítica bloqueada para uma empresa ou integração crítica degradada, sem alternativa operacional segura. | Venda ou estoque bloqueado; pedidos externos sem processamento. | Até 4 horas úteis. |
| P2 normal | Falha parcial, pontual ou com alternativa segura e impacto controlado. | Relatório inconsistente com operação principal disponível. | Até 1 dia útil. |
| P3 baixo | Defeito cosmético, baixa frequência ou impacto pequeno que não bloqueia trabalho. | Texto, alinhamento ou comportamento secundário. | Até 2 dias úteis. |
| Melhoria | Pedido novo, preferência ou ampliação de escopo sem falha do comportamento acordado. | Novo relatório ou personalização. | Registrar para priorização; não há prazo automático de entrega. |

Essas metas são operacionais e não constituem SLA contratual. P0 aberto bloqueia
novo piloto, expansão relevante ou publicação não relacionada até a contenção e
a avaliação de risco.

## Estados do incidente

```text
detectado -> reconhecido -> em contenção -> em correção -> recuperado -> encerrado
                                  |                |
                                  +-> monitorado <-+
```

- **Detectado:** primeiro sinal verificável do problema.
- **Reconhecido:** registro criado, severidade inicial e responsável definidos.
- **Em contenção:** ação reduz impacto sem esconder a causa.
- **Em correção:** causa provável conhecida e mudança segura em preparação.
- **Recuperado:** serviço e jornada voltaram, ainda sob observação.
- **Encerrado:** evidências, causa raiz e ações preventivas foram registradas.

A severidade pode subir ou descer conforme as evidências. Registrar a mudança e
o motivo; nunca rebaixar apenas para cumprir meta.

## Fluxo obrigatório

1. **Detectar e registrar.** Criar uma cópia de
   `docs/templates/REGISTRO_INCIDENTE.md` com identificador
   `INC-AAAAMMDD-NN` e horário de Brasília.
2. **Confirmar o impacto.** Registrar jornadas, quantidade de empresas ou
   usuários afetados, período e alternativa segura. Não copiar payload bruto.
3. **Classificar e assumir.** Definir severidade, coordenador, executor técnico
   e horário da próxima atualização.
4. **Preservar evidências.** Guardar `request_id`, `correlation_id`, eventos Ops,
   versão implantada e intervalo de logs conforme
   `docs/RETENCAO_LOGS_AUDITORIA.md`.
5. **Conter.** Reduzir o impacto com ação reversível. Feature flag, isolamento
   de job, pausa de integração ou rollback só podem seguir o procedimento
   autorizado correspondente.
6. **Diagnosticar.** Separar sintoma, causa imediata e causa raiz. Registrar
   hipóteses descartadas e evidências, sem usar produção como laboratório.
7. **Corrigir.** Usar branch, teste de regressão, PR e gates normais. Correção
   emergencial não autoriza commit direto nem deploy informal.
8. **Recuperar e validar.** Conferir health/watchdog, jornada afetada,
   isolamento por tenant, filas e integrações relevantes.
9. **Comunicar.** Informar fato, impacto, alternativa e próxima atualização sem
   especular ou expor dados de outro cliente.
10. **Encerrar e aprender.** Completar causa raiz, métricas, risco residual e
    ações preventivas com responsável e prazo.

## Comunicação

| Situação | Atualização mínima |
|---|---|
| P0 com impacto ativo | Ao reconhecer e, depois, no máximo a cada 60 minutos ou quando o estado mudar. |
| P1 com impacto ativo | Ao reconhecer, quando houver contenção e ao recuperar. |
| P2/P3 | No reconhecimento e no encerramento, salvo mudança relevante. |
| Segurança, privacidade ou dados | Comunicação restrita; envolver avaliação jurídica/privacidade antes de afirmar alcance ou responsabilidade. |

Cada atualização deve dizer: o que está confirmado, impacto conhecido,
contenção/alternativa, próximo passo e horário da próxima atualização. Não
prometer prazo de resolução sem evidência.

## Causa raiz e melhoria estrutural

Todo P0 exige análise de causa raiz. P1 também exige quando houver recorrência,
risco de dados/segurança ou ausência de alternativa segura.

Uma correção deve virar ação estrutural quando qualquer condição ocorrer:

- o mesmo sintoma ou a mesma causa aparece duas vezes em 30 dias;
- um P0 ou P1 revelou falta de teste, alerta, rollback ou documentação;
- houve risco cross-tenant, exposição, corrupção ou perda de dados;
- a recuperação dependeu de comando manual não padronizado;
- o tempo de detecção ou recuperação ficou acima da meta interna;
- a mesma causa pode afetar outros módulos, tenants ou integrações;
- a contenção permanecer necessária após a recuperação.

A ação estrutural deve ter prioridade, responsável, prazo, critério de aceite e
PR/issue rastreável. O incidente só pode ser encerrado com a ação registrada;
ela pode ser executada depois quando o risco residual estiver aceito pelo
responsável do negócio.

## Métricas

Registrar os horários em uma única linha do tempo:

- **MTTD:** detecção menos início estimado do impacto;
- **MTTA:** reconhecimento menos detecção;
- **MTTC:** contenção menos detecção;
- **MTTR:** recuperação menos detecção;
- **recorrência:** incidentes com mesma causa em até 30 dias.

Mensalmente, revisar quantidade por severidade, MTTD, MTTA, MTTR, recorrências,
metas de primeira resposta não atendidas e ações preventivas atrasadas. Enquanto
o volume for pequeno, uma tabela no histórico Git é suficiente; não é necessário
contratar outra ferramenta.

As metas de MTTD/MTTR só devem ser formalizadas depois de uma linha de base real.
Roadmaps históricos não constituem SLA nem prova de desempenho atual.

## Segurança, privacidade e retenção

- Nunca registrar senha, token, cookie, certificado, chave ou payload pessoal
  desnecessário.
- Usar tenant, horário e identificadores técnicos; anonimizar nomes quando
  possível.
- Suspeita de acesso entre empresas, vazamento ou corrupção é P0 até prova em
  contrário.
- Incidente de segurança, fraude, disputa ou dado pode exigir `legal hold`; não
  purgar evidências relacionadas antes do encerramento formal.
- Rotação de credenciais segue `docs/SEGURANCA_ROTACAO_SSH_SECRETS.md`.
- Decisões LGPD ou comunicação regulatória exigem avaliação jurídica externa.

## Critério de encerramento

Um incidente fica encerrado somente quando:

- serviço e jornada afetada estão validados;
- health/watchdog e componentes relacionados estão saudáveis;
- impacto, período e empresas afetadas estão delimitados;
- causa raiz ou melhor explicação baseada em evidência está registrada;
- correção, versão, PR, deploy e rollback estão rastreáveis quando aplicáveis;
- comunicação final foi feita quando necessária;
- ações preventivas possuem responsável, prazo e aceite de risco residual;
- retenção normal ou `legal hold` está decidido;
- nenhuma evidência contém segredo ou dado pessoal desnecessário.

## Rotina de sustentação

- Revisar incidentes abertos e ações vencidas semanalmente.
- Revisar métricas e recorrências mensalmente.
- Revisar esta política trimestralmente ou após todo P0.
- Transformar dúvidas repetidas em Ajuda/treinamento e defeitos repetidos em
  teste automatizado ou melhoria estrutural.
- Manter o painel Ops, alertas, backups, rollback e homologação como capacidades
  exercitadas, não apenas documentadas.

