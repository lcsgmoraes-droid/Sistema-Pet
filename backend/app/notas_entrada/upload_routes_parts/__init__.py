from app.notas_entrada.upload_routes_parts.lote_xml_route import (
    router as lote_xml_router,
    upload_lote_xml,
)
from app.notas_entrada.upload_routes_parts.pdf_route import router as pdf_router
from app.notas_entrada.upload_routes_parts.pdf_route import upload_pdf
from app.notas_entrada.upload_routes_parts.xml_route import router as xml_router
from app.notas_entrada.upload_routes_parts.xml_route import upload_xml

__all__ = [
    "lote_xml_router",
    "pdf_router",
    "upload_lote_xml",
    "upload_pdf",
    "upload_xml",
    "xml_router",
]
