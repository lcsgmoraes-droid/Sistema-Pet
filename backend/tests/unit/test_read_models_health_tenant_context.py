from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.read_models import queries
from app.read_models.models import (  # noqa: F401
    PerformanceParceiro,
    ReceitaMensal,
    VendasResumoDiario,
)
from app.tenancy.context import clear_current_tenant


def test_verificar_saude_read_models_funciona_sem_tenant_context():
    clear_current_tenant()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        resultado = queries.verificar_saude_read_models(db)
    finally:
        db.close()
        clear_current_tenant()

    assert resultado["status"] == "healthy"
    assert set(resultado["read_models"]) == {
        "VendasResumoDiario",
        "ReceitaMensal",
        "PerformanceParceiro",
    }
