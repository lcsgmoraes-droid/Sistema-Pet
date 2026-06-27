from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_app_mobile_calculadora_nao_usa_rotas_admin_que_deslogam():
    sources = {
        path: (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in [
            "app-mobile/src/services/shop.service.ts",
            "app-mobile/src/services/pets.service.ts",
            "app-mobile/src/screens/pets/FoodCalculatorScreen.tsx",
        ]
    }

    for source in sources.values():
        assert "api.post('/api/produtos/calculadora-racao'" not in source
        assert "api.post('/api/produtos/comparar-racoes'" not in source
        assert "api.post('/produtos/calculadora-racao'" not in source
        assert (
            "api.get<CalculadoraResultado>('/produtos/calculadora-racao'" not in source
        )
        assert "api.post('/produtos/comparar-racoes'" not in source

    screen_source = sources["app-mobile/src/screens/pets/FoodCalculatorScreen.tsx"]
    assert "calcularRacaoLocal(" in screen_source
    assert "compararRacoesLocal(" in screen_source
    assert "calcularRacaoComProduto" not in screen_source
    assert "compararRacoesCategoria" not in screen_source


def test_app_mobile_calculadora_usa_calculo_local_sem_api():
    source = (REPO_ROOT / "app-mobile/src/services/shop.service.ts").read_text(
        encoding="utf-8"
    )

    assert "export function calcularRacaoLocal" in source
    assert "export function compararRacoesLocal" in source
    assert "pesoPetKg * 1000 * 0.025" in source
    assert "custo_mensal" in source


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


def test_app_mobile_form_pet_avisa_ao_sair_com_foto_pendente():
    source = (REPO_ROOT / "app-mobile/src/screens/pets/PetFormScreen.tsx").read_text(
        encoding="utf-8"
    )

    assert "beforeRemove" in source
    assert "Foto ainda nao salva" in source
    assert "Salvar agora" in source
    assert "Descartar foto" in source
    assert "navigation.dispatch(e.data.action)" in source


def test_app_mobile_form_pet_mantem_editor_nativo_com_orientacao():
    source = (REPO_ROOT / "app-mobile/src/screens/pets/PetFormScreen.tsx").read_text(
        encoding="utf-8"
    )

    assert "allowsEditing: true" in source
    assert "aspect: [1, 1]" in source
    assert "Cortar confirma o enquadramento" in source
    assert "Foto pronta para salvar" in source
    assert "Salvar foto" in source
