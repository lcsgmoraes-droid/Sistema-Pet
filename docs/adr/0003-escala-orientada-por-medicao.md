# ADR-0003 — Escala orientada por medição

- Estado: Aceito
- Data: 2026-08-27
- Responsável: plataforma CorePet

## Contexto

Quantidade de código, uso de IA, escolha por monólito ou sensação de rapidez não
provam capacidade. Também não é seguro descobrir o limite gerando carga sobre
empresas em produção.

## Decisão

A evolução de capacidade seguirá evidência progressiva:

1. definir jornadas, indicadores e metas internas propostas;
2. executar carga autenticada somente leitura em homologação isolada;
3. aumentar volume, concorrência e massa fictícia em degraus controlados;
4. medir sucesso, p50, p95, p99, throughput, banco e recursos do host;
5. formar linha de base operacional antes de aprovar SLO ou faixa comercial;
6. otimizar ou escalar vertical/horizontalmente somente após localizar o gargalo.

O executor autenticado bloqueia os domínios de produção de forma incondicional.
Produção recebe apenas probes operacionais leves pelo fluxo autorizado; carga
autenticada pertence à homologação ou a um staging isolado.

## Alternativas consideradas

- **Prometer 100 ou 1.000 empresas por estimativa:** rejeitada por não considerar
  usuários simultâneos, dados, rotas e integrações.
- **Teste pesado em produção:** rejeitado pelo risco a empresas e dados reais.
- **Adicionar servidores antes de medir:** rejeitado porque pode aumentar custo
  sem corrigir consulta, pool, fila ou integração que seja o gargalo real.

## Consequências

- Resultados locais são linha de base, não SLA nem dimensionamento definitivo.
- Cada relatório registra amostra, concorrência, critérios e ambiente.
- Acesso autenticado usa credenciais efêmeras fora do Git e nunca imprime token.
- Escritas de venda, estoque, finanças e cadastro não entram na carga padrão.
- Staging remoto passa a ser necessário quando a estabilidade do teste local ou
  a faixa de clientes justificar infraestrutura dedicada.

## Gatilhos para revisão

- necessidade de carga com webhooks, filas ou escrita idempotente controlada;
- mais de uma pessoa precisar homologar ou repetir testes continuamente;
- aproximação de uma nova faixa comercial de empresas ativas;
- SLO rompido ou saturação de CPU, memória, banco, pool ou armazenamento.

## Evidências relacionadas

- `docs/TESTE_CAPACIDADE_SEGURO.md`
- `docs/SLOS_INDICADORES_JORNADAS.md`
- `scripts/capacity_authenticated.py`
- `scripts/capacity_smoke.py`
