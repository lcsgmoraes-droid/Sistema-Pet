from datetime import date

from app.whatsapp import models as _whatsapp_models  # noqa: F401
from app.whatsapp import models_handoff as _whatsapp_handoff_models  # noqa: F401
from app.services import vet_clinical_evidence as service
from app.veterinario_models import (
    DocumentoConhecimentoVet,
    FonteConhecimentoVet,
)

PUBMED_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <Journal>
          <JournalIssue>
            <PubDate><Year>2026</Year><Month>Jul</Month><Day>18</Day></PubDate>
          </JournalIssue>
          <Title>Journal of Veterinary Internal Medicine</Title>
        </Journal>
        <ArticleTitle>Acute kidney injury in dogs: a prospective study</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Renal injury is clinically relevant.</AbstractText>
          <AbstractText Label="RESULTS">Early monitoring improved detection and supported safer clinical decisions in canine patients with suspected acute renal injury.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><ForeName>Ana</ForeName><LastName>Silva</LastName></Author>
        </AuthorList>
        <Language>eng</Language>
      </Article>
      <MeshHeadingList>
        <MeshHeading><DescriptorName>Dogs</DescriptorName></MeshHeading>
        <MeshHeading><DescriptorName>Acute Kidney Injury</DescriptorName></MeshHeading>
      </MeshHeadingList>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">12345678</ArticleId>
        <ArticleId IdType="doi">10.1000/vet.2026.1</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


def _source(db_session):
    source = FonteConhecimentoVet(
        codigo="pubmed",
        nome="PubMed",
        tipo="literatura_cientifica",
        url_base="https://pubmed.ncbi.nlm.nih.gov/",
        requer_revisao=True,
        ativo=True,
    )
    db_session.add(source)
    db_session.flush()
    return source


def test_parse_pubmed_xml_extracts_traceable_metadata():
    rows = service.parse_pubmed_xml(PUBMED_XML)

    assert len(rows) == 1
    row = rows[0]
    assert row["fonte_documento_id"] == "12345678"
    assert row["publicado_em"] == date(2026, 7, 18)
    assert row["doi"] == "10.1000/vet.2026.1"
    assert row["especies"] == ["cao"]
    assert "BACKGROUND: Renal injury" in row["resumo"]
    assert len(row["hash_conteudo"]) == 64


def test_automatic_evidence_status_keeps_short_record_as_reference_only():
    row = service.parse_pubmed_xml(PUBMED_XML)[0]
    row["resumo"] = "Resumo curto."

    assert service._automatic_evidence_status(row) == "referencia"


def test_sync_pubmed_makes_eligible_abstract_automatically_available(
    db_session, monkeypatch
):
    monkeypatch.setattr(service, "_fetch_pubmed_ids", lambda **_kwargs: ["12345678"])
    monkeypatch.setattr(
        service,
        "_fetch_pubmed_records",
        lambda _ids, **_kwargs: service.parse_pubmed_xml(PUBMED_XML),
    )

    result = service.sync_pubmed_veterinary_evidence(
        db_session,
        dry_run=False,
        limit=1,
    )
    db_session.flush()
    document = db_session.query(DocumentoConhecimentoVet).one()

    assert result["created"] == 1
    assert result["auto_available"] == 1
    assert result["pending_review"] == 0
    assert document.status_revisao == "auto_disponivel"


def test_retrieval_uses_human_reviewed_and_automatically_eligible_documents(
    db_session,
):
    source = _source(db_session)
    approved = DocumentoConhecimentoVet(
        fonte_id=source.id,
        fonte_documento_id="approved",
        titulo="Acute kidney injury in dogs",
        resumo="Renal monitoring in canine patients.",
        autores=[],
        periodico="Vet Journal",
        url="https://pubmed.ncbi.nlm.nih.gov/1/",
        publicado_em=date(2026, 1, 1),
        especies=["cao"],
        temas=["Dogs", "Acute Kidney Injury"],
        status_revisao="aprovado",
        hash_conteudo="a" * 64,
        ativo=True,
    )
    pending = DocumentoConhecimentoVet(
        fonte_id=source.id,
        fonte_documento_id="pending",
        titulo="Kidney disease in dogs",
        resumo="This pending article must not be retrieved.",
        autores=[],
        url="https://pubmed.ncbi.nlm.nih.gov/2/",
        temas=["Dogs", "Kidney"],
        status_revisao="pendente",
        hash_conteudo="b" * 64,
        ativo=True,
    )
    automatic = DocumentoConhecimentoVet(
        fonte_id=source.id,
        fonte_documento_id="automatic",
        titulo="Canine kidney injury monitoring",
        resumo="Automatically screened PubMed abstract about renal monitoring.",
        autores=[],
        url="https://pubmed.ncbi.nlm.nih.gov/3/",
        temas=["Dogs", "Kidney"],
        status_revisao="auto_disponivel",
        hash_conteudo="c" * 64,
        ativo=True,
    )
    db_session.add_all([approved, pending, automatic])
    db_session.flush()

    result = service.buscar_evidencias_clinicas_disponiveis(
        db_session,
        pergunta="Como investigar lesão renal no cachorro?",
    )

    assert {item["fonte_documento_id"] for item in result} == {
        "approved",
        "automatic",
    }
    assert result[0]["ref"] == "E1"
    assert all(item["fonte_documento_id"] != "pending" for item in result)


