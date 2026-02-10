# 🚀 Roadmap: Evolução do Cálculo de Margem para Enterprise

## 📋 Status Atual: ✅ FUNCIONAL

O sistema atual está **correto e funcional** para operação imediata.

Este documento mapeia **evoluções futuras** necessárias quando o sistema crescer.

---

## 🚨 PONTO 1: Regime de Imposto

### ✅ Implementação Atual (Simplificada - OK)

```python
imposto_valor = total_venda * (aliquota_imposto / 100)
```

**Funciona perfeitamente para:**
- Empresas no Simples Nacional (alíquota fixa)
- Cálculo rápido no PDV
- Estimativa confiável

### 🔮 Evolução Futura (Necessária)

**Imposto real depende de:**

#### 1. NCM (Nomenclatura Comum do Mercosul)
```python
# Exemplo: Ração para cães
produto.ncm = "2309.1000"
# NCM define alíquota ICMS e possível substituição tributária
```

#### 2. Tipo de Produto
```python
# Medicamentos: isenção ou redução
# Alimentos: alíquota diferenciada
# Serviços: ISS ao invés de ICMS
```

#### 3. Substituição Tributária (ICMS-ST)
```python
# Produto já vem com imposto pago pelo fabricante
# Revenda não paga ICMS novamente
# MVA (Margem de Valor Agregado) pode aplicar
```

#### 4. Empresa
```python
# Simples Nacional: 7%
# Lucro Presumido: 11.33%
# Lucro Real: alíquota por produto
```

#### 5. Canal de Venda
```python
# Venda presencial: ICMS normal
# Venda e-commerce interestadual: DIFAL
# Exportação: isenção
```

### 🛠️ Arquitetura Preparada

**Fase 1: PDV (Atual)**
```python
# Usa alíquota estimada configurável
aliquota_imposto_padrao = 7.0
```

**Fase 2: Integração Fiscal (Futuro)**
```python
def calcular_imposto_produto(
    produto_id: int,
    valor_venda: float,
    uf_origem: str,
    uf_destino: str,
    empresa_id: int
) -> Dict:
    """
    Busca alíquota real do sistema fiscal
    Considera NCM, ST, DIFAL, MVA, etc
    """
    # Chama módulo fiscal (a desenvolver)
    fiscal_service = FiscalService()
    return fiscal_service.calcular_tributos(
        ncm=produto.ncm,
        valor=valor_venda,
        uf_origem=uf_origem,
        uf_destino=uf_destino,
        regime_empresa=empresa.regime_tributario
    )
```

### 📝 Ação Recomendada

1. **Hoje**: Continuar usando `aliquota_imposto_padrao`
2. **Quando crescer**: 
   - Adicionar campo `ncm` na tabela `produtos`
   - Adicionar campo `regime_tributario` na tabela `empresas`
   - Criar tabela `tributos_por_ncm`
   - Integrar com API fiscal (Sefaz, NFe)
3. **No PDV**: Aceitar parâmetro opcional `imposto_calculado_fiscal`
   ```python
   imposto_valor = imposto_calculado_fiscal or (total_venda * aliquota_padrao / 100)
   ```

---

## 🚨 PONTO 2: Base de Cálculo da Comissão

### ✅ Implementação Atual (Sobre Total - OK)

```python
comissao_calculada = total_venda * (comissao_percentual / 100)
```

**Calcula sobre:** Valor total (produtos + entrega)

### 🔮 Evolução Futura (Parametrizável)

**Bases possíveis:**

#### 1. Sobre Total com Entrega (atual)
```python
base = valor_produtos + taxa_entrega_receita_empresa
comissao = base * 2%  # R$ 205 * 2% = R$ 4,10
```

#### 2. Sobre Produtos Sem Entrega
```python
base = valor_produtos  # Sem entrega
comissao = base * 2%   # R$ 190 * 2% = R$ 3,80
```

#### 3. Sobre Produtos Sem Desconto
```python
base = subtotal  # Antes do desconto
comissao = base * 2%  # R$ 200 * 2% = R$ 4,00
```

