from app.services import ncm_oficial_service as service


def test_monta_apenas_ncm_completo_e_preserva_contexto_hierarquico():
    itens = service._montar_itens(
        [
            {"Codigo": "39", "Descricao": "Plásticos e suas obras"},
            {"Codigo": "39.26", "Descricao": "Outras obras de plástico"},
            {"Codigo": "3926.90.90", "Descricao": "-- Outras"},
        ]
    )

    assert itens == [
        {
            "ncm": "39269090",
            "descricao": "Outras",
            "descricao_hierarquica": (
                "Plásticos e suas obras > Outras obras de plástico > Outras"
            ),
            "texto_busca": "plasticos e suas obras outras obras de plastico outras",
        }
    ]


def test_pesquisa_codigo_exato_tem_prioridade(monkeypatch):
    monkeypatch.setattr(
        service,
        "obter_tabela_ncm_oficial",
        lambda: {
            "itens": [
                {
                    "ncm": "23091000",
                    "descricao": "Alimentos para cães ou gatos",
                    "descricao_hierarquica": "Preparações > Alimentos para cães ou gatos",
                    "texto_busca": "preparacoes alimentos para caes ou gatos",
                },
                {
                    "ncm": "39269090",
                    "descricao": "Outras obras de plástico",
                    "descricao_hierarquica": "Plásticos > Outras obras de plástico",
                    "texto_busca": "plasticos outras obras de plastico",
                },
            ],
            "atualizado_em": "Vigente em 15/09/2026",
            "ato": "Resolução de teste",
        },
    )

    resultado = service.pesquisar_ncm_oficial("23091000", limite=2)

    assert resultado["resultados"][0]["ncm"] == "23091000"
    assert resultado["resultados"][0]["score"] == 100
    assert resultado["atualizado_em"] == "Vigente em 15/09/2026"


def test_pesquisa_por_descricao_encontra_candidato_oficial(monkeypatch):
    monkeypatch.setattr(
        service,
        "obter_tabela_ncm_oficial",
        lambda: {
            "itens": [
                {
                    "ncm": "23091000",
                    "descricao": "Alimentos para cães ou gatos",
                    "descricao_hierarquica": "Preparações > Alimentos para cães ou gatos",
                    "texto_busca": "preparacoes alimentos para caes ou gatos",
                }
            ],
            "atualizado_em": None,
            "ato": None,
        },
    )

    resultado = service.pesquisar_ncm_oficial("alimento para cães", limite=3)

    assert resultado["resultados"][0]["ncm"] == "23091000"
    assert resultado["resultados"][0]["score"] >= 70


def test_cache_persistente_evitar_download_a_cada_processo(monkeypatch, tmp_path):
    cache_path = tmp_path / "ncm_oficial.json"
    monkeypatch.setattr(service, "NCM_CACHE_PATH", cache_path)
    chamadas = []

    def baixar():
        chamadas.append(True)
        return {
            "carregado_em": 1.0,
            "baixado_em_epoch": service.time.time(),
            "atualizado_em": "Vigente hoje",
            "ato": "Ato oficial",
            "itens": [
                {
                    "ncm": "23091000",
                    "descricao": "Alimentos para cães ou gatos",
                    "descricao_hierarquica": "Alimentos para cães ou gatos",
                    "texto_busca": "alimentos para caes ou gatos",
                }
            ],
        }

    monkeypatch.setattr(service, "_baixar_tabela", baixar)
    service.limpar_cache_ncm_oficial()
    primeira = service.obter_tabela_ncm_oficial()
    service.limpar_cache_ncm_oficial()
    segunda = service.obter_tabela_ncm_oficial()

    assert primeira["itens"] == segunda["itens"]
    assert len(chamadas) == 1
    assert cache_path.exists()
