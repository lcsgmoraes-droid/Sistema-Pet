import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import "../styles/CalculadoraRacao.css";

export default function CalculadoraRacao() {
  const [produtos, setProdutos] = useState([]);
  const [pets, setPets] = useState([]);
  const [loading, setLoading] = useState(false);

  // Formulário
  const [form, setForm] = useState({
    pet_id: "",
    pet_nome: "",
    produto_id: "",
    produto_nome: "",
    categoria_racao: "", // filhote, adulto, senior
    peso_pet_kg: "",
    idade_meses: "",
    nivel_atividade: "normal",
    // Filtros para comparativo
    classificacao: "",
    especies: "dog",
    produto_comparar_id: "",
    produto_comparar_nome: "",
  });

  // Resultado
  const [resultado, setResultado] = useState(null);
  const [comparativo, setComparativo] = useState([]);

  useEffect(() => {
    carregarProdutos();
    carregarPets();
  }, []);

  const carregarProdutos = async () => {
    try {
      console.log("🔍 Iniciando carregamento de produtos...");

      const response = await api.get("/produtos/");

      console.log("📡 Resposta da API:", {
        status: response.status,
        dataType: typeof response.data,
        isArray: Array.isArray(response.data),
        dataPreview:
          typeof response.data === "string"
            ? response.data.substring(0, 200)
            : "object",
      });

      // Se a resposta for string, tentar parsear
      let data = response.data;
      if (typeof data === "string") {
        console.warn("⚠️ API retornou string, tentando parsear JSON...");
        try {
          data = JSON.parse(data);
        } catch (e) {
          console.error("❌ Erro ao parsear JSON:", e);
          console.error("❌ Conteúdo recebido:", data.substring(0, 500));
          toast.error("Erro: resposta da API inválida");
          return;
        }
      }

      // A API retorna objeto paginado: {items: [], total: X}
      const listaProdutos = Array.isArray(data)
        ? data
        : data.items || data.produtos || [];
      console.log("📦 Total de produtos recebidos:", listaProdutos.length);
      console.log(
        "📦 Estrutura da resposta:",
        Array.isArray(data)
          ? "Array direto"
          : `Objeto com keys: ${Object.keys(data).join(", ")}`,
      );

      if (listaProdutos.length > 0) {
        console.log("📦 Estrutura do primeiro produto:", listaProdutos[0]);
      }

      // Filtrar apenas produtos com peso_embalagem
      const racoes = listaProdutos.filter(
        (p) => p.peso_embalagem && p.peso_embalagem > 0,
      );
      console.log("🥫 Rações encontradas:", racoes.length);
      console.log("📊 Total de produtos:", listaProdutos.length);

      if (racoes.length > 0) {
        console.log(
          "🥫 IDs das rações:",
          racoes.map((r) => `${r.id}-${r.nome}`),
        );
      } else {
        console.log(
          "⚠️ Produtos sem peso_embalagem:",
          listaProdutos.slice(0, 5).map((p) => ({
            id: p.id,
            nome: p.nome,
            peso_embalagem: p.peso_embalagem,
            categoria_racao: p.categoria_racao,
            classificacao_racao: p.classificacao_racao,
          })),
        );
      }

      setProdutos(racoes);

      if (racoes.length === 0 && listaProdutos.length > 0) {
        console.warn(
          "⚠️ Produtos encontrados, mas nenhum tem peso de embalagem configurado",
        );
        toast.error(
          `${listaProdutos.length} produtos encontrados, mas nenhum tem PESO DE EMBALAGEM configurado. ` +
            'Edite os produtos de ração e preencha o campo "Peso da Embalagem (kg)".',
          { duration: 6000 },
        );
      } else if (racoes.length === 0) {
        console.log("ℹ️ Nenhum produto encontrado");
        toast.error("Nenhum produto encontrado. Cadastre produtos primeiro.");
      }
    } catch (error) {
      console.error("❌ Erro ao carregar produtos:", error);
      console.error("❌ Detalhes:", error.response?.data || error.message);
      toast.error(
        `Erro ao carregar produtos: ${error.response?.data?.detail || error.message}`,
      );
    }
  };

  const carregarPets = async () => {
    try {
      const response = await api.get("/clientes/pets/todos");
      const listaPets = Array.isArray(response.data) ? response.data : [];
      setPets(listaPets);
      console.log("🐾 Pets carregados:", listaPets.length);
    } catch (error) {
      console.error("❌ Erro ao carregar pets:", error);
      // Não mostrar erro para não incomodar se não tiver pets
    }
  };

  const handlePetChange = (petId) => {
    const petSelecionado = pets.find((p) => p.id === parseInt(petId));

    if (petSelecionado) {
      // Calcular idade em meses a partir da data de nascimento
      let idadeMeses = "";
      if (petSelecionado.data_nascimento) {
        const nascimento = new Date(petSelecionado.data_nascimento);
        const hoje = new Date();
        const diffTime = Math.abs(hoje - nascimento);
        const diffMonths = Math.floor(diffTime / (1000 * 60 * 60 * 24 * 30.44)); // média de dias por mês
        idadeMeses = diffMonths.toString();
      }

      const especieTexto =
        petSelecionado.especie === "Cachorro"
          ? "dog"
          : petSelecionado.especie === "Gato"
            ? "cat"
            : form.especies;

      setForm({
        ...form,
        pet_id: petId,
        pet_nome: `${petSelecionado.nome} - ${petSelecionado.especie} ${petSelecionado.peso ? `(${petSelecionado.peso}kg)` : ""}`,
        peso_pet_kg: petSelecionado.peso || "",
        idade_meses: idadeMeses,
        especies: especieTexto,
      });

      toast.success(`Pet ${petSelecionado.nome} selecionado!`);
    } else {
      setForm({
        ...form,
        pet_id: "",
        peso_pet_kg: "",
        idade_meses: "",
      });
    }
  };

  const calcular = async () => {
    if (!form.peso_pet_kg) {
      toast.error("Informe o peso do pet");
      return;
    }

    // Validar idade obrigatória para ração de filhote
    if (form.categoria_racao === "filhote" && !form.idade_meses) {
      toast.error("⚠️ Idade é obrigatória para rações de filhote!");
      return;
    }

    try {
      setLoading(true);
      const response = await api.post("/api/produtos/calculadora-racao", {
        produto_id: form.produto_id ? parseInt(form.produto_id) : null,
        peso_pet_kg: parseFloat(form.peso_pet_kg),
        idade_meses: form.idade_meses ? parseInt(form.idade_meses) : null,
        nivel_atividade: form.nivel_atividade,
      });
      setResultado(response.data);
      setComparativo([]);
      toast.success("Cálculo realizado!");
    } catch (error) {
      console.error("Erro:", error);
      toast.error(error.response?.data?.detail || "Erro ao calcular");
    } finally {
      setLoading(false);
    }
  };

  const compararRacoes = async () => {
    if (!form.peso_pet_kg) {
      toast.error("Informe o peso do pet");
      return;
    }

    try {
      setLoading(true);

      // MODO 1x1: Se selecionou uma ração específica para comparar
      if (form.produto_comparar_id) {
        // Calcular SOMENTE para a ração selecionada no comparativo
        const calcResponse = await api.post("/api/produtos/calculadora-racao", {
          produto_id: parseInt(form.produto_comparar_id),
          peso_pet_kg: parseFloat(form.peso_pet_kg),
          idade_meses: form.idade_meses ? parseInt(form.idade_meses) : null,
          nivel_atividade: form.nivel_atividade,
        });

        const racaoComparar = calcResponse.data;

        // Se também selecionou uma ração principal, calcular ela também
        if (form.produto_id) {
          const calcPrincipal = await api.post(
            "/api/produtos/calculadora-racao",
            {
              produto_id: parseInt(form.produto_id),
              peso_pet_kg: parseFloat(form.peso_pet_kg),
              idade_meses: form.idade_meses ? parseInt(form.idade_meses) : null,
              nivel_atividade: form.nivel_atividade,
            },
          );

          // Evitar duplicatas: se selecionou a mesma ração
          if (calcPrincipal.data.produto_id === racaoComparar.produto_id) {
            setComparativo([calcPrincipal.data]);
            toast.success(`Mostrando cálculo da ração selecionada`);
          } else {
            // Mostrar SOMENTE essas duas rações: selecionada primeiro, depois a comparada
            const duasRacoes = [calcPrincipal.data, racaoComparar];
            setComparativo(duasRacoes);
            toast.success(`Comparando 2 rações selecionadas!`);
          }
        } else {
          // Se não tem ração principal, mostrar só a do comparativo
          setComparativo([racaoComparar]);
          toast.success(`Mostrando cálculo da ração selecionada`);
        }

        // Mantém o resultado individual visível
      } else {
        // MODO FILTROS: usar filtros de classificação e espécie
        const params = {
          peso_pet_kg: parseFloat(form.peso_pet_kg),
          nivel_atividade: form.nivel_atividade,
        };
        if (form.idade_meses) params.idade_meses = parseInt(form.idade_meses);
        if (form.classificacao) params.classificacao = form.classificacao;
        if (form.especies) params.especies = form.especies;

        const response = await api.post("/api/produtos/comparar-racoes", null, {
          params,
        });

        let todasRacoes = response.data.racoes || [];

        // Se há uma ração selecionada no campo principal, incluir ela sempre
        if (form.produto_id) {
          // Primeiro, remover a ração principal da lista se já estiver lá
          todasRacoes = todasRacoes.filter(
            (r) => r.produto_id !== parseInt(form.produto_id),
          );

          // Calcular a ração principal
          const calcPrincipal = await api.post(
            "/api/produtos/calculadora-racao",
            {
              produto_id: parseInt(form.produto_id),
              peso_pet_kg: parseFloat(form.peso_pet_kg),
              idade_meses: form.idade_meses ? parseInt(form.idade_meses) : null,
              nivel_atividade: form.nivel_atividade,
            },
          );

          const racaoPrincipal = calcPrincipal.data;

          // ORDENAR só as outras rações por custo-benefício
          todasRacoes.sort((a, b) => a.custo_por_dia - b.custo_por_dia);

          // Colocar ração principal SEMPRE no topo
          todasRacoes = [racaoPrincipal, ...todasRacoes];
        }

        // LIMITADOR: mostrar no máximo 10 rações
        const racoesLimitadas = todasRacoes.slice(0, 10);

        setComparativo(racoesLimitadas);
        // Mantém o resultado individual visível

        const totalRacoes = todasRacoes.length;
        if (totalRacoes === 0) {
          toast.error(
            "Nenhuma ração encontrada com esses filtros. Tente outros critérios.",
          );
        }
      }
    } catch (error) {
      console.error("Erro:", error);
      toast.error(error.response?.data?.detail || "Erro ao comparar");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="calculadora-racao-container">
      <div className="header">
        <h1>🥫 Calculadora de Ração</h1>
        <p>Calcule duração, custo/dia e compare produtos</p>
      </div>

      <div className="calculadora-grid">
        {/* Formulário */}
        <div className="form-card">
          <h2>📝 Dados do Pet</h2>

          {/* NOVO: Buscar Pet Cadastrado */}
          <div className="form-group">
            <label>🐾 Buscar Pet Cadastrado</label>
            <input
              type="text"
              list="pets-list"
              value={form.pet_nome || ""}
              onChange={(e) => {
                const nomePet = e.target.value;
                setForm({ ...form, pet_nome: nomePet });

                // Se digitou exatamente o nome de um pet, seleciona ele
                const petEncontrado = pets.find(
                  (p) =>
                    `${p.nome} - ${p.especie} ${p.peso ? `(${p.peso}kg)` : ""}` ===
                    nomePet,
                );
                if (petEncontrado) {
                  handlePetChange(petEncontrado.id);
                }
              }}
              placeholder="Digite ou selecione um pet"
              className="pet-select"
            />
            <datalist id="pets-list">
              {pets.map((pet) => (
                <option
                  key={pet.id}
                  value={`${pet.nome} - ${pet.especie} ${pet.peso ? `(${pet.peso}kg)` : ""}`}
                />
              ))}
            </datalist>
            <small className="form-hint">
              💡 Digite ou selecione um pet para preencher automaticamente peso
              e idade
            </small>
          </div>

          <div className="form-group">
            <label>Peso do Pet (kg) *</label>
            <input
              type="number"
              step="0.1"
              value={form.peso_pet_kg}
              onChange={(e) =>
                setForm({ ...form, peso_pet_kg: e.target.value })
              }
              placeholder="Ex: 8.5"
            />
          </div>

          <div className="form-group">
            <label>
              Idade (meses)
              {form.categoria_racao === "filhote" && (
                <span style={{ color: "#ff6b6b" }}> *</span>
              )}
            </label>
            <input
              type="number"
              value={form.idade_meses}
              onChange={(e) =>
                setForm({ ...form, idade_meses: e.target.value })
              }
              placeholder={
                form.categoria_racao === "filhote"
                  ? "Obrigatório para filhotes!"
                  : "Ex: 24 (opcional)"
              }
              required={form.categoria_racao === "filhote"}
              style={
                form.categoria_racao === "filhote"
                  ? { borderColor: "#ff6b6b", borderWidth: "2px" }
                  : {}
              }
            />
          </div>

          <div className="form-group">
            <label>Nível de Atividade</label>
            <select
              value={form.nivel_atividade}
              onChange={(e) =>
                setForm({ ...form, nivel_atividade: e.target.value })
              }
            >
              <option value="baixo">Baixo</option>
              <option value="normal">Normal</option>
              <option value="alto">Alto</option>
            </select>
          </div>

          <hr />

          <h3>🥫 Ração</h3>

          <div className="form-group">
            <label>Selecionar Ração</label>
            <input
              type="text"
              list="racoes-list"
              value={form.produto_nome || ""}
              onChange={(e) => {
                const nomeRacao = e.target.value;
                setForm({ ...form, produto_nome: nomeRacao });

                // Se digitou exatamente o nome de uma ração, seleciona ela
                const racaoEncontrada = produtos.find(
                  (p) =>
                    `${p.nome} - ${p.peso_embalagem}kg - R$ ${p.preco_venda}` ===
                    nomeRacao,
                );
                if (racaoEncontrada) {
                  setForm({
                    ...form,
                    produto_id: racaoEncontrada.id,
                    produto_nome: nomeRacao,
                    categoria_racao: racaoEncontrada.categoria_racao || "",
                  });
                }
              }}
              placeholder="Digite ou selecione uma ração"
            />
            <datalist id="racoes-list">
              {produtos.map((p) => (
                <option
                  key={p.id}
                  value={`${p.nome} - ${p.peso_embalagem}kg - R$ ${p.preco_venda}`}
                />
              ))}
            </datalist>
            {form.categoria_racao === "filhote" && (
              <small
                className="form-hint"
                style={{ color: "#ff6b6b", fontWeight: "bold" }}
              >
                ⚠️ Ração de filhote - idade é obrigatória!
              </small>
            )}
          </div>

          <div className="button-group">
            <button
              onClick={calcular}
              disabled={loading}
              className="btn-primary"
            >
              {loading ? "Calculando..." : "📊 Calcular"}
            </button>
          </div>

          <hr />

          <h3>🔍 Comparar Rações</h3>

          <div className="info-box">
            <strong>💡 Dica:</strong> Escolha UMA das opções abaixo:
            <br />• Selecione uma ração específica para ver como ela se compara
            <br />• OU use os filtros gerais para ver todas de uma categoria
          </div>

          {/* NOVO: Selecionar uma ração específica para comparar */}
          <div className="form-group">
            <label>⭐ Comparar Ração Específica</label>
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                type="text"
                list="racoes-comparar-list"
                value={form.produto_comparar_nome || ""}
                onChange={(e) => {
                  const nomeRacao = e.target.value;

                  // Se limpar o campo
                  if (nomeRacao === "") {
                    setForm({
                      ...form,
                      produto_comparar_id: "",
                      produto_comparar_nome: "",
                    });
                    return;
                  }

                  setForm({
                    ...form,
                    produto_comparar_nome: nomeRacao,
                    classificacao: "",
                  });

                  // Se digitou exatamente o nome de uma ração, seleciona ela
                  const racaoEncontrada = produtos.find(
                    (p) =>
                      `${p.nome} - ${p.classificacao_racao} - R$ ${p.preco_venda}` ===
                      nomeRacao,
                  );
                  if (racaoEncontrada) {
                    setForm({
                      ...form,
                      produto_comparar_id: racaoEncontrada.id,
                      produto_comparar_nome: nomeRacao,
                      classificacao: "",
                    });
                  }
                }}
                placeholder="Digite ou selecione uma ração"
                disabled={form.classificacao !== ""}
                style={{ flex: 1 }}
              />
              {form.produto_comparar_nome && (
                <button
                  type="button"
                  onClick={() =>
                    setForm({
                      ...form,
                      produto_comparar_id: "",
                      produto_comparar_nome: "",
                    })
                  }
                  className="btn-clear"
                  title="Limpar seleção"
                >
                  ✕
                </button>
              )}
            </div>
            <datalist id="racoes-comparar-list">
              {produtos.map((p) => (
                <option
                  key={p.id}
                  value={`${p.nome} - ${p.classificacao_racao} - R$ ${p.preco_venda}`}
                />
              ))}
            </datalist>
            {form.classificacao && (
              <small className="form-warning">
                ⚠️ Limpe o filtro de classificação para usar esta opção
              </small>
            )}
            {!form.produto_comparar_id && !form.classificacao && (
              <small className="form-hint">
                💡 Deixe vazio para comparar por classificação abaixo
              </small>
            )}
          </div>

          <div className="divider-text">OU</div>

          <div className="form-group">
            <label>📋 Filtro por Classificação</label>
            <div style={{ display: "flex", gap: "8px" }}>
              <select
                value={form.classificacao}
                onChange={(e) =>
                  setForm({
                    ...form,
                    classificacao: e.target.value,
                    produto_comparar_id: "",
                    produto_comparar_nome: "",
                  })
                }
                disabled={form.produto_comparar_id !== ""}
                style={{ flex: 1 }}
              >
                <option value="">Todas as classificações</option>
                <option value="super_premium">Super Premium</option>
                <option value="premium">Premium</option>
                <option value="especial">Especial</option>
                <option value="standard">Standard</option>
              </select>
              {form.classificacao && (
                <button
                  type="button"
                  onClick={() => setForm({ ...form, classificacao: "" })}
                  className="btn-clear"
                  title="Limpar filtro"
                >
                  ✕
                </button>
              )}
            </div>
            {form.produto_comparar_id && (
              <small className="form-warning">
                ⚠️ Limpe a ração específica acima para usar este filtro
              </small>
            )}
          </div>

          <div className="form-group">
            <label>Espécie</label>
            <select
              value={form.especies}
              onChange={(e) => setForm({ ...form, especies: e.target.value })}
            >
              <option value="dog">🐶 Cães</option>
              <option value="cat">🐱 Gatos</option>
              <option value="both">Ambos</option>
            </select>
          </div>

          <div className="button-group">
            <button
              onClick={compararRacoes}
              disabled={loading}
              className="btn-secondary"
            >
              {loading ? "Comparando..." : "🔍 Comparar Todas"}
            </button>
          </div>
        </div>

        <div>
          {/* Resultado Individual */}
          {resultado && (
            <div className="result-card">
              <h2>📊 Resultado do Cálculo</h2>
              <div className="result-header">
                <h3>{resultado.produto_nome}</h3>
                {resultado.classificacao && (
                  <span className={`badge badge-${resultado.classificacao}`}>
                    {resultado.classificacao.replace("_", " ")}
                  </span>
                )}
              </div>

              <div className="result-stats">
                <div className="stat">
                  <span className="label">Peso Embalagem</span>
                  <span className="value">
                    {resultado.peso_embalagem_kg} kg
                  </span>
                </div>
                <div className="stat">
                  <span className="label">Preço</span>
                  <span className="value">R$ {resultado.preco.toFixed(2)}</span>
                </div>
              </div>

              <div className="result-details">
                <div className="detail-item">
                  <span className="icon">⏱️</span>
                  <div>
                    <strong>Duração</strong>
                    <p>
                      {resultado.duracao_dias} dias ({resultado.duracao_meses}{" "}
                      meses)
                    </p>
                  </div>
                </div>
                <div className="detail-item">
                  <span className="icon">🥫</span>
                  <div>
                    <strong>Consumo diário</strong>
                    <p>{resultado.quantidade_diaria_g}g</p>
                  </div>
                </div>
                <div className="detail-item">
                  <span className="icon">💰</span>
                  <div>
                    <strong>Custo/kg</strong>
                    <p>R$ {resultado.custo_por_kg.toFixed(2)}</p>
                  </div>
                </div>
                <div className="detail-item">
                  <span className="icon">📅</span>
                  <div>
                    <strong>Custo/dia</strong>
                    <p>R$ {resultado.custo_por_dia.toFixed(2)}</p>
                  </div>
                </div>
                <div className="detail-item">
                  <span className="icon">📆</span>
                  <div>
                    <strong>Custo mensal</strong>
                    <p>R$ {resultado.custo_mensal.toFixed(2)}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Comparativo - LOGO ABAIXO DO RESULTADO */}
          {comparativo.length > 0 && (
            <div className="comparativo-card">
              <h2>🏆 Comparativo de Rações ({comparativo.length})</h2>
              <p className="subtitle">
                Ordenado por melhor custo-benefício (menor custo diário)
              </p>

              <div className="comparativo-list">
                {(() => {
                  // Encontrar menor custo diário
                  const menorCusto = Math.min(
                    ...comparativo.map((r) => r.custo_por_dia),
                  );

                  return comparativo.map((item, index) => {
                    // ⭐ Ração BASE (do campo "Selecionar Ração")
                    const isSelecionada =
                      form.produto_id &&
                      item.produto_id === parseInt(form.produto_id);
                    // 🏆 Melhor custo-benefício
                    const isMelhor = item.custo_por_dia === menorCusto;

                    return (
                      <div
                        key={item.produto_id}
                        className={`comparativo-item ${isMelhor ? "melhor" : ""} ${isSelecionada ? "selecionada" : ""}`}
                      >
                        {(isSelecionada || isMelhor) && (
                          <div className="comparativo-badges">
                            {isSelecionada && (
                              <span className="badge-selecionada">
                                ⭐ Selecionada
                              </span>
                            )}
                            {isMelhor && (
                              <span className="badge-melhor">
                                🏆 Melhor Custo-Benefício
                              </span>
                            )}
                          </div>
                        )}

                        <div className="item-header">
                          <div>
                            <h4>{item.produto_nome}</h4>
                            <div
                              style={{
                                display: "flex",
                                gap: "8px",
                                alignItems: "center",
                                marginTop: "4px",
                              }}
                            >
                              {item.classificacao && (
                                <span
                                  className={`badge badge-${item.classificacao}`}
                                >
                                  {item.classificacao.replace("_", " ")}
                                </span>
                              )}
                              <span
                                style={{
                                  fontSize: "13px",
                                  color: "#64748b",
                                  backgroundColor: "#f1f5f9",
                                  padding: "2px 8px",
                                  borderRadius: "4px",
                                }}
                              >
                                🍽️ {item.quantidade_diaria_g}g/dia
                              </span>
                            </div>
                          </div>
                          <div className="item-price">
                            R$ {item.preco.toFixed(2)}
                          </div>
                        </div>

                        <div className="item-stats">
                          <div className="stat-small">
                            <span className="label">Peso</span>
                            <span>{item.peso_embalagem_kg}kg</span>
                          </div>
                          <div className="stat-small">
                            <span className="label">Duração</span>
                            <span>{item.duracao_dias}d</span>
                          </div>
                          <div className="stat-small highlight">
                            <span className="label">Custo/dia</span>
                            <span>R$ {item.custo_por_dia.toFixed(2)}</span>
                          </div>
                          <div className="stat-small">
                            <span className="label">Custo/mês</span>
                            <span>R$ {item.custo_mensal.toFixed(2)}</span>
                          </div>
                        </div>

                        {/* Explicação detalhada para o melhor */}
                        {isMelhor && comparativo.length > 1 && (
                          <div
                            style={{
                              marginTop: "12px",
                              padding: "12px",
                              backgroundColor: "#ecfdf5",
                              borderLeft: "3px solid #10b981",
                              borderRadius: "4px",
                            }}
                          >
                            <p
                              style={{
                                margin: "0 0 6px 0",
                                fontSize: "13px",
                                fontWeight: "600",
                                color: "#065f46",
                              }}
                            >
                              ✨ Por que esta é a melhor opção?
                            </p>
                            <p
                              style={{
                                margin: "0",
                                fontSize: "13px",
                                color: "#047857",
                                lineHeight: "1.5",
                              }}
                            >
                              Apesar de{" "}
                              {item.classificacao === "premium" ||
                              item.classificacao === "super_premium"
                                ? `ter um preço mais alto (R$ ${item.preco.toFixed(2)})`
                                : `custar R$ ${item.preco.toFixed(2)}`}
                              , esta ração{" "}
                              {item.classificacao === "super_premium"
                                ? "super premium é muito concentrada em nutrientes"
                                : item.classificacao === "premium"
                                  ? "premium tem melhor densidade nutricional"
                                  : "tem excelente eficiência alimentar"}
                              , então seu pet consome apenas{" "}
                              <strong>
                                {item.quantidade_diaria_g}g por dia
                              </strong>
                              .
                              {comparativo[1] && (
                                <>
                                  {" "}
                                  Em comparação, a segunda opção requer{" "}
                                  <strong>
                                    {comparativo[1].quantidade_diaria_g}g/dia
                                  </strong>
                                  , resultando em um custo diário{" "}
                                  <strong>
                                    R${" "}
                                    {(
                                      comparativo[1].custo_por_dia -
                                      item.custo_por_dia
                                    ).toFixed(2)}{" "}
                                    maior
                                  </strong>
                                  (R$ {item.custo_por_dia.toFixed(2)} vs R${" "}
                                  {comparativo[1].custo_por_dia.toFixed(2)}).
                                </>
                              )}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
