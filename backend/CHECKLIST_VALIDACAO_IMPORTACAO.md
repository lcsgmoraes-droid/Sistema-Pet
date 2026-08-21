# Checklist da importacao SimplesVet

O checklist antigo continha comandos sem filtro por empresa e resultados de uma
importacao historica. Ele nao representa a estrutura multitenant atual.

Antes de aplicar:

- [ ] empresa e usuario do plano estao corretos;
- [ ] simulacao terminou sem falha fatal;
- [ ] contagens e rejeicoes foram revisadas;
- [ ] plano ainda esta dentro das 24 horas;
- [ ] arquivos nao foram editados depois da simulacao;
- [ ] ambiente de destino foi conferido;
- [ ] em producao, backup e autorizacao explicita foram confirmados.

Depois de aplicar:

- [ ] recibo `simplesvet-applied-<plan_id>.json` foi gerado;
- [ ] contagens aplicadas foram comparadas com a simulacao;
- [ ] clientes, produtos, pets e vendas foram conferidos pela empresa correta;
- [ ] nenhuma outra empresa apresentou mudanca de contagem;

Procedimento completo:

- [`docs/IMPORTACAO_SIMPLESVET_SEGURA.md`](../docs/IMPORTACAO_SIMPLESVET_SEGURA.md)
