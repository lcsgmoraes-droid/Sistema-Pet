"""
ABA 7: Sistema Tributário - Cálculo de Impostos
Suporta: Simples Nacional, Lucro Presumido, Lucro Real, MEI
"""

from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import date

from app.ia.aba7_extrato_models import ConfiguracaoTributaria


class CalculadoraTributaria:
    """Calcula impostos baseado no regime tributário configurado"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def obter_configuracao(self, usuario_id: int) -> Optional[ConfiguracaoTributaria]:
        """Busca configuração tributária do usuário"""
        return (
            self.db.query(ConfiguracaoTributaria)
            .filter(ConfiguracaoTributaria.usuario_id == usuario_id)
            .first()
        )
    
    def calcular_impostos(
        self,
        usuario_id: int,
        receita_bruta: float,
        receita_liquida: float,
        lucro_operacional: float
    ) -> Dict:
        """
        Calcula todos os impostos baseado no regime
        
        Returns:
            {
                'impostos': float,
                'detalhamento': {
                    'simples_nacional': float,
                    'irpj': float,
                    'csll': float,
                    'pis': float,
                    'cofins': float,
                    'iss': float,
                    'icms': float
                },
                'aliquota_efetiva': float,
                'regime': str
            }
        """
        config = self.obter_configuracao(usuario_id)
        
        if not config:
            # Sem configuração, estima 8% (Simples Nacional médio)
            impostos_estimados = receita_bruta * 0.08
            return {
                'impostos': impostos_estimados,
                'detalhamento': {'estimado': impostos_estimados},
                'aliquota_efetiva': 8.0,
                'regime': 'nao_configurado'
            }
        
        if config.regime == 'simples_nacional':
            return self._calcular_simples_nacional(config, receita_bruta)
        
        elif config.regime == 'lucro_presumido':
            return self._calcular_lucro_presumido(config, receita_bruta)
        
        elif config.regime == 'lucro_real':
            return self._calcular_lucro_real(config, receita_bruta, lucro_operacional)
        
        elif config.regime == 'mei':
            return self._calcular_mei(config, receita_bruta)
        
        else:
            # Fallback
            impostos_estimados = receita_bruta * 0.08
            return {
                'impostos': impostos_estimados,
                'detalhamento': {'estimado': impostos_estimados},
                'aliquota_efetiva': 8.0,
                'regime': config.regime
            }
    
    def _calcular_simples_nacional(
        self,
        config: ConfiguracaoTributaria,
        receita_bruta: float
    ) -> Dict:
        """
        Simples Nacional - Alíquota única progressiva
        Anexo I (Comércio): 4% a 19%
        """
        # Usa alíquota efetiva configurada
        aliquota = config.aliquota_efetiva_simples or 8.54  # Média do Anexo I
        impostos = receita_bruta * (aliquota / 100)
        
        return {
            'impostos': impostos,
            'detalhamento': {
                'simples_nacional': impostos
            },
            'aliquota_efetiva': aliquota,
            'regime': 'simples_nacional',
            'anexo': config.anexo_simples,
            'faixa': config.faixa_simples
        }
    
    def _calcular_lucro_presumido(
        self,
        config: ConfiguracaoTributaria,
        receita_bruta: float
    ) -> Dict:
        """
        Lucro Presumido - Cálculo separado de cada tributo
        - PIS: 0.65% sobre faturamento
        - COFINS: 3% sobre faturamento
        - IRPJ: 15% sobre lucro presumido (8% da receita para comércio)
        - CSLL: 9% sobre lucro presumido
        """
        # PIS e COFINS
        pis = receita_bruta * (config.aliquota_pis or 0.0065)
        cofins = receita_bruta * (config.aliquota_cofins or 0.03)
        
        # Lucro presumido
        presuncao = config.presuncao_lucro_percentual or 8.0  # 8% para comércio
        lucro_presumido = receita_bruta * (presuncao / 100)
        
        # IRPJ (15% + adicional de 10% acima de R$ 60k trimestral)
        irpj_base = lucro_presumido * (config.aliquota_irpj or 0.15)
        
        # Adicional de IRPJ (10% sobre o que exceder R$ 60k no trimestre)
        limite_trimestral = 60000
        if lucro_presumido > limite_trimestral:
            irpj_adicional = (lucro_presumido - limite_trimestral) * (config.aliquota_adicional_irpj or 0.10)
            irpj = irpj_base + irpj_adicional
        else:
            irpj = irpj_base
        
        # CSLL
        csll = lucro_presumido * (config.aliquota_csll or 0.09)
        
        # ISS (se aplicável - para serviços)
        iss = 0
        if config.incluir_iss_dre and config.aliquota_iss:
            iss = receita_bruta * (config.aliquota_iss / 100)
        
        # ICMS (se aplicável - estadual)
        icms = 0
        if config.incluir_icms_dre and config.aliquota_icms:
            icms = receita_bruta * (config.aliquota_icms / 100)
        
        total_impostos = pis + cofins + irpj + csll + iss + icms
        aliquota_efetiva = (total_impostos / receita_bruta * 100) if receita_bruta > 0 else 0
        
        return {
            'impostos': total_impostos,
            'detalhamento': {
                'pis': pis,
                'cofins': cofins,
                'irpj': irpj,
                'csll': csll,
                'iss': iss,
                'icms': icms
            },
            'aliquota_efetiva': aliquota_efetiva,
            'regime': 'lucro_presumido',
            'lucro_presumido': lucro_presumido
        }
    
    def _calcular_lucro_real(
        self,
        config: ConfiguracaoTributaria,
        receita_bruta: float,
        lucro_operacional: float
    ) -> Dict:
        """
        Lucro Real - Cálculo sobre lucro efetivo
        Usado por empresas com margem baixa ou prejuízo
        """
        # PIS e COFINS (não cumulativo)
        pis = receita_bruta * 0.0165  # 1.65%
        cofins = receita_bruta * 0.076  # 7.6%
        
        # IRPJ e CSLL sobre lucro real
        lucro_real = max(0, lucro_operacional)  # Não tributa prejuízo
        
        irpj_base = lucro_real * 0.15
        
        # Adicional de IRPJ (10% acima de R$ 60k trimestral)
        limite_trimestral = 60000
        if lucro_real > limite_trimestral:
            irpj_adicional = (lucro_real - limite_trimestral) * 0.10
            irpj = irpj_base + irpj_adicional
        else:
            irpj = irpj_base
        
        csll = lucro_real * 0.09
        
        # ISS/ICMS
        iss = 0
        if config.incluir_iss_dre and config.aliquota_iss:
            iss = receita_bruta * (config.aliquota_iss / 100)
        
        icms = 0
        if config.incluir_icms_dre and config.aliquota_icms:
            icms = receita_bruta * (config.aliquota_icms / 100)
        
        total_impostos = pis + cofins + irpj + csll + iss + icms
        aliquota_efetiva = (total_impostos / receita_bruta * 100) if receita_bruta > 0 else 0
        
        return {
            'impostos': total_impostos,
            'detalhamento': {
                'pis': pis,
                'cofins': cofins,
                'irpj': irpj,
                'csll': csll,
                'iss': iss,
                'icms': icms
            },
            'aliquota_efetiva': aliquota_efetiva,
            'regime': 'lucro_real',
            'lucro_real': lucro_real
        }
    
    def _calcular_mei(
        self,
        config: ConfiguracaoTributaria,
        receita_bruta: float
    ) -> Dict:
        """
        MEI - Valor fixo mensal
        R$ 67,00 (comércio/indústria) ou R$ 71,00 (serviços)
        """
        # MEI tem limite de R$ 81.000/ano
        if receita_bruta > 81000 / 12:  # Se ultrapassar no mês
            # Desenquadramento automático, usar Simples
            return self._calcular_simples_nacional(config, receita_bruta)
        
        # Valor fixo do DAS-MEI
        valor_mensal = 71.00  # Média (pode ser configurável)
        
        return {
            'impostos': valor_mensal,
            'detalhamento': {
                'das_mei': valor_mensal
            },
            'aliquota_efetiva': (valor_mensal / receita_bruta * 100) if receita_bruta > 0 else 0,
            'regime': 'mei'
        }
    
    def salvar_configuracao(
        self,
        usuario_id: int,
        regime: str,
        **kwargs
    ) -> ConfiguracaoTributaria:
        """Cria ou atualiza configuração tributária"""
        config = self.obter_configuracao(usuario_id)
        
        if not config:
            config = ConfiguracaoTributaria(usuario_id=usuario_id)
            self.db.add(config)
        
        # Atualizar campos
        config.regime = regime
        
        # Simples Nacional
        if 'anexo_simples' in kwargs:
            config.anexo_simples = kwargs['anexo_simples']
        if 'faixa_simples' in kwargs:
            config.faixa_simples = kwargs['faixa_simples']
        if 'aliquota_efetiva_simples' in kwargs:
            config.aliquota_efetiva_simples = kwargs['aliquota_efetiva_simples']
        
        # Lucro Presumido
        if 'presuncao_lucro_percentual' in kwargs:
            config.presuncao_lucro_percentual = kwargs['presuncao_lucro_percentual']
        if 'aliquota_irpj' in kwargs:
            config.aliquota_irpj = kwargs['aliquota_irpj']
        if 'aliquota_adicional_irpj' in kwargs:
            config.aliquota_adicional_irpj = kwargs['aliquota_adicional_irpj']
        if 'aliquota_csll' in kwargs:
            config.aliquota_csll = kwargs['aliquota_csll']
        if 'aliquota_pis' in kwargs:
            config.aliquota_pis = kwargs['aliquota_pis']
        if 'aliquota_cofins' in kwargs:
            config.aliquota_cofins = kwargs['aliquota_cofins']
        
        # ICMS/ISS
        if 'estado' in kwargs:
            config.estado = kwargs['estado']
        if 'aliquota_icms' in kwargs:
            config.aliquota_icms = kwargs['aliquota_icms']
        if 'incluir_icms_dre' in kwargs:
            config.incluir_icms_dre = kwargs['incluir_icms_dre']
        if 'aliquota_iss' in kwargs:
            config.aliquota_iss = kwargs['aliquota_iss']
        if 'incluir_iss_dre' in kwargs:
            config.incluir_iss_dre = kwargs['incluir_iss_dre']
        
        self.db.commit()
        self.db.refresh(config)
        return config
    
    def estimar_economia_regime(
        self,
        usuario_id: int,
        receita_bruta: float,
        lucro_operacional: float
    ) -> Dict:
        """
        Compara todos os regimes e sugere o mais econômico
        
        Returns:
            {
                'simples_nacional': {'impostos': 1000, 'aliquota': 8.5},
                'lucro_presumido': {'impostos': 1200, 'aliquota': 10.2},
                'lucro_real': {'impostos': 800, 'aliquota': 6.8},
                'recomendacao': 'lucro_real',
                'economia_anual_estimada': 2400
            }
        """
        config = self.obter_configuracao(usuario_id)
        
        if not config:
            # Criar config temporária com valores padrão
            config = ConfiguracaoTributaria(
                usuario_id=usuario_id,
                regime='simples_nacional',
                aliquota_efetiva_simples=8.54,
                presuncao_lucro_percentual=8.0,
                aliquota_irpj=0.15,
                aliquota_csll=0.09,
                aliquota_pis=0.0065,
                aliquota_cofins=0.03
            )
        
        # Simular cada regime
        config_temp = config
        
        # Simples Nacional
        config_temp.regime = 'simples_nacional'
        simples = self._calcular_simples_nacional(config_temp, receita_bruta)
        
        # Lucro Presumido
        config_temp.regime = 'lucro_presumido'
        presumido = self._calcular_lucro_presumido(config_temp, receita_bruta)
        
        # Lucro Real
        config_temp.regime = 'lucro_real'
        real = self._calcular_lucro_real(config_temp, receita_bruta, lucro_operacional)
        
        # Encontrar o melhor
        opcoes = {
            'simples_nacional': simples['impostos'],
            'lucro_presumido': presumido['impostos'],
            'lucro_real': real['impostos']
        }
        
        melhor_regime = min(opcoes, key=opcoes.get)
        menor_imposto = opcoes[melhor_regime]
        maior_imposto = max(opcoes.values())
        economia_mensal = maior_imposto - menor_imposto
        economia_anual = economia_mensal * 12
        
        return {
            'simples_nacional': {
                'impostos': simples['impostos'],
                'aliquota': simples['aliquota_efetiva']
            },
            'lucro_presumido': {
                'impostos': presumido['impostos'],
                'aliquota': presumido['aliquota_efetiva']
            },
            'lucro_real': {
                'impostos': real['impostos'],
                'aliquota': real['aliquota_efetiva']
            },
            'recomendacao': melhor_regime,
            'economia_mensal_estimada': economia_mensal,
            'economia_anual_estimada': economia_anual,
            'regime_atual': config.regime if self.obter_configuracao(usuario_id) else None
        }
