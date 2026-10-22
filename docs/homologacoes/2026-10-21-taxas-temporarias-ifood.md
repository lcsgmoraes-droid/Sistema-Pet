# Homologação DEV — taxas temporárias iFood

| Campo | Valor |
|---|---|
| Data / executor | 2026-10-21 / Codex |
| Responsável de negócio | Lucas |
| Branch | `codex/ifood-taxas-simulacao` |
| Ambiente | `corepet-ifood-dev`, `http://127.0.0.1:18081` |
| Massa | Produto fictício 2, `DEV-IFOOD-3KG`, custo R$ 60, preço salvo R$ 150, estoque 4 |

| Cenário | Resultado |
|---|---|
| Taxas temporárias e preço R$ 100 no navegador | Comissões 15%/25%, pagamento 3%, tributos 4%, despesa R$ 2 e meta 30%: contribuição própria R$ 16/16% e iFood R$ 6/6% |
| Restaurar taxas da loja | Mantém R$ 100 digitado; entrega iFood volta a R$ 10/10% com taxas salvas |
| Pendências da simulação | Meta não atendida gera aviso; simular regular R$ 100 também aponta a promoção cadastrada de R$ 120 incompatível, sem alterar a oferta real |
| Reabrir tela | Volta ao salvo R$ 150 e taxas reais; contribuição própria R$ 61,50/41% |
| Persistência após API e navegador | GET de regras e produto idênticos à baseline; nenhum botão de gravar acionado |
| Contratos backend | 102 aprovados; tenant, acesso somente leitura, zero/nulo/herança, limites, promoção e nenhuma escrita/chamada externa |
| Regressão frontend | 67 aprovados; 19 do hook incluem taxas, restauração, concorrência e recuperação após PUT |
| Qualidade | Ruff, ESLint, Prettier focados, build local e Dockerfiles oficiais aprovados |
| Revisão independente | Nenhum bug acionável encontrado |

As taxas reais salvas continuam 10%/20%, pagamento 2%, tributos 5%, despesa R$ 3 e
meta 30%. Nenhum preço, custo, estoque, promoção ou regra foi alterado por esta
homologação. Não houve operação em produção.

Flags de escrita, operação e polling iFood falsas no DEV. Imagens oficiais
reconstruídas no Compose isolado, preservando volumes e o ambiente da porta
18080. Backend/frontend saudáveis após a reconstrução.

Evidências locais do chat: `ifood-taxas-dev-baseline.json`,
`ifood-taxas-dev-http-result.json` e capturas da calculadora em DEV. São arquivos
fora do Git, sem credenciais. Comandos reproduzíveis:

```powershell
npm --prefix frontend run test:ifood
cd backend
.\.venv\Scripts\python.exe -m pytest tests/unit/test_ifood_management.py tests/unit/test_ifood_catalog_contract.py tests/unit/test_ifood_routes_contract.py tests/unit/test_ifood_orders_contract.py tests/unit/test_ifood_client_contract.py -q
```

Decisão técnica: aprovada para revisão do Lucas em DEV. Aceite de negócio e
publicação em produção permanecem etapas futuras; envio de anúncios não faz
parte desta entrega.
