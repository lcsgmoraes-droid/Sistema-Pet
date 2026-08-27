# ADR-0001 — Monólito modular como arquitetura principal

- Estado: Aceito
- Data: 2026-08-27
- Responsável: plataforma CorePet

## Contexto

O CorePet atende várias empresas e reúne vendas, estoque, financeiro,
ecommerce, veterinário e integrações. O estágio atual precisa de simplicidade
operacional, transações confiáveis e evolução frequente sem multiplicar deploys,
filas e pontos de falha.

## Decisão

Manter o backend como monólito modular em FastAPI, com PostgreSQL como banco
transacional principal. Os domínios ficam separados internamente por rotas,
schemas, serviços, consultas e eventos. Processamento pesado ou assíncrono pode
ter worker próprio sem transformar automaticamente cada módulo em microsserviço.

Uma extração para serviço separado só ocorre quando medição e operação provarem
ao menos uma necessidade: escala independente, isolamento de falha, requisito
regulatório ou ciclo de deploy realmente autônomo.

## Alternativas consideradas

- **Microsserviços imediatos:** rejeitados porque aumentariam rede, observação,
  consistência distribuída, deploys e custo antes de existir gargalo medido.
- **Reescrita total:** rejeitada porque elevaria o risco para empresas ativas e
  descartaria comportamento já testado.
- **Código sem fronteiras internas:** rejeitado porque dificulta manutenção e
  cria acoplamento mesmo dentro de um único processo.

## Consequências

- Deploy, transações e diagnóstico permanecem simples para o estágio atual.
- Refatorações devem ser incrementais e preservar contratos públicos.
- O processo principal ainda compartilha recursos e domínio de falha; health,
  workers, timeouts e métricas precisam mostrar quando isso deixa de ser viável.
- Um módulo novo não pode espalhar regras por `main.py` ou componentes de tela.

## Gatilhos para revisão

- um domínio consumir recursos de forma desproporcional e repetível;
- falha de uma integração afetar jornadas não relacionadas apesar dos limites;
- necessidade de deploy independente gerar bloqueio operacional frequente;
- exigência legal ou de segurança demandar isolamento físico;
- testes demonstrarem que escala horizontal do monólito não atende a meta.

## Evidências relacionadas

- `docs/ARQUITETURA.md`
- `docs/auditorias/estrutura-geral-definition-of-done.md`
- `docker-compose.prod.yml`
- `backend/app/main.py`
