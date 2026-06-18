# -*- coding: utf-8 -*-
"""
Serviço de Classificação Inteligente de Rações
Auto-classifica produtos baseado no nome usando padrões e palavras-chave

Versionamento:
- v1.0.0 (2026-02-14): Versão inicial com 6 categorias (espécie, linha, porte, fase, tratamento, sabor)
"""

import re
from typing import Dict, List, Optional, Tuple


class ClassificadorRacao:
    """
    Classifica automaticamente produtos de ração baseado no nome
    Extrai: espécie, linha, porte, fase, tratamento, sabor e peso
    
    Atributos:
        VERSION: Versão do algoritmo de classificação
    """
    
    VERSION = "v1.0.0"  # Versionamento para auditoria e evolução
    
    # Padrões de Espécie
    ESPECIES = {
        "Cães": [
            r"\bcachorro\b",
            r"\bc[ãa]es\b",
            r"\bdog\b",
            r"\bdogs\b",
            r"\bcanin[oe]\b",
            r"\bpuppy\b",
            r"\bfilhote.*c[ãa]o\b",
        ],
        "Gatos": [
            r"\bgato\b",
            r"\bgatos\b",
            r"\bcat\b",
            r"\bcats\b",
            r"\bfelin[oe]\b",
            r"\bkitten\b",
            r"\bfilhote.*gato\b",
        ],
        "Pássaros": [
            r"\bp[áa]ssaro\b",
            r"\bp[áa]ssaros\b",
            r"\baves\b",
            r"\bbird\b",
            r"\bbirds\b",
            r"\bcalopsita\b",
            r"\bperiquito\b",
            r"\bcanário\b",
            r"\bpapagaio\b",
        ],
        "Roedores": [
            r"\broedor\b",
            r"\broedores\b",
            r"\bhamster\b",
            r"\bcoelho\b",
            r"\bpor\s*quinho\b",
            r"\bchinchila\b",
        ],
        "Peixes": [
            r"\bpeixe\b",
            r"\bpeixes\b",
            r"\baqua.*peixe\b",
            r"\bornamental\b",
        ],
    }
    
    # Padrões de Linha/Categoria da Ração
    LINHAS_RACAO = {
        "Super Premium": [
            r"\bsuper\s*premium\b",
            r"\bsuper-premium\b",
            r"\bhigh\s*premium\b",
            r"\bgourmet\b",
            r"\bultrapremium\b",
            r"\bultra\s*premium\b",
        ],
        "Premium Special": [
            r"\bpremium\s*special\b",
            r"\bpremium\s*especial\b",
            r"\bespecial\s*premium\b",
            r"\bspecial\s*premium\b",
        ],
        "Premium": [
            r"\bpremium\b(?!\s*(special|especial))",  # Premium mas não "Premium Special"
            r"\bhigh\s*quality\b",
            r"\balta\s*qualidade\b",
        ],
        "Standard": [
            r"\bstandard\b",
            r"\btradicional\b",
            r"\beconomic[oa]\b",
            r"\bpopular\b",
            r"\bbasic[oa]\b",
            r"\bclassic[oa]\b",
        ],
    }
    
    # Padrões de Porte
    PORTES = {
        "Pequeno": [
            r"\bradulto\s+mini\b",
            r"\bmini\b",
            r"\bmini\s+adulto\b",
            r"\bminiature\b",
            r"\bpequeno\s+porte\b",
            r"\bsmall\b",
            r"\bsmall\s+breed\b",
            r"\bra[çc]as\s+pequenas\b",
        ],
        "Médio": [
            r"\bm[ée]dio\s+porte\b",
            r"\bmedium\b",
            r"\bmedium\s+breed\b",
            r"\bra[çc]as\s+m[ée]dias\b",
        ],
        "Grande": [
            r"\bgrande\s+porte\b",
            r"\blarge\b",
            r"\blarge\s+breed\b",
            r"\bra[çc]as\s+grandes\b",
            r"\bmaxi\b",
        ],
        "Gigante": [
            r"\bgigante\b",
            r"\bgiant\b",
            r"\bgiant\s+breed\b",
            r"\bra[çc]as\s+gigantes\b",
        ],
        "Todos": [
            r"\btodos\s+os\s+portes\b",
            r"\btodas\s+as\s+ra[çc]as\b",
            r"\ball\s+breeds\b",
            r"\ball\s+sizes\b",
        ],
    }
    
    # Padrões de Fase/Público
    FASES = {
        "Filhote": [
            r"\bfilhote\b",
            r"\bpuppy\b",
            r"\bjunior\b",
            r"\bjr\b",
            r"\bkitten\b",
            r"\bgrowth\b",
            r"\bstarter\b",
        ],
        "Adulto": [
            r"\badultos?\b",  # Adulto ou Adultos
            r"\badult\b",
            r"\bad\b",
        ],
        "Senior": [
            r"\bsenior\b",
            r"\bmatured\b",
            r"\b\+7\b",
            r"\b\+8\b",
            r"\bidoso\b",
        ],
        "Gestante": [
            r"\bgestante\b",
            r"\bpregnant\b",
            r"\blactante\b",
            r"\bmother\b",
        ],
        "Todos": [
            r"\btodos\b",
            r"\ball\s+ages\b",
            r"\ball\s+life\s+stages\b",
        ],
    }
    
    # Padrões de Tratamento/Condição Especial
    TRATAMENTOS = {
        "Obesidade": [
            r"\bobesidade\b",
            r"\blight\b",
            r"\bweight\s+control\b",
            r"\bweight\s+management\b",
            r"\bfitness\b",
            r"\bfit\b",
            r"\bslim\b",
        ],
        "Alergia": [
            r"\bhipoalerg[êe]nico\b",
            r"\bhypoallergenic\b",
            r"\balergia\b",
            r"\ballerg\w*\b",
        ],
        "Sensível": [
            r"\bsens[íi]vel\b",
            r"\bsensitive\b",
            r"\bstomach\b",
            r"\bdigest\w*\s+care\b",
        ],
        "Digestivo": [
            r"\bdigestivo\b",
            r"\bdigestive\b",
            r"\bdigest\b",
            r"\bgastrointestinal\b",
            r"\bgi\b",
        ],
        "Urinário": [
            r"\burin[áa]rio\b",
            r"\burinary\b",
            r"\burinary\s+care\b",
        ],
        "Renal": [
            r"\brenal\b",
            r"\bkidney\b",
            r"\bnephro\b",
        ],
        "Cardíaco": [
            r"\bcardíaco\b",
            r"\bcardiac\b",
            r"\bheart\b",
            r"\bcardio\b",
        ],
        "Dermatológico": [
            r"\bdermat\w+\b",
            r"\bskin\b",
            r"\bpele\b",
            r"\bhair\b",
            r"\bpelo\b",
        ],
    }
    
    # Padrões de Sabor/Proteína
    SABORES = {
        "Frango": [r"\bfrango\b", r"\bchicken\b", r"\bgalinha\b"],
        "Carne": [r"\bcarne\b", r"\bbeef\b", r"\bbovina\b", r"\bbovino\b"],
        "Peixe": [r"\bpeixe\b", r"\bfish\b", r"\bsalm[ãa]o\b", r"\bsalmon\b", r"\batum\b", r"\btuna\b"],
        "Cordeiro": [r"\bcordeiro\b", r"\blamb\b"],
        "Peru": [r"\bperu\b", r"\bturkey\b"],
        "Pato": [r"\bpato\b", r"\bduck\b"],
        "Vegetariano": [r"\bvegetariano\b", r"\bvegetarian\b", r"\bveg\b"],
        "Soja": [r"\bsoja\b", r"\bsoy\b"],
        "Mix": [r"\bmix\b", r"\bmisto\b", r"\bvariado\b"],
    }
    
    def __init__(self):
        """Inicializa o classificador compilando os regex patterns"""
        self.especies_compiled = {k: [re.compile(p, re.IGNORECASE) for p in v] for k, v in self.ESPECIES.items()}
        self.linhas_compiled = {k: [re.compile(p, re.IGNORECASE) for p in v] for k, v in self.LINHAS_RACAO.items()}
        self.portes_compiled = {k: [re.compile(p, re.IGNORECASE) for p in v] for k, v in self.PORTES.items()}
        self.fases_compiled = {k: [re.compile(p, re.IGNORECASE) for p in v] for k, v in self.FASES.items()}
        self.tratamentos_compiled = {k: [re.compile(p, re.IGNORECASE) for p in v] for k, v in self.TRATAMENTOS.items()}
        self.sabores_compiled = {k: [re.compile(p, re.IGNORECASE) for p in v] for k, v in self.SABORES.items()}
    
    def extrair_peso(self, nome: str) -> Optional[float]:
        """
        Extrai o peso da embalagem do nome do produto
        Exemplos: "15kg", "10 kg", "1.5kg", "500g"
        """
        # Padrão para kg
        match_kg = re.search(r'(\d+(?:[.,]\d+)?)\s*kg', nome, re.IGNORECASE)
        if match_kg:
            peso_str = match_kg.group(1).replace(',', '.')
            return float(peso_str)
        
        # Padrão para g (converte para kg)
        match_g = re.search(r'(\d+(?:[.,]\d+)?)\s*g\b', nome, re.IGNORECASE)
        if match_g:
            peso_str = match_g.group(1).replace(',', '.')
            return float(peso_str) / 1000
        
        return None
    
    def _classificar_categoria(self, nome: str, patterns_dict: Dict[str, List]) -> List[str]:
        """
        Classifica nome em uma categoria usando dicionário de patterns
        Retorna lista de matches encontrados
        """
        matches = []
        nome_lower = nome.lower()
        
        for categoria, patterns in patterns_dict.items():
            for pattern in patterns:
                if pattern.search(nome_lower):
                    matches.append(categoria)
                    break  # Já encontrou, não precisa testar outros patterns desta categoria
        
        return matches if matches else None
    
    def classificar(self, nome: str, peso_atual: Optional[float] = None) -> Dict:
        """
        Classifica produto baseado no nome
        
        Args:
            nome: Nome do produto
            peso_atual: Peso já cadastrado (opcional, não sobrescreve se existir)
        
        Returns:
            Dict com: especie_indicada, linha_racao, porte_animal, fase_publico, tipo_tratamento, sabor_proteina, peso_embalagem
        """
        resultado = {
            "especie_indicada": None,
            "linha_racao": None,
            "porte_animal": None,
            "fase_publico": None,
            "tipo_tratamento": None,
            "sabor_proteina": None,
            "peso_embalagem": None,
        }
        
        # Classificar espécie
        especies = self._classificar_categoria(nome, self.especies_compiled)
        if especies:
            resultado["especie_indicada"] = especies[0]  # Pega primeira espécie identificada
        
        # Classificar linha/categoria (Premium, Super Premium, etc.)
        linhas = self._classificar_categoria(nome, self.linhas_compiled)
        if linhas:
            # Ordem de prioridade: Super Premium > Premium Special > Premium > Standard
            prioridade = ["Super Premium", "Premium Special", "Premium", "Standard"]
            for linha in prioridade:
                if linha in linhas:
                    resultado["linha_racao"] = linha
                    break
        
        # Classificar porte
        resultado["porte_animal"] = self._classificar_categoria(nome, self.portes_compiled)
        
        # Classificar fase
        resultado["fase_publico"] = self._classificar_categoria(nome, self.fases_compiled)
        
        # Classificar tratamento
        resultado["tipo_tratamento"] = self._classificar_categoria(nome, self.tratamentos_compiled)
        
        # Classificar sabor (retorna único, não array)
        sabores = self._classificar_categoria(nome, self.sabores_compiled)
        if sabores:
            resultado["sabor_proteina"] = sabores[0]  # Pega primeiro match
        
        # Extrair peso (só se não tiver peso_atual)
        if not peso_atual:
            peso_extraido = self.extrair_peso(nome)
            if peso_extraido:
                resultado["peso_embalagem"] = peso_extraido
        
        return resultado
    
    def analisar_confianca(self, resultado: Dict) -> Dict:
        """
        Analisa a confiança da classificação
        
        Returns:
            {
                "completo": bool,
                "campos_faltantes": List[str],
                "score": float (0-100)
            }
        """
        campos_importantes = ["porte_animal", "fase_publico", "sabor_proteina", "peso_embalagem"]
        campos_preenchidos = sum(1 for campo in campos_importantes if resultado.get(campo))
        
        campos_faltantes = [
            campo for campo in campos_importantes 
            if not resultado.get(campo)
        ]
        
        score = (campos_preenchidos / len(campos_importantes)) * 100
        
        return {
            "completo": score == 100,
            "campos_faltantes": campos_faltantes,
            "score": round(score, 1)
        }
    
    def gerar_origem_campos(self, resultado: Dict) -> Dict[str, str]:
        """
        Gera dict com origem de cada campo classificado pela IA
        
        Args:
            resultado: Resultado da classificação
        
        Returns:
            Dict mapeando campo -> origem ("IA" para campos identificados automaticamente)
        """
        origem = {}
        
        # Todos os campos identificados pela IA são marcados como "IA"
        campos_ia = [
            "especie_indicada",
            "linha_racao",
            "porte_animal",
            "fase_publico",
            "tipo_tratamento",
            "sabor_proteina",
            "peso_embalagem"
        ]
        
        for campo in campos_ia:
            if resultado.get(campo) is not None:
                origem[campo] = "IA"
        
        return origem


# Instância global do classificador
classificador = ClassificadorRacao()


def classificar_produto(nome: str, peso_atual: Optional[float] = None) -> Tuple[Dict, Dict, Dict]:
    """
    Função helper para classificar produto
    
    Returns:
        (resultado_classificacao, analise_confianca, metadata)
        metadata contém: {"versao": "v1.0.0", "origem": {...}}
    """
    resultado = classificador.classificar(nome, peso_atual)
    confianca = classificador.analisar_confianca(resultado)
    origem = classificador.gerar_origem_campos(resultado)
    
    metadata = {
        "versao": ClassificadorRacao.VERSION,
        "origem": origem
    }
    
    return resultado, confianca, metadata