#### 4. Sobre Margem (Lucro)
```python
base = valor_produtos - custo_produtos
comissao = base * 10%  # R$ 70 * 10% = R$ 7,00
```

#### 5. Produtos Específicos
```python
# Comissão apenas em produtos category='nutrição'
# Produtos de higiene não geram comissão
```

#### 6. Faixas Progressivas
```python
if base < 500:
    comissao = base * 1%
elif base < 1000:
    comissao = base * 2%
else:
    comissao = base * 3%
```

### 🛠️ Arquitetura Preparada

**Adicionar à empresa_config_geral:**
```python
class EmpresaConfigGeral:
    # ... campos existentes ...
    
    # Nova configuração
    comissao_base = Column(String(50), default='total_venda')
    # Valores: 'total_venda', 'produtos_sem_entrega', 
    #          'produtos_sem_desconto', 'margem'
    
    comissao_percentual_vendedor = Column(Numeric(5,2), default=2.0)
```

**Função preparada:**
```python
def calcular_comissao_vendedor(
    db: Session,
    tenant_id: str,
    subtotal: float,
    desconto: float,
    taxa_entrega_receita: float,
    custo_produtos: float
) -> float:
    """
    Calcula comissão baseada na configuração da empresa
    """
    config = db.query(EmpresaConfigGeral).filter(...).first()
    
    if config.comissao_base == 'total_venda':
        base = (subtotal - desconto) + taxa_entrega_receita
    elif config.comissao_base == 'produtos_sem_entrega':
        base = subtotal - desconto
    elif config.comissao_base == 'produtos_sem_desconto':
        base = subtotal
    elif config.comissao_base == 'margem':
        base = (subtotal - desconto) - custo_produtos
    
    return base * (config.comissao_percentual_vendedor / 100)
```

### 📝 Ação Recomendada

1. **Hoje**: Aceitar `comissao_percentual` e `comissao_valor` como parâmetros
2. **Futuro próximo**:
   - Adicionar campo `comissao_base` na config
   - Default: `'total_venda'` (comportamento atual)
3. **Futuro médio**:
   - Comissão por produto/categoria
   - Regras de comissão por vendedor
4. **Futuro distante**:
   - Múltiplos vendedores na mesma venda
   - Comissão gerente + vendedor
   - Metas e bônus

---

## 🚨 PONTO 3: Parcelamento e Momento do Custo

### ✅ Implementação Atual (Taxa Imediata - OK)

```python
# Cartão 3x com taxa 4%
taxa_valor = total_venda * 0.04  # R$ 205 * 4% = R$ 8,20
```

**Funciona para:** DRE por competência (reconhece custo no momento da venda)

### 🔮 Evolução Futura (Fluxo de Caixa)

#### Cenário 1: Recebimento à Vista com Taxa Antecipada
```
Venda: R$ 205 em 3x
Operadora antecipa: R$ 196,80 (descontou R$ 8,20)
Empresa recebe: hoje
```

**DRE (Competência):**
```
Receita: R$ 205,00
Taxa cartão: -R$ 8,20
Líquido: R$ 196,80
```

**Fluxo Caixa:**
```
Entrada hoje: R$ 196,80
```

#### Cenário 2: Recebimento Parcelado Sem Antecipação
```
Venda: R$ 205 em 3x
Cliente paga: R$ 68,33 por mês
Operadora cobra: R$ 2,73 de taxa por parcela
Empresa recebe: 3 parcelas de R$ 65,60
```

**DRE (Competência):**
```
Receita: R$ 205,00 (hoje)
Taxa cartão: -R$ 8,20 (hoje)
```

**Fluxo Caixa:**
```
Mês 1: +R$ 65,60
Mês 2: +R$ 65,60
Mês 3: +R$ 65,60
```

#### Cenário 3: Antecipação Parcial
```
Venda: R$ 205 em 12x
Taxa normal: 8%
Taxa antecipação: 12% (maior!)
```

