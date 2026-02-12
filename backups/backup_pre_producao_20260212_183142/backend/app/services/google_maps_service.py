"""
Google Maps Service - Etapa 9.2
Serviços para integração com Google Maps API (Distance Matrix, Directions, Geocoding)
"""

import requests
from decimal import Decimal
from typing import Dict, Any, List, Tuple
from app.config import GOOGLE_MAPS_API_KEY
from app.utils.logger import logger


# URLs da API
GOOGLE_DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
GOOGLE_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def calcular_distancia_km(origem: str, destino: str) -> Decimal:
    """
    Calcula distância em KM entre origem e destino usando Google Distance Matrix API
    
    Args:
        origem: Endereço de partida (ex: "Av. Paulista, 1578, São Paulo, SP")
        destino: Endereço de chegada
        
    Returns:
        Distância em quilômetros (Decimal)
        
    Raises:
        Exception: Se houver erro na API ou rota inválida
        
    Exemplo:
        >>> distancia = calcular_distancia_km(
        ...     "Av. Paulista, 1578, São Paulo, SP",
        ...     "Rua Augusta, 2690, São Paulo, SP"
        ... )
        >>> logger.info(f"{distancia} km")
        2.41 km
    """
    if not GOOGLE_MAPS_API_KEY:
        raise Exception("GOOGLE_MAPS_API_KEY não configurada")
    
    params = {
        "origins": origem,
        "destinations": destino,
        "key": GOOGLE_MAPS_API_KEY,
        "units": "metric",
    }

    try:
        response = requests.get(GOOGLE_DISTANCE_MATRIX_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise Exception(f"Erro ao chamar Google Maps API: {str(e)}")

    # Validar resposta
    if data.get("status") != "OK":
        error_message = data.get("error_message", "Erro desconhecido")
        raise Exception(f"Erro Google Maps: {data.get('status')} - {error_message}")

    # Validar elemento
    element = data["rows"][0]["elements"][0]
    
    if element.get("status") != "OK":
        raise Exception(f"Rota inválida: {element.get('status')}")

    # Extrair distância em metros e converter para KM
    distancia_m = element["distance"]["value"]
    distancia_km = Decimal(distancia_m) / Decimal(1000)

    return distancia_km.quantize(Decimal("0.01"))  # Arredondar para 2 casas decimais


def calcular_distancia_com_duracao(origem: str, destino: str) -> Dict[str, Any]:
    """
    Calcula distância e duração entre origem e destino
    
    Args:
        origem: Endereço de partida
        destino: Endereço de chegada
        
    Returns:
        Dict com:
            - distancia_km (Decimal): Distância em quilômetros
            - duracao_minutos (int): Duração estimada em minutos
            - distancia_texto (str): Distância formatada (ex: "2.4 km")
            - duracao_texto (str): Duração formatada (ex: "11 mins")
            
    Exemplo:
        >>> resultado = calcular_distancia_com_duracao(origem, destino)
        >>> logger.info(f"{resultado['distancia_km']} km em {resultado['duracao_minutos']} minutos")
    """
    if not GOOGLE_MAPS_API_KEY:
        raise Exception("GOOGLE_MAPS_API_KEY não configurada")
    
    params = {
        "origins": origem,
        "destinations": destino,
        "key": GOOGLE_MAPS_API_KEY,
        "units": "metric",
    }

    try:
        response = requests.get(GOOGLE_DISTANCE_MATRIX_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise Exception(f"Erro ao chamar Google Maps API: {str(e)}")

    if data.get("status") != "OK":
        error_message = data.get("error_message", "Erro desconhecido")
        raise Exception(f"Erro Google Maps: {data.get('status')} - {error_message}")

    element = data["rows"][0]["elements"][0]
    
    if element.get("status") != "OK":
        raise Exception(f"Rota inválida: {element.get('status')}")

    # Extrair dados
    distancia_m = element["distance"]["value"]
    distancia_km = Decimal(distancia_m) / Decimal(1000)
    distancia_texto = element["distance"]["text"]
    
    duracao_segundos = element["duration"]["value"]
    duracao_minutos = int(duracao_segundos / 60)
    duracao_texto = element["duration"]["text"]

    return {
        "distancia_km": distancia_km.quantize(Decimal("0.01")),
        "duracao_minutos": duracao_minutos,
        "distancia_texto": distancia_texto,
        "duracao_texto": duracao_texto,
    }


def calcular_tempo_estimado(origem: str, destino: str) -> int:
    """
    ETAPA 10 - Calcula apenas o tempo estimado entre dois pontos
    
    Args:
        origem: Endereço de partida
        destino: Endereço de chegada
        
    Returns:
        Tempo estimado em segundos
        
    Exemplo:
        >>> segundos = calcular_tempo_estimado(origem, destino)
        >>> minutos = segundos / 60
    """
    try:
        resultado = calcular_distancia_com_duracao(origem, destino)
        return resultado["duracao_minutos"] * 60  # Converter para segundos
    except Exception as e:
        # Fallback: estimar 30 segundos por km (velocidade urbana ~40km/h)
        raise e


def geocode_endereco(endereco: str) -> Tuple[Decimal, Decimal]:
    """
    Converte endereço em coordenadas (latitude, longitude)
    
    Args:
        endereco: Endereço completo
        
    Returns:
        Tupla (latitude, longitude)
        
    Exemplo:
        >>> lat, lng = geocode_endereco("Av. Paulista, 1578, São Paulo, SP")
        >>> logger.info(f"Lat: {lat}, Lng: {lng}")
        Lat: -23.5614117, Lng: -46.6558999
    """
    if not GOOGLE_MAPS_API_KEY:
        raise Exception("GOOGLE_MAPS_API_KEY não configurada")
    
    params = {
        "address": endereco,
        "key": GOOGLE_MAPS_API_KEY,
    }

    try:
        response = requests.get(GOOGLE_GEOCODING_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise Exception(f"Erro ao chamar Google Geocoding API: {str(e)}")

    if data.get("status") != "OK":
        error_message = data.get("error_message", "Erro desconhecido")
        raise Exception(f"Erro Geocoding: {data.get('status')} - {error_message}")

    location = data["results"][0]["geometry"]["location"]
    
    latitude = Decimal(str(location["lat"]))
    longitude = Decimal(str(location["lng"]))

    return (latitude, longitude)


def calcular_rota_multiplos_pontos(
    origem: str, 
    destino: str, 
    paradas: List[str]
) -> Dict[str, Any]:
    """
    Calcula rota otimizada com múltiplas paradas usando Directions API
    
    Args:
        origem: Endereço de partida
        destino: Endereço de chegada
        paradas: Lista de endereços intermediários
        
    Returns:
        Dict com:
            - distancia_total_km (Decimal): Distância total da rota
            - duracao_total_minutos (int): Tempo total estimado
            - segmentos (List): Detalhes de cada trecho
            - ordem_otimizada (List[int]): Índices das paradas na ordem otimizada
            
    Exemplo:
        >>> resultado = calcular_rota_multiplos_pontos(
        ...     origem="Loja",
        ...     destino="Loja",  # Retorna à loja
        ...     paradas=["Cliente 1", "Cliente 2", "Cliente 3"]
        ... )
        >>> logger.info(f"Total: {resultado['distancia_total_km']} km")
    """
    if not GOOGLE_MAPS_API_KEY:
        raise Exception("GOOGLE_MAPS_API_KEY não configurada")
    
    params = {
        "origin": origem,
        "destination": destino,
        "key": GOOGLE_MAPS_API_KEY,
        "units": "metric",
    }
    
    # Adicionar paradas (waypoints)
    if paradas:
        # optimize:true pede ao Google para otimizar a ordem das paradas
        waypoints_str = "optimize:true|" + "|".join(paradas)
        params["waypoints"] = waypoints_str

    try:
        response = requests.get(GOOGLE_DIRECTIONS_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise Exception(f"Erro ao chamar Google Directions API: {str(e)}")

    if data.get("status") != "OK":
        error_message = data.get("error_message", "Erro desconhecido")
        raise Exception(f"Erro Directions: {data.get('status')} - {error_message}")

    route = data["routes"][0]
    
    # Calcular totais
    distancia_total_m = sum(leg["distance"]["value"] for leg in route["legs"])
    distancia_total_km = Decimal(distancia_total_m) / Decimal(1000)
    
    duracao_total_segundos = sum(leg["duration"]["value"] for leg in route["legs"])
    duracao_total_minutos = int(duracao_total_segundos / 60)
    
    # Extrair segmentos
    segmentos = []
    for i, leg in enumerate(route["legs"]):
        segmentos.append({
            "ordem": i + 1,
            "origem": leg["start_address"],
            "destino": leg["end_address"],
            "distancia_km": Decimal(leg["distance"]["value"]) / Decimal(1000),
            "duracao_minutos": int(leg["duration"]["value"] / 60),
        })
    
    # Ordem otimizada (se houver paradas)
    ordem_otimizada = []
    if paradas and "waypoint_order" in route:
        ordem_otimizada = route["waypoint_order"]

    return {
        "distancia_total_km": distancia_total_km.quantize(Decimal("0.01")),
        "duracao_total_minutos": duracao_total_minutos,
        "segmentos": segmentos,
        "ordem_otimizada": ordem_otimizada,
    }


def calcular_rota_otimizada(origem: str, destinos: List[str]) -> Tuple[List[int], List[Dict[str, Any]]]:
    """
    ETAPA 9.3 - Calcula a melhor ordem de entregas usando Google Directions API
    
    Usa optimize:true para que o Google retorne a sequência otimizada que
    minimiza distância/tempo total.
    
    Args:
        origem: Endereço de partida (loja)
        destinos: Lista de endereços de entrega (N entregas)
        
    Returns:
        Tupla com:
            - ordem (List[int]): Índices reordenados (ex: [2, 0, 1] = entregar 3º, depois 1º, depois 2º)
            - legs (List[Dict]): Detalhes de cada trecho com distância e duração
            
    Raises:
        Exception: Se houver erro na API ou rota inválida
        
    Exemplo:
        >>> origem = "Rua da Loja, 100"
        >>> destinos = [
        ...     "Cliente A - Rua X, 10",
        ...     "Cliente B - Rua Y, 20", 
        ...     "Cliente C - Rua Z, 30"
        ... ]
        >>> ordem, legs = calcular_rota_otimizada(origem, destinos)
        >>> logger.info(f"Ordem otimizada: {ordem}")  # Ex: [1, 2, 0]
        >>> logger.info(f"1ª parada: Cliente {ordem[0] + 1}")  # Ex: Cliente B
        
    Detalhes dos legs:
        Cada item contém:
        - distance.value: distância em metros
        - distance.text: distância formatada
        - duration.value: duração em segundos
        - duration.text: duração formatada
    """
    if not GOOGLE_MAPS_API_KEY:
        raise Exception("GOOGLE_MAPS_API_KEY não configurada")
    
    if not destinos:
        raise Exception("Lista de destinos está vazia")
    
    # Montar waypoints com optimize:true
    waypoints = "|".join(destinos)
    
    params = {
        "origin": origem,
        "destination": destinos[-1],  # Último destino (será reordenado)
        "waypoints": f"optimize:true|{waypoints}",
        "key": GOOGLE_MAPS_API_KEY,
        "units": "metric",
    }

    try:
        response = requests.get(GOOGLE_DIRECTIONS_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise Exception(f"Erro ao chamar Google Directions API: {str(e)}")

    # Validar resposta
    if data.get("status") != "OK":
        error_message = data.get("error_message", "Erro desconhecido")
        raise Exception(f"Erro Google Directions: {data.get('status')} - {error_message}")

    route = data["routes"][0]
    
    # Extrair ordem otimizada
    ordem = route.get("waypoint_order", [])
    
    # Extrair legs (trechos da rota)
    legs = route["legs"]

    return ordem, legs