def test_retrieval_does_not_use_species_match_as_clinical_relevance(db_session):
    source = _source(db_session)
    irrelevant = DocumentoConhecimentoVet(
        fonte_id=source.id,
        fonte_documento_id="irrelevant",
        titulo="Canine mammary tumor therapeutic screening",
        resumo=(
            "Laboratory study using Madin Darby canine kidney cells "
            "to evaluate therapeutic response."
        ),
        autores=[],
        url="https://pubmed.ncbi.nlm.nih.gov/4/",
        temas=["Dogs", "Mammary Tumors", "Madin Darby Canine Kidney Cells"],
        status_revisao="auto_disponivel",
        hash_conteudo="d" * 64,
        ativo=True,
    )
    db_session.add(irrelevant)
    db_session.flush()

    result = service.buscar_evidencias_clinicas_disponiveis(
        db_session,
        pergunta=(
            "Caso fictício: cão com vômitos e creatinina elevada. "
            "Quais hipóteses e próximos exames?"
        ),
    )

    assert result == []


def test_retrieval_rejects_mdck_influenza_study_for_canine_kidney_case(db_session):
    source = _source(db_session)
    relevant = DocumentoConhecimentoVet(
        fonte_id=source.id,
        fonte_documento_id="ckd-dogs",
        titulo="Chronic kidney disease monitoring in dogs",
        resumo="Clinical renal monitoring of dogs with chronic kidney disease.",
        autores=[],
        url="https://pubmed.ncbi.nlm.nih.gov/10/",
        temas=["Dogs", "Renal Insufficiency, Chronic", "Kidney disease"],
        status_revisao="auto_disponivel",
        hash_conteudo="e" * 64,
        ativo=True,
    )
    irrelevant = DocumentoConhecimentoVet(
        fonte_id=source.id,
        fonte_documento_id="mdck-influenza",
        titulo="Development of an H5N1 influenza vaccine using MDCK cells",
        resumo=(
            "A scalable influenza vaccine manufacturing platform using "
            "Madin Darby canine kidney cells."
        ),
        autores=[],
        url="https://pubmed.ncbi.nlm.nih.gov/11/",
        temas=["Dogs", "Madin Darby Canine Kidney Cells", "Influenza Vaccines"],
        status_revisao="auto_disponivel",
        hash_conteudo="f" * 64,
        ativo=True,
    )
    db_session.add_all([relevant, irrelevant])
    db_session.flush()

    result = service.buscar_evidencias_clinicas_disponiveis(
        db_session,
        pergunta=(
            "Cao com doenca renal cronica e vomitos. Quais informacoes devo "
            "avaliar antes de sugerir medicamento?"
        ),
    )

    assert [item["fonte_documento_id"] for item in result] == ["ckd-dogs"]


def test_content_change_recalculates_automatic_eligibility(db_session, monkeypatch):
    source = _source(db_session)
    original = service.parse_pubmed_xml(PUBMED_XML)[0]
    document = DocumentoConhecimentoVet(
        fonte_id=source.id,
        status_revisao="aprovado",
        revisado_por_id=99,
        **original,
    )
    db_session.add(document)
    db_session.flush()

    changed = {
        **original,
        "resumo": (
            "Updated abstract from the source with sufficient detail about "
            "population, clinical monitoring, outcomes, limitations, and "
            "follow-up for veterinary decision support."
        ),
    }
    changed["hash_conteudo"] = service._content_hash(changed)
    monkeypatch.setattr(service, "_fetch_pubmed_ids", lambda **_kwargs: ["12345678"])
    monkeypatch.setattr(
        service,
        "_fetch_pubmed_records",
        lambda _ids, **_kwargs: [changed],
    )

    result = service.sync_pubmed_veterinary_evidence(
        db_session,
        dry_run=False,
        limit=1,
    )

    assert result["updated"] == 1
    assert document.status_revisao == "auto_disponivel"
    assert document.revisado_por_id is None
    assert "elegibilidade automática recalculada" in document.motivo_revisao
