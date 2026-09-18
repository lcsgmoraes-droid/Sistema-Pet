---
tipo: base
atualizado: 2026-09-12
---

# Pendências

Tudo que depende de conhecimento humano para ser confirmado. Ver [[README]], [[Matriz-de-Riscos]].

## Segurança (prioridade alta — ver [[Vulnerabilidades]])

- [ ] Confirmar se `StoneConfig.conciliacao_password_enc` está em uso real em produção; se sim, auditar o caminho de cifragem (código não localizado nesta análise).
- [ ] Decidir sobre reativar/implementar MFA (schema já suporta, fluxo real não verifica).
- [ ] Confirmar topologia real de deploy (quantos processos/réplicas de backend) para dimensionar o impacto do rate limiting in-memory.
- [ ] Confirmar se logs em nível DEBUG rodam em produção (exposição de e-mail de usuário).
- [ ] Auditar entropia/expiração do token de rastreamento público de entrega (`/rastreio/:token`).
- [ ] Confirmar profundidade de validação do webhook Asaas (assinatura vs. token estático).
- [ ] Decidir o destino do webhook legado `POST /pagarme` (aposentar ou formalizar).

## Arquitetura e produto

- [ ] Esclarecer a relação entre `intnfe/` (ativação/CSC) e `nfe/`+`nfe_routes.py` (emissão via SEFAZ) — são sistemas complementares por função ou um é legado do outro?
- [ ] Confirmar se há plano de migrar a emissão fiscal de "via Bling" para "via IntNFe nativo" e em que prazo.
- [ ] Confirmar se o reaproveitamento da entidade `Cliente` para fornecedor/entregador/funcionário é definitivo ou candidato a separação futura.
- [ ] Confirmar se há (ou há plano de) unificação entre `Venda` (PDV) e `Pedido` (e-commerce).
- [ ] Confirmar governança do Catálogo Mestre global de produtos vs. catálogo próprio de cada tenant (quem edita o quê).
- [ ] Atualizar `docs/ARQUITETURA.md` oficial para incluir o worker do catálogo mestre e os jobs in-process hoje não mencionados ali.

## Integrações

- [ ] Confirmar se `FIREBASE_SERVER_KEY`/`FIREBASE_PROJECT_ID` (presentes no `.env.example`) ainda são usados ou são legado substituído por Expo Push.
- [ ] Confirmar se há implementação real de providers de IA alternativos (Groq, Google AI) além da variável de ambiente reservada.
- [ ] Confirmar comportamento de indisponibilidade prolongada do Mercado Pago (sem fila de retry durável confirmada).

## Infraestrutura e CI/CD

- [ ] Confirmar diretamente nas configurações do GitHub as regras exatas de branch protection da `main` (só documentado internamente, não auditável via código).
- [ ] Confirmar se existe CODEOWNERS ou processo equivalente de revisão por área (não encontrado no repositório).
- [ ] Confirmar se há WAF na frente do Nginx em produção.
- [ ] Confirmar RPO/RTO formal de backup (rotina existe, meta de tempo de recuperação não encontrada no código).

## Funcionalidades não aprofundadas nesta fase (ver [[Matriz-de-Cobertura]])

- [ ] Dashboard — agregação de dados de múltiplas áreas, não documentado em detalhe.
- [ ] Lembretes — ligado a recorrência de produto, não aprofundado.
- [ ] Calculadora de Ração — não aprofundada.
- [ ] Cadastros auxiliares (cargos, departamentos, marcas, bancos, formas de pagamento) — não aprofundados individualmente.
- [ ] RH/Funcionários — não aprofundado.
- [ ] Configurações (fiscal, parâmetros gerais, grupos de empresas, custo da moto) — não aprofundado.
- [ ] Alertas do gestor — não aprofundado.
- [ ] Painel `/ops` (plataforma/staff da CorePet) — autenticação separada confirmada, funcionalidade interna não mapeada.
- [ ] Aplicativo mobile (`app-mobile/src/`) — fora do escopo desta rodada, que focou backend + frontend web.

## Negócio

- [ ] Confirmar regras exatas de percentual/faixa de comissão por vendedor/categoria.
- [ ] Confirmar regras de repasse financeiro ao veterinário parceiro.
- [ ] Confirmar regra de inadimplência/negativação de contas a receber, se existir.