**Se NÃO antecipar:**
```
Recebe: 12x R$ 15,73 = R$ 188,76
Taxa: R$ 16,24 (8%)
```

**Se antecipar:**
```
Recebe hoje: R$ 180,40
Taxa: R$ 24,60 (12%)
Paga R$ 8,36 a mais pela antecipação!
```

### 🛠️ Arquitetura Necessária

**Adicionar campos no registro da venda:**
```python
class Venda:
    # ... campos existentes ...
    
    # Financeiro
    taxa_prevista = Column(Numeric(10,2))      # Taxa teórica
    taxa_efetiva = Column(Numeric(10,2))       # Taxa real cobrada
    valor_liquido_previsto = Column(Numeric(10,2))
    valor_liquido_efetivo = Column(Numeric(10,2))
    
    # Recebimento
    antecipado = Column(Boolean, default=False)
    taxa_antecipacao = Column(Numeric(5,2))
    
    # Data recebimento efetivo
    recebido_em = Column(DateTime)
```

**Criar tabela de parcelas:**
```python
class VendaParcela:
    id = Column(Integer, primary_key=True)
    venda_id = Column(Integer, ForeignKey('vendas.id'))
    numero_parcela = Column(Integer)
    valor_parcela = Column(Numeric(10,2))
    valor_liquido = Column(Numeric(10,2))
    taxa_parcela = Column(Numeric(10,2))
    vencimento = Column(Date)
    recebido_em = Column(DateTime)
    status = Column(String(20))  # 'pendente', 'recebido', 'antecipado'
```

**Integração com operadora:**
```python
class IntegracaoOperadora:
    """
    Busca extrato da operadora e reconcilia
    """
    def buscar_extrato(self, data_inicio, data_fim):
        # API Stone, Rede, Cielo, etc
        pass
    
    def reconciliar_venda(self, venda_id, valor_liquido_real):
        venda = db.query(Venda).get(venda_id)
        venda.valor_liquido_efetivo = valor_liquido_real
        venda.taxa_efetiva = venda.total - valor_liquido_real
```

### 📝 Ação Recomendada

1. **Hoje**: 
   - PDV calcula `taxa_prevista` (correto)
   - Registra no momento da venda
2. **Curto prazo**:
   - Criar tabela `vendas_parcelas`
   - Registrar previsão de recebimento
3. **Médio prazo**:
   - Desenvolver módulo de conciliação bancária
   - Integrar com API das operadoras
   - Marcar parcelas como "recebidas"
4. **Longo prazo**:
   - Dashboard de fluxo de caixa projetado vs realizado
   - Análise de custo de antecipação
   - Otimização automática (quando vale antecipar)

---

## 🚨 PONTO 4: Custo Operacional Flexível

### ✅ Implementação Atual (Valor Informado - OK)

```python
custo_operacional_entrega = 8.00  # Informado manualmente
```

**Funciona para:** Estimativa rápida e consistente

### 🔮 Evolução Futura (Cálculo Automático)

#### 1. Custo Médio Automático
```python
# Calcula média dos últimos 30 dias
total_custos = sum(entregas.custo_real)
quantidade = len(entregas)
custo_medio = total_custos / quantidade
```

#### 2. Custo por Quilômetro
```python
# Integração com Google Maps
distancia = calcular_distancia(empresa, cliente)  # 5.2 km
custo_por_km = 1.50  # R$ 1,50/km
custo_operacional = distancia * custo_por_km  # R$ 7,80
```

#### 3. Custo por Região
```python
regioes = {
    'centro': 5.00,
    'zona_norte': 8.00,
    'zona_sul': 10.00,
    'outro_municipio': 15.00
}
custo_operacional = regioes[cliente.regiao]
```

