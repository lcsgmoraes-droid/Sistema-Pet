# Catálogo operacional CorePet para EcommerceAI

`GET /integracoes/ecommerceai/catalog/marketplace-products` é uma leitura autenticada pelo token da conexão existente, com escopo `catalog:read`. Não altera produto, custo, reservas, estoque, conexão ou comando da integração. A rota anterior `/catalog/products` permanece compatível.

Parâmetros: `page` (a partir de 1), `page_size` (1–200; padrão 100) e `q` opcional (até 200 caracteres; busca literal em nome, SKU ou código de barras). A ordem é o ID estável do produto. A lista contém somente produtos não excluídos do tenant conectado, inclusive inativos identificados por `active=false`.

Resposta: `schema_version="corepet.catalog.v1"`, `tenant_id`, `generated_at` UTC, `page`, `page_size`, `total`, `has_next`, `products`.

Cada produto contém `corepet_id` string, `sku`, `name`, `description`, `barcode`, `unit`, `product_type`, `active`, `sellable`, `updated_at` UTC ou null, `media` e `warnings`. `sellable` identifica um produto físico vendável e ativo; não comprova prontidão para publicação nem disponibilidade positiva.

- `cost`: `amount` decimal-string ou null, `currency="BRL"`, `status="ready"|"unavailable"`, `reason` ou null. É o custo corrente cadastral positivo de produtos simples/variações sem composição. Zero cadastral é ambíguo por ser o default e fica indisponível; não significa custo gratuito confirmado. Não se recalcula histórico financeiro.
- `stock`: `physical`, `reserved`, `available` como decimal-string ou null; `status`, `reason`, `owner_tenant_id`. Para estoque padrão local, `physical` representa o saldo operacional em `estoque_atual`; `available=max(physical-reserved,0)` segue a listagem CorePet. Não é um inventário bruto anterior a bloqueios: bloqueios de validade já retirados do saldo não são descontados novamente.
- `media`: imagens principal/galeria ordenadas e deduplicadas, com URL HTTP(S) absoluta e `type="image"`. Caminhos locais `/uploads/` usam a URL pública configurada. URLs inválidas são omitidas com aviso. Esta versão não cadastra nem exporta vídeos.

## Limites explícitos desta entrega

Kits, variações com composição, produtos pai, serviços e granel não recebem cálculo pronto. Estoque separado de ecommerce e saldo de produto local compartilhado com outra empresa retornam `unavailable` com motivo. Catálogo recebido de outras empresas por compartilhamento ainda não é importado por esta rota; a ausência de produto aqui não revoga acesso nem comprova exclusão em outro catálogo.

Reservas leem os itens ativos pelo serviço central e somam em Decimal exatamente os itens cujas identidades foram validadas, sem reler ou resolver novamente o conjunto. Kits físicos reservam apenas o próprio estoque conforme a regra central. Uma reserva virtual com composição integralmente identificada na mesma empresa mantém indisponível apenas o saldo dos componentes atingidos (`reservation_composition_unsupported`); produtos simples sem relação com essa composição preservam o cálculo das suas próprias reservas. O saldo do kit continua indisponível: esta entrega não habilita cálculo ou publicação de kits.

Identidade ausente ou ambígua e quantidade inválida mantêm o bloqueio de reservas para toda a página (`reservation_identity_unverified`). Composição virtual vazia, componente ausente, excluído ou de outra empresa, quantidade de componente inválida e composição aninhada também bloqueiam toda a página (`reservation_composition_unverified`), pois não é possível delimitar com segurança os produtos afetados. Essas verificações abrangem as reservas da empresa, inclusive produtos fora da página ou busca solicitada. Falha de banco/consulta retorna HTTP 503, nunca mapa de reservas vazio apresentado como sucesso. Não há fallback ao Bling.

Em PostgreSQL, cada requisição usa uma sessão dedicada com isolamento `REPEATABLE READ` e transação `READ ONLY`, configurados antes da autenticação e da primeira consulta. Produto, reservas, identidades e configuração são lidos na mesma visão, sem alterar o isolamento global nem reaproveitar objetos já carregados pela requisição. A sessão fecha com rollback e não permite escrita. Os testes isolados em SQLite preservam a sessão injetada.

Esta é uma leitura consistente por página, não um snapshot congelado entre várias requisições, nem um feed incremental. `updated_at` é da linha do produto e não garante capturar alterações em imagens ou reservas. O consumidor deve revisar cargas completas e frescor; não publicar saldo ou aplicar pedidos com base apenas em `status="ready"`.

O comando Bling/EcommerceAI é escolhido no EcommerceAI. Nenhum seletor, mudança de autoridade, processamento de pedidos, publicação em marketplace ou envio de saldo ao Bling é criado por esta entrega.
