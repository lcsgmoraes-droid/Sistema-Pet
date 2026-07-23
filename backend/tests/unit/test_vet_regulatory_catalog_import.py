from types import SimpleNamespace

import pytest

from app.services import vet_regulatory_catalog_import as catalog


def test_parse_dailymed_title_separates_product_ingredient_and_manufacturer():
    parsed = catalog._parse_dailymed_title(
        "NEXGARD COMBO (ESAFOXOLANER, EPRINOMECTIN, AND PRAZIQUANTEL) SOLUTION "
        "[BOEHRINGER INGELHEIM ANIMAL HEALTH USA INC.]"
    )

    assert parsed["nome_comercial"] == "NEXGARD COMBO"
    assert parsed["principio_ativo"] == ("ESAFOXOLANER, EPRINOMECTIN, AND PRAZIQUANTEL")
    assert parsed["forma_farmaceutica"] == "SOLUTION"
    assert parsed["fabricante"] == "BOEHRINGER INGELHEIM ANIMAL HEALTH USA INC."


def test_validate_dailymed_page_rejects_wrong_source_schema():
    with pytest.raises(catalog.RegulatorySourceSchemaError):
        catalog._validate_dailymed_page({"data": [{"UNIDADE_DA_FEDERACAO": "SP"}]})


def test_build_dailymed_row_is_explicit_about_us_jurisdiction_and_status():
    row = catalog._build_dailymed_row(
        {
            "setid": "abc-123",
            "title": "CARPROFEN INJECTION [MWI ANIMAL HEALTH]",
            "published_date": "Jul 20, 2026",
            "spl_version": 1,
        },
        "50578-4",
    )

    assert row["jurisdicao"] == "US"
    assert row["status_regulatorio"].endswith("nao_verificado")
    assert row["bula_url"].endswith("setid=abc-123&type=pdf")
    assert row["publicado_em"].isoformat() == "2026-07-20"


def test_changed_ignores_only_sync_timestamp():
    row = catalog._build_dailymed_row(
        {
            "setid": "abc-123",
            "title": "CARPROFEN INJECTION [MWI ANIMAL HEALTH]",
            "published_date": "Jul 20, 2026",
            "spl_version": 1,
        },
        "50578-4",
    )
    existing = SimpleNamespace(**row)

    assert catalog._changed(existing, row) is False


def test_parse_vmd_snapshot_keeps_authorised_product_and_spc():
    xml_payload = b"""<?xml version="1.0"?>
    <VMD_PIDProducts>
      <CurrentAuthorisedProducts>
        <VMDProductNo>A123</VMDProductNo>
        <Name>Example Tablets for Dogs and Cats</Name>
        <MAHolder>Example Animal Health Ltd</MAHolder>
        <VMNo>01234/5678</VMNo>
        <DateOfIssue>2026-07-01</DateOfIssue>
        <Territory>Great Britain</Territory>
        <ActiveSubstances>Meloxicam</ActiveSubstances>
        <ControlledDrug>N</ControlledDrug>
        <TargetSpecies>Dogs, Cats</TargetSpecies>
        <DistributionCategory>POM-V</DistributionCategory>
        <PharmaceuticalForm>Tablet</PharmaceuticalForm>
        <TherapeuticGroup>Analgesic</TherapeuticGroup>
        <SPC_Link>https://example.test/spc.pdf</SPC_Link>
      </CurrentAuthorisedProducts>
      <ExpiredProducts>
        <VMDProductNo>E999</VMDProductNo>
        <Name>Expired Product</Name>
        <SPC_Link>https://example.test/expired.pdf</SPC_Link>
      </ExpiredProducts>
    </VMD_PIDProducts>
    """

    rows = catalog.parse_vmd_current_products(xml_payload)

    assert len(rows) == 1
    assert rows[0]["fonte"] == "vmd_uk"
    assert rows[0]["fonte_id"] == "A123"
    assert rows[0]["jurisdicao"] == "GB"
    assert rows[0]["status_regulatorio"] == "autorizado_vmd"
    assert rows[0]["principio_ativo"] == "Meloxicam"
    assert rows[0]["especies_indicadas"] == ["Dogs", "Cats"]
    assert rows[0]["bula_url"] == "https://example.test/spc.pdf"