#### 4. Custo por Veículo
```python
veiculos = {
    'moto': {
        'combustivel_por_km': 0.30,
        'manutencao_mensal': 200.00,
        'depreciacao_mensal': 150.00
    },
    'carro': {
        'combustivel_por_km': 0.60,
        'manutencao_mensal': 400.00,
        'depreciacao_mensal': 300.00
    }
}

# Custo real considerando todos os fatores
distancia = 5.2
combustivel = distancia * veiculos['moto']['combustivel_por_km']  # R$ 1,56
manutencao_proporcional = 200 / 300  # 300 entregas/mês estimadas
depreciacao_proporcional = 150 / 300
custo_total = combustivel + manutencao_proporcional + depreciacao_proporcional
```

#### 5. Custo por Tempo
```python
# Entregador ganha R$ 2.000/mês
# Trabalha 220h/mês
custo_hora = 2000 / 220  # R$ 9,09/h

tempo_estimado = calcular_tempo_rota(origem, destino)  # 25 min
custo_tempo = (tempo_estimado / 60) * custo_hora  # R$ 3,79

custo_combustivel = distancia * 0.30  # R$ 1,56

custo_total = custo_tempo + custo_combustivel  # R$ 5,35
```

#### 6. Custo Dinâmico (ML/IA)
```python
# Machine Learning baseado em histórico
modelo = TreinaCustoEntrega(
    historico_entregas=ultimos_6_meses
)

custo_previsto = modelo.prever(
    distancia=5.2,
    horario='14:30',
    dia_semana='segunda',
    clima='chuva',
    regiao='zona_norte',
    veiculo='moto'
)
# Output: R$ 12,50 (chuva aumenta custo)
```

### 🛠️ Arquitetura Preparada

**Tabela de configuração:**
```python
class ConfiguracaoEntrega:
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(36))
    
    # Método de cálculo
    metodo_calculo = Column(String(50), default='fixo')
    # Valores: 'fixo', 'medio', 'por_km', 'por_regiao', 
    #          'por_veiculo', 'por_tempo'
    
    # Custos fixos
    custo_fixo = Column(Numeric(10,2), default=8.00)
    
    # Custos por km
    custo_por_km = Column(Numeric(10,2))
    
    # Custos por região (JSON)
    custos_por_regiao = Column(JSON)
    
    # Custos por veículo (JSON)
    custos_por_veiculo = Column(JSON)
```

**Função flexível:**
```python
def calcular_custo_operacional_entrega(
    db: Session,
    tenant_id: str,
    cliente_endereco: str = None,
    veiculo: str = None,
    horario: datetime = None
) -> float:
    """
    Calcula custo operacional baseado na configuração
    """
    config = db.query(ConfiguracaoEntrega).filter(...).first()
    
    if config.metodo_calculo == 'fixo':
        return float(config.custo_fixo)
    
    elif config.metodo_calculo == 'por_km':
        distancia = calcular_distancia_google_maps(
            empresa_endereco,
            cliente_endereco
        )
        return distancia * float(config.custo_por_km)
    
    elif config.metodo_calculo == 'por_regiao':
        regiao = identificar_regiao(cliente_endereco)
        return config.custos_por_regiao.get(regiao, 8.00)
    
    elif config.metodo_calculo == 'por_veiculo':
        custo_veiculo = config.custos_por_veiculo.get(veiculo)
        distancia = calcular_distancia(...)
        return calcular_custo_veiculo(distancia, custo_veiculo)
    
    # Default
    return 8.00
```

### 📝 Ação Recomendada

1. **Hoje**: 
   - Aceitar `custo_operacional_entrega` como parâmetro
   - Usar valor fixo (R$ 8)
2. **Curto prazo**:
   - Criar tabela `configuracao_entrega`
   - Adicionar opção de custo fixo configurável
3. **Médio prazo**:
   - Implementar cálculo por região
   - Implementar cálculo por km (Google Maps)
4. **Longo prazo**:
   - Histórico de custos reais
   - Custo médio automático
   - ML para previsão de custos
5. **Futuro distante**:
   - Otimização de rotas
   - Agendamento inteligente
   - Precificação dinâmica de entrega

---

## 🎯 Roadmap de Implementação

