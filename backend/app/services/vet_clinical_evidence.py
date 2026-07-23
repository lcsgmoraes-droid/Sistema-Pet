"""Sincronizacao, revisao e recuperacao de evidencia clinica veterinaria."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable, Optional

from defusedxml import ElementTree as ET
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.veterinario_models import (
    DocumentoConhecimentoVet,
    FonteConhecimentoVet,
)

PUBMED_SOURCE_CODE = "pubmed"
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_DEFAULT_QUERY = (
    "(veterinary medicine[MeSH Terms] OR dogs[MeSH Terms] OR cats[MeSH Terms] "
    'OR horses[MeSH Terms] OR cattle[MeSH Terms]) AND ("last 2 years"[PDat])'
)
PUBMED_TERMS_URL = "https://www.ncbi.nlm.nih.gov/home/develop/api/"
AUTO_AVAILABLE_STATUS = "auto_disponivel"
REFERENCE_ONLY_STATUS = "referencia"


class ClinicalEvidenceSourceError(RuntimeError):
    """A fonte externa falhou ou respondeu com contrato inesperado."""


@dataclass
class EvidenceSyncSummary:
    source: str
    dry_run: bool
    fetched: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0
    pending_review: int = 0
    auto_available: int = 0
    reference_only: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "dry_run": self.dry_run,
            "fetched": self.fetched,
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "rejected": self.rejected,
            "pending_review": self.pending_review,
            "auto_available": self.auto_available,
            "reference_only": self.reference_only,
        }


def _http_bytes(url: str, timeout_seconds: int = 45) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, application/xml",
            "User-Agent": (
                "CorePet/1.0 (evidencia-clinica-veterinaria; contato@corepet.com.br)"
            ),
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def _text(element) -> str:
    if element is None:
        return ""
    return re.sub(r"\s+", " ", "".join(element.itertext())).strip()


def _parse_pubmed_date(article) -> Optional[date]:
    candidates = [
        article.find("./MedlineCitation/Article/ArticleDate"),
        article.find("./MedlineCitation/Article/Journal/JournalIssue/PubDate"),
        article.find("./PubmedData/History/PubMedPubDate[@PubStatus='pubmed']"),
    ]
    month_names = {
        name.lower(): index
        for index, name in enumerate(
            (
                "",
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            )
        )
        if name
    }
    for node in candidates:
        if node is None:
            continue
        year_text = _text(node.find("Year"))
        month_text = _text(node.find("Month"))
        day_text = _text(node.find("Day"))
        try:
            year = int(year_text)
            month = (
                int(month_text)
                if month_text.isdigit()
                else month_names.get(month_text[:3].lower(), 1)
            )
            day = int(day_text) if day_text.isdigit() else 1
            return date(year, max(1, min(month, 12)), max(1, min(day, 28)))
        except (TypeError, ValueError):
            medline_date = _text(node.find("MedlineDate"))
            match = re.search(r"\b(19|20)\d{2}\b", medline_date)
            if match:
                return date(int(match.group(0)), 1, 1)
    return None


def _unique(values: Iterable[str], limit: int = 40) -> list[str]:
    result: list[str] = []
    for value in values:
        clean = re.sub(r"\s+", " ", str(value or "")).strip()
        if clean and clean.casefold() not in {item.casefold() for item in result}:
            result.append(clean)
        if len(result) >= limit:
            break
    return result


def _infer_species(terms: Iterable[str]) -> list[str]:
    joined = " ".join(terms).casefold()
    mapping = (
        ("cao", ("dog", "canine")),
        ("gato", ("cat", "feline")),
        ("equino", ("horse", "equine")),
        ("bovino", ("cattle", "bovine", "cow")),
        ("suino", ("swine", "porcine", "pig")),
        ("ave", ("poultry", "avian", "bird")),
    )
    return [
        label for label, aliases in mapping if any(alias in joined for alias in aliases)
    ]


def _content_hash(row: dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "titulo": row["titulo"],
            "resumo": row["resumo"],
            "autores": row["autores"],
            "publicado_em": (
                row["publicado_em"].isoformat() if row["publicado_em"] else None
            ),
            "temas": row["temas"],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _automatic_evidence_status(row: dict[str, Any]) -> str:
    publication_types = {
        str(item or "").strip().casefold()
        for item in (row.get("metadados_fonte") or {}).get("publication_types", [])
    }
    if publication_types & {
        "retracted publication",
        "retraction of publication",
    }:
        return "rejeitado"
    if len(str(row.get("resumo") or "").strip()) < 120:
        return REFERENCE_ONLY_STATUS
    return AUTO_AVAILABLE_STATUS


def parse_pubmed_xml(xml_payload: bytes) -> list[dict[str, Any]]:
    """Converte o XML oficial do PubMed em registros em quarentena."""

    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError as exc:
        raise ClinicalEvidenceSourceError("PubMed retornou XML invalido.") from exc

    rows: list[dict[str, Any]] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = _text(article.find("./MedlineCitation/PMID"))
        title = _text(article.find("./MedlineCitation/Article/ArticleTitle"))
        if not pmid or not title:
            continue

        abstract_parts = []
        for abstract in article.findall(
            "./MedlineCitation/Article/Abstract/AbstractText"
        ):
            value = _text(abstract)
            label = str(abstract.attrib.get("Label") or "").strip()
            if value:
                abstract_parts.append(f"{label}: {value}" if label else value)

        authors = []
        for author in article.findall("./MedlineCitation/Article/AuthorList/Author"):
            collective = _text(author.find("CollectiveName"))
            personal = " ".join(
                part
                for part in (
                    _text(author.find("ForeName")),
                    _text(author.find("LastName")),
                )
                if part
            )
            authors.append(collective or personal)

        mesh_terms = [
            _text(node)
            for node in article.findall(
                "./MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName"
            )
        ]
        keywords = [
            _text(node)
            for node in article.findall("./MedlineCitation/KeywordList/Keyword")
        ]
        topics = _unique([*mesh_terms, *keywords])
        doi = None
        for article_id in article.findall("./PubmedData/ArticleIdList/ArticleId"):
            if str(article_id.attrib.get("IdType") or "").lower() == "doi":
                doi = _text(article_id) or None
                break

        row = {
            "fonte_documento_id": pmid,
            "titulo": title,
            "resumo": "\n".join(abstract_parts).strip() or None,
            "autores": _unique(authors),
            "periodico": _text(article.find("./MedlineCitation/Article/Journal/Title"))
            or None,
            "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "idioma": _text(article.find("./MedlineCitation/Article/Language")) or None,
            "publicado_em": _parse_pubmed_date(article),
            "especies": _infer_species(topics),
            "temas": topics,
            "metadados_fonte": {
                "pmid": pmid,
                "publication_types": _unique(
                    _text(node)
                    for node in article.findall(
                        "./MedlineCitation/Article/PublicationTypeList/PublicationType"
                    )
                ),
            },
            "ativo": True,
        }
        row["hash_conteudo"] = _content_hash(row)
        rows.append(row)
    return rows


def _fetch_pubmed_ids(
    *,
    query: str,
    retmax: int,
    api_key: Optional[str],
    email: Optional[str],
) -> list[str]:
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": max(1, min(int(retmax), 500)),
        "sort": "pub date",
        "tool": "corepet",
    }
    if api_key:
        params["api_key"] = api_key
    if email:
        params["email"] = email
    payload = _http_bytes(f"{PUBMED_SEARCH_URL}?{urllib.parse.urlencode(params)}")
    try:
        parsed = json.loads(payload)
        ids = parsed["esearchresult"]["idlist"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ClinicalEvidenceSourceError(
            "PubMed ESearch retornou contrato inesperado."
        ) from exc
    return [str(item).strip() for item in ids if str(item).strip()]


def _fetch_pubmed_records(
    ids: list[str],
    *,
    api_key: Optional[str],
    email: Optional[str],
) -> list[dict[str, Any]]:
    if not ids:
        return []
    params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml",
        "rettype": "abstract",
        "tool": "corepet",
    }
    if api_key:
        params["api_key"] = api_key
    if email:
        params["email"] = email
    return parse_pubmed_xml(
        _http_bytes(f"{PUBMED_FETCH_URL}?{urllib.parse.urlencode(params)}")
    )


def _ensure_pubmed_source(db: Session) -> FonteConhecimentoVet:
    source = (
        db.query(FonteConhecimentoVet)
        .filter(FonteConhecimentoVet.codigo == PUBMED_SOURCE_CODE)
        .first()
    )
    if source:
        return source
    source = FonteConhecimentoVet(
        codigo=PUBMED_SOURCE_CODE,
        nome="PubMed / National Library of Medicine",
        tipo="literatura_cientifica",
        url_base="https://pubmed.ncbi.nlm.nih.gov/",
        jurisdicao="US",
        descricao=(
            "Metadados bibliograficos e resumos cientificos. "
            "Ingestao nao equivale a validacao clinica."
        ),
        termos_url=PUBMED_TERMS_URL,
        requer_revisao=False,
        ativo=True,
    )
    db.add(source)
    db.flush()
    return source


def sync_pubmed_veterinary_evidence(
    db: Session,
    *,
    dry_run: bool = True,
    query: str = PUBMED_DEFAULT_QUERY,
    limit: int = 100,
    api_key: Optional[str] = None,
    email: Optional[str] = None,
) -> dict[str, Any]:
    """Ingest studies with automatic source and metadata eligibility."""

    summary = EvidenceSyncSummary(source=PUBMED_SOURCE_CODE, dry_run=dry_run)
    ids = _fetch_pubmed_ids(
        query=query,
        retmax=limit,
        api_key=api_key,
        email=email,
    )
    rows = _fetch_pubmed_records(ids, api_key=api_key, email=email)
    summary.fetched = len(rows)
    summary.rejected = max(0, len(ids) - len(rows))

    source = (
        db.query(FonteConhecimentoVet)
        .filter(FonteConhecimentoVet.codigo == PUBMED_SOURCE_CODE)
        .first()
    )
    if source is None and not dry_run:
        source = _ensure_pubmed_source(db)

    for row in rows:
        automatic_status = _automatic_evidence_status(row)
        if automatic_status == AUTO_AVAILABLE_STATUS:
            summary.auto_available += 1
        elif automatic_status == REFERENCE_ONLY_STATUS:
            summary.reference_only += 1
        else:
            summary.rejected += 1
        existing = None
        if source is not None:
            existing = (
                db.query(DocumentoConhecimentoVet)
                .filter(
                    DocumentoConhecimentoVet.fonte_id == source.id,
                    DocumentoConhecimentoVet.fonte_documento_id
                    == row["fonte_documento_id"],
                )
                .first()
            )
        if existing is None:
            summary.created += 1
            if not dry_run:
                db.add(
                    DocumentoConhecimentoVet(
                        fonte_id=source.id,
                        status_revisao=automatic_status,
                        motivo_revisao=(
                            "Elegibilidade automática pela origem PubMed e "
                            "presença de resumo bibliográfico."
                            if automatic_status == AUTO_AVAILABLE_STATUS
                            else None
                        ),
                        **row,
                    )
                )
            continue

        if existing.hash_conteudo == row["hash_conteudo"]:
            summary.unchanged += 1
            if not dry_run and existing.status_revisao in {
                "pendente",
                AUTO_AVAILABLE_STATUS,
                REFERENCE_ONLY_STATUS,
            }:
                existing.status_revisao = automatic_status
                existing.motivo_revisao = (
                    "Elegibilidade automática recalculada na sincronização."
                )
            continue

        summary.updated += 1
        if not dry_run:
            for field, value in row.items():
                setattr(existing, field, value)
            existing.status_revisao = automatic_status
            existing.motivo_revisao = (
                "Conteúdo alterado na fonte; elegibilidade automática recalculada."
            )
            existing.revisado_por_id = None
            existing.revisado_em = None

    if not dry_run:
        source.ultima_sincronizacao_em = datetime.now(timezone.utc)
        source.ultimo_status = "ok"
        source.ultimo_erro = None
        db.flush()
    return summary.to_dict()


def revisar_documento_clinico(
    documento: DocumentoConhecimentoVet,
    *,
    status: str,
    reviewer_id: int,
    motivo: Optional[str] = None,
) -> DocumentoConhecimentoVet:
    normalized = str(status or "").strip().lower()
    if normalized not in {"aprovado", "rejeitado", "pendente"}:
        raise ValueError("Status de revisao invalido.")
    documento.status_revisao = normalized
    documento.motivo_revisao = str(motivo or "").strip() or None
    documento.revisado_por_id = reviewer_id if normalized != "pendente" else None
    documento.revisado_em = (
        datetime.now(timezone.utc) if normalized != "pendente" else None
    )
    return documento


_STOPWORDS = {
    "a",
    "ao",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "este",
    "esta",
    "meu",
    "minha",
    "no",
    "na",
    "o",
    "os",
    "para",
    "por",
    "que",
    "qual",
    "quais",
    "um",
    "uma",
}
_TERM_EXPANSIONS = {
    "cao": {"dog", "dogs", "canine"},
    "cachorro": {"dog", "dogs", "canine"},
    "gato": {"cat", "cats", "feline"},
    "felino": {"cat", "cats", "feline"},
    "vomito": {"vomiting", "emesis"},
    "vomitos": {"vomiting", "emesis"},
    "diarreia": {"diarrhea"},
    "rim": {"kidney", "renal"},
    "rins": {"kidney", "renal"},
    "renal": {"kidney"},
    "creatinina": {"creatinine", "kidney", "renal"},
    "coracao": {"heart", "cardiac"},
    "cardiaco": {"heart", "cardiac"},
    "pele": {"skin", "dermatology"},
    "coceira": {"pruritus", "itch"},
    "dor": {"pain"},
    "febre": {"fever"},
    "convulsao": {"seizure"},
    "antibiotico": {"antibiotic", "antimicrobial"},
}
_SPECIES_TERMS = {
    "cao",
    "cachorro",
    "dog",
    "dogs",
    "canine",
    "gato",
    "felino",
    "cat",
    "cats",
    "feline",
}
_GENERIC_RETRIEVAL_TERMS = {
    "animal",
    "animals",
    "anos",
    "caso",
    "cite",
    "clinical",
    "clinico",
    "dados",
    "diferencie",
    "disponiveis",
    "evidencia",
    "evidencias",
    "exame",
    "exames",
    "falta",
    "faltam",
    "fato",
    "fatos",
    "forem",
    "hipotese",
    "hipoteses",
    "mais",
    "paciente",
    "priorizar",
    "proximo",
    "proximos",
    "relevante",
    "relevantes",
    "resposta",
    "study",
    "test",
    "teste",
    "uteis",
    "util",
    "veterinary",
}


def _tokens(value: Any) -> set[str]:
    normalized = (
        unicodedata.normalize("NFKD", str(value or ""))
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    base = {
        token
        for token in re.findall(r"[a-z0-9]{3,}", normalized.lower())
        if token not in _STOPWORDS
    }
    expanded = set(base)
    for token in base:
        expanded.update(_TERM_EXPANSIONS.get(token, set()))
    return expanded


def buscar_evidencias_clinicas_disponiveis(
    db: Session,
    *,
    pergunta: str,
    limite: int = 4,
) -> list[dict[str, Any]]:
    """Retrieve active eligible documents with source and curation traceability."""

    query_tokens = _tokens(pergunta)
    if not query_tokens:
        return []
    clinical_query_tokens = query_tokens - _SPECIES_TERMS - _GENERIC_RETRIEVAL_TERMS
    if not clinical_query_tokens:
        return []
    if not inspect(db.get_bind()).has_table("vet_conhecimento_documentos"):
        return []
    candidates = (
        db.query(DocumentoConhecimentoVet)
        .filter(
            DocumentoConhecimentoVet.status_revisao.in_(
                ["aprovado", AUTO_AVAILABLE_STATUS]
            ),
            DocumentoConhecimentoVet.ativo == True,  # noqa: E712
        )
        .order_by(
            DocumentoConhecimentoVet.publicado_em.desc().nullslast(),
            DocumentoConhecimentoVet.id.desc(),
        )
        .limit(500)
        .all()
    )

    ranked = []
    for document in candidates:
        title_tokens = _tokens(document.titulo)
        topic_tokens = _tokens(" ".join(document.temas or []))
        abstract_tokens = _tokens(document.resumo)
        document_tokens = title_tokens | topic_tokens | abstract_tokens
        clinical_matches = clinical_query_tokens & document_tokens
        if not clinical_matches:
            continue
        title_clinical_matches = clinical_query_tokens & title_tokens
        supporting_clinical_matches = clinical_query_tokens & (
            topic_tokens | abstract_tokens
        )
        if not title_clinical_matches and len(supporting_clinical_matches) < 2:
            # Um unico termo no resumo/MeSH pode ser apenas o nome de uma
            # linhagem laboratorial (ex.: "canine kidney cells"), sem relacao
            # clinica com o caso. Nesse cenario, e melhor nao citar o artigo.
            continue
        species_bonus = len(query_tokens & _SPECIES_TERMS & document_tokens)
        score = (
            5 * len(clinical_query_tokens & title_tokens)
            + 3 * len(clinical_query_tokens & topic_tokens)
            + len(clinical_query_tokens & abstract_tokens)
            + species_bonus
        )
        if score <= 0:
            continue
        ranked.append((score, document.publicado_em or date.min, document))

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    result = []
    for index, (_score, _published, document) in enumerate(
        ranked[: max(1, min(limite, 8))],
        start=1,
    ):
        result.append(
            {
                "ref": f"E{index}",
                "id": document.id,
                "fonte": document.fonte.codigo if document.fonte else "pubmed",
                "fonte_documento_id": document.fonte_documento_id,
                "titulo": document.titulo,
                "publicado_em": (
                    document.publicado_em.isoformat() if document.publicado_em else None
                ),
                "url": document.url,
                "doi": document.doi,
                "resumo": (document.resumo or "")[:1600],
                "status_revisao": document.status_revisao,
                "nivel_curadoria": (
                    "revisado_por_humano"
                    if document.status_revisao == "aprovado"
                    else "triagem_automatica_pubmed"
                ),
            }
        )
    return result


def buscar_evidencias_clinicas_aprovadas(
    db: Session,
    *,
    pergunta: str,
    limite: int = 4,
) -> list[dict[str, Any]]:
    """Backward-compatible alias for the previous public helper name."""
    return buscar_evidencias_clinicas_disponiveis(
        db,
        pergunta=pergunta,
        limite=limite,
    )
