from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_app_mobile_racao_service_nao_duplica_prefixo_api():
    source = (REPO_ROOT / "app-mobile/src/services/shop.service.ts").read_text(
        encoding="utf-8"
    )

    assert "api.post('/api/produtos/calculadora-racao'" not in source
    assert "api.post('/api/produtos/comparar-racoes'" not in source
    assert "api.post('/produtos/calculadora-racao'" in source
    assert "api.post('/produtos/comparar-racoes'" in source


def test_app_mobile_upload_foto_pet_deixa_axios_montar_multipart():
    source = (REPO_ROOT / "app-mobile/src/services/pets.service.ts").read_text(
        encoding="utf-8"
    )

    upload_start = source.index("export async function uploadFotoPet")
    upload_source = source[
        upload_start : source.index("export async function obterCarteirinhaPet")
    ]

    assert "Content-Type" not in upload_source
    assert "multipart/form-data" not in upload_source
    assert "api.post<Pet>(`/app/pets/${petId}/foto`, formData)" in upload_source


def test_app_mobile_form_pet_nao_engole_erro_de_upload_foto():
    source = (REPO_ROOT / "app-mobile/src/screens/pets/PetFormScreen.tsx").read_text(
        encoding="utf-8"
    )

    assert "catch (uploadErr: any)" in source
    assert "Foto nao salva" in source
    assert "return;" in source
    assert "catch {\n          // N" not in source
