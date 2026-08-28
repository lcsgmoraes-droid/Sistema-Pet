"""Basic unauthenticated application routes."""

from typing import Optional

from fastapi import FastAPI

from app.config import SYSTEM_NAME, SYSTEM_VERSION


def register_basic_routes(app: FastAPI) -> None:
    """Register root, health and small diagnostic routes."""

    @app.get("/")
    def root():
        """Rota raiz"""
        return {
            "system": SYSTEM_NAME,
            "version": SYSTEM_VERSION,
            "status": "online",
            "docs": "/docs",
        }

    @app.get("/test-racas")
    def test_racas(especie: str = ""):
        """Rota de teste para debug"""
        return [
            {"id": 1, "nome": "Labrador", "especie": "Cão"},
            {"id": 2, "nome": "Golden Retriever", "especie": "Cão"},
            {"id": 3, "nome": "Siamês", "especie": "Gato"},
        ]

    @app.get("/racas")
    def get_racas(especie: Optional[str] = None):
        """
        Endpoint de raças para formulário de pets
        Retorna lista de raças filtradas por espécie
        """
        racas_cao = [
            {"id": 1, "nome": "Labrador", "especie": "Cão"},
            {"id": 2, "nome": "Golden Retriever", "especie": "Cão"},
            {"id": 3, "nome": "Bulldog", "especie": "Cão"},
            {"id": 4, "nome": "Poodle", "especie": "Cão"},
            {"id": 5, "nome": "Pastor Alemão", "especie": "Cão"},
            {"id": 6, "nome": "Beagle", "especie": "Cão"},
            {"id": 7, "nome": "Yorkshire", "especie": "Cão"},
            {"id": 8, "nome": "Shih Tzu", "especie": "Cão"},
            {"id": 9, "nome": "Pit Bull", "especie": "Cão"},
            {"id": 10, "nome": "Chihuahua", "especie": "Cão"},
            {"id": 11, "nome": "SRD (Sem Raça Definida)", "especie": "Cão"},
        ]

        racas_gato = [
            {"id": 12, "nome": "Siamês", "especie": "Gato"},
            {"id": 13, "nome": "Persa", "especie": "Gato"},
            {"id": 14, "nome": "Maine Coon", "especie": "Gato"},
            {"id": 15, "nome": "Bengal", "especie": "Gato"},
            {"id": 16, "nome": "Sphynx", "especie": "Gato"},
            {"id": 17, "nome": "Ragdoll", "especie": "Gato"},
            {"id": 18, "nome": "SRD (Sem Raça Definida)", "especie": "Gato"},
        ]

        if especie == "Cão":
            return racas_cao
        elif especie == "Gato":
            return racas_gato
        else:
            return racas_cao + racas_gato