### Fase 1: PDV Básico (✅ ATUAL)
**Status**: Implementado e funcional

- [x] Cálculo de margem com todos os custos
- [x] Imposto simplificado (alíquota fixa)
- [x] Comissão sobre total da venda
- [x] Taxa de pagamento por parcela
- [x] Custo operacional fixo
- [x] Distribuição de taxa de entrega

**Pronto para produção!**

### Fase 2: Configurações Avançadas (3-6 meses)
**Quando**: Sistema estiver rodando e com feedback dos usuários

- [ ] Campo `comissao_base` configurável
- [ ] Campo `metodo_calculo_entrega` configurável
- [ ] Custos por região (tabela simples)
- [ ] Tabela `vendas_parcelas` para controle de recebimento
- [ ] Campo `ncm` nos produtos

### Fase 3: Integração Fiscal (6-12 meses)
**Quando**: Volume justificar complexidade

- [ ] Tabela `tributos_por_ncm`
- [ ] Integração com Sefaz
- [ ] Cálculo ICMS-ST
- [ ] Cálculo DIFAL (e-commerce)
- [ ] Geração de XML NFe
- [ ] Envio automático de notas

### Fase 4: Conciliação Financeira (12-18 meses)
**Quando**: Múltiplas formas de pagamento e volume alto

- [ ] Integração APIs operadoras (Stone, Rede, Cielo)
- [ ] Reconciliação bancária automática
- [ ] Controle de parcelas recebidas vs previstas
- [ ] Dashboard fluxo de caixa
- [ ] Análise de variação (taxa prevista vs efetiva)

### Fase 5: Inteligência (18-24 meses)
**Quando**: Dados históricos suficientes

- [ ] Machine Learning para custo de entrega
- [ ] Previsão de demanda
- [ ] Otimização de rotas
- [ ] Precificação dinâmica
- [ ] Análise de rentabilidade por produto/cliente/região

---

## 📊 Decisões de Design

### ✅ O que está certo hoje

1. **Separação de responsabilidades**
   - `pdv_indicadores.py`: Cálculo puro
   - `pdv_indicadores_routes.py`: API REST
   - Configurações: `empresa_config_geral`

2. **Parâmetros flexíveis**
   - Aceita valores calculados externamente
   - Não força lógica rígida
   - Permite override

3. **Valores default sensatos**
   - Imposto: 7% (Simples Nacional mais comum)
   - Comissão: sobre total
   - Custo entrega: informado

### 🎯 Preparação arquitetural

1. **Banco de dados extensível**
   - Campos JSON para configurações complexas
   - Tabelas de apoio fáceis de adicionar
   - Não precisa migração pesada

2. **API retrocompatível**
   - Novos parâmetros = opcionais
   - Comportamento padrão = atual
   - Clientes antigos continuam funcionando

3. **Lógica isolada**
   - Fácil adicionar `calcular_imposto_fiscal()`
   - Fácil adicionar `calcular_comissao_regras()`
   - Fácil adicionar `calcular_custo_entrega_inteligente()`

---

## 🏆 Conclusão

### Para hoje:
✅ Sistema está **correto, funcional e pronto para produção**

### Para amanhã:
🎯 Arquitetura **permite todas as evoluções** sem refatoração pesada

### Filosofia:
> "Começa simples. Escala quando necessário. Não quando antecipado."

---

## 📚 Referências

- [pdv_indicadores.py](backend/app/utils/pdv_indicadores.py) - Implementação atual
- [empresa_config_geral_models.py](backend/app/empresa_config_geral_models.py) - Modelo de configuração
- [CALCULO_MARGEM_COMPLETO.md](CALCULO_MARGEM_COMPLETO.md) - Documentação funcional
- [LOGICA_TAXA_ENTREGA.md](LOGICA_TAXA_ENTREGA.md) - Lógica de distribuição

---

**Versão**: 1.0  
**Data**: Fevereiro 2026  
**Tipo**: Roadmap Técnico  
**Status**: Planejamento  
