from app.services.google_maps_service import limpar_endereco_para_maps


def test_limpar_endereco_para_maps_remove_complemento_e_rotulo_numero():
    endereco = "Rua das Flores, numero 123, Apto 45, Centro, Sao Paulo, SP"

    assert limpar_endereco_para_maps(endereco) == "Rua das Flores, 123, Centro, Sao Paulo, SP"


def test_limpar_endereco_para_maps_preserva_rua_numero_bairro_e_cidade():
    endereco = "Av Brasil, Número: 900, Jardim Paulista, Ribeirao Preto, SP, 14000-000"

    assert limpar_endereco_para_maps(endereco) == "Av Brasil, 900, Jardim Paulista, Ribeirao Preto, SP, 14000-000"
