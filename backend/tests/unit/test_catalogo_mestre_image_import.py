from pathlib import Path

from PIL import Image

from app.services.catalogo_mestre_image_import import (
    CatalogImageCandidate,
    build_image_import_plan,
    discover_image_candidates,
)


def _candidate(filename: str, gtin: str, file_hash: str) -> CatalogImageCandidate:
    return CatalogImageCandidate(
        path=Path(filename),
        filename=filename,
        gtin=gtin,
        label="Produto",
        status="valido",
        sha256=file_hash,
        width=100,
        height=100,
        size_bytes=1000,
        image_format="JPEG",
    )


def test_discover_validates_filename_checksum_and_real_image(tmp_path):
    valid = tmp_path / "7891000244753_DOG CHOW FILHOTE CARNE 100G.png"
    Image.new("RGB", (40, 30), "white").save(valid)
    invalid_gtin = tmp_path / "7891000244754_GTIN ERRADO.jpg"
    Image.new("RGB", (10, 10), "white").save(invalid_gtin)
    no_gtin = tmp_path / "produto-sem-ean.webp"
    Image.new("RGB", (10, 10), "white").save(no_gtin)
    (tmp_path / "relatorio_download.csv").write_text(
        "nome,ean,fonte,arquivo\n"
        "Dog Chow,7891000244753,Busca web,"
        '"C:\\\\lote\\\\7891000244753_DOG CHOW FILHOTE CARNE 100G.png"\n',
        encoding="utf-8",
    )

    candidates = discover_image_candidates(tmp_path)
    by_name = {candidate.filename: candidate for candidate in candidates}

    assert by_name[valid.name].status == "valido"
    assert by_name[valid.name].gtin == "7891000244753"
    assert by_name[valid.name].width == 40
    assert by_name[valid.name].height == 30
    assert by_name[valid.name].sha256
    assert by_name[valid.name].reported_source == "Busca web"
    assert by_name[invalid_gtin.name].status == "gtin_invalido"
    assert by_name[no_gtin.name].status == "nome_sem_gtin"
    assert "relatorio_download.csv" not in by_name


def test_plan_never_creates_missing_products_and_respects_scope_and_target():
    candidates = [
        _candidate("7891000244753_RACAO.jpg", "7891000244753", "a" * 64),
        _candidate("742832524896_AREIA.jpg", "742832524896", "b" * 64),
        _candidate("850006715398_CHURU.jpg", "850006715398", "c" * 64),
        _candidate("4007221055259_DRONTAL.jpg", "4007221055259", "d" * 64),
    ]
    masters = [
        {
            "id": 1,
            "gtin": "7891000244753",
            "nome": "Dog Chow",
            "tipo_catalogo": "racao",
            "imagem_meta_quantidade": 5,
        },
        {
            "id": 2,
            "gtin": "742832524896",
            "nome": "Areia",
            "tipo_catalogo": "areia_sanitaria",
            "imagem_meta_quantidade": 5,
        },
        {
            "id": 3,
            "gtin": "850006715398",
            "nome": "Brinquedo cadastrado errado",
            "tipo_catalogo": "outro",
            "imagem_meta_quantidade": 5,
        },
    ]
    images = [
        {
            "produto_id": 2,
            "hash_arquivo": f"existing-{index}",
            "ordem": index,
            "ativo": True,
            "status_revisao": "aprovada",
        }
        for index in range(5)
    ]

    plan = build_image_import_plan(candidates, masters, images)
    by_gtin = {item.candidate.gtin: item for item in plan}

    assert by_gtin["7891000244753"].status == "pronto_para_estagio"
    assert by_gtin["742832524896"].status == "meta_de_imagens_atingida"
    assert by_gtin["850006715398"].status == "produto_fora_do_escopo"
    assert by_gtin["4007221055259"].status == "sem_produto_no_mestre"


def test_plan_blocks_duplicate_hash_and_ambiguous_gtin():
    candidates = [
        _candidate("5420036914952_CAPSTAR.jpg", "5420036914952", "a" * 64),
        _candidate("742832524896_AREIA.jpg", "742832524896", "b" * 64),
    ]
    masters = [
        {
            "id": 10,
            "gtin": "5420036914952",
            "nome": "Capstar",
            "tipo_catalogo": "medicamento",
            "imagem_meta_quantidade": 5,
        },
        {
            "id": 20,
            "gtin": "742832524896",
            "nome": "Areia A",
            "tipo_catalogo": "areia_sanitaria",
            "imagem_meta_quantidade": 5,
        },
        {
            "id": 21,
            "gtin": "742832524896",
            "nome": "Areia B",
            "tipo_catalogo": "areia_sanitaria",
            "imagem_meta_quantidade": 5,
        },
    ]
    images = [
        {
            "produto_id": 10,
            "hash_arquivo": "a" * 64,
            "ordem": 0,
            "ativo": False,
            "status_revisao": "pendente",
        }
    ]

    plan = build_image_import_plan(candidates, masters, images)

    assert plan[0].status == "imagem_duplicada_no_produto"
    assert plan[1].status == "gtin_ambiguo_no_mestre"


def test_stage_keeps_file_private_inactive_and_pending(tmp_path):
    source = tmp_path / "5420036914952_CAPSTAR.jpg"
    Image.new("RGB", (20, 30), "white").save(source)
    discovered = discover_image_candidates(tmp_path)[0]
    plan = build_image_import_plan(
        [discovered],
        [
            {
                "id": 10,
                "gtin": "5420036914952",
                "nome": "Capstar",
                "tipo_catalogo": "medicamento",
                "imagem_meta_quantidade": 5,
            }
        ],
        [],
    )
    staging_root = tmp_path / "seguro" / "catalogo_mestre_pendente"

    class FakeDb:
        def __init__(self):
            self.added = []
            self.flushed = False

        def add(self, value):
            self.added.append(value)

        def flush(self):
            self.flushed = True

    db = FakeDb()

    from app.services.catalogo_mestre_image_import import stage_image_import

    staged = stage_image_import(
        db,
        plan,
        source_ref="drive-folder-id",
        staging_dir=staging_root,
    )

    assert staged == 1
    assert db.flushed is True
    assert len(db.added) == 1
    image = db.added[0]
    assert image.ativo is False
    assert image.status_revisao == "pendente"
    assert image.direitos_uso_status == "nao_verificado"
    assert image.arquivo_url is None
    assert image.metadados["protegida_de_publicacao"] is True
    assert len(list(staging_root.rglob("*.jpg"))) == 1
