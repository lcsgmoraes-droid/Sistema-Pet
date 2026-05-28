import CustomerIdentity from "../../components/ui/CustomerIdentity";
import ProductIdentity from "../../components/ui/ProductIdentity";

function RotaVendaDetalhes({ loading, venda, onFechar }) {
  return (
                <div
                  style={{
                    marginTop: 0,
                    marginBottom: 15,
                    padding: 15,
                    backgroundColor: "#f8f9fa",
                    borderRadius: 8,
                    border: "2px solid #007BFF",
                    boxShadow: "0 2px 8px rgba(0,123,255,0.2)",
                  }}
                >
                  {loading ? (
                    <div
                      style={{
                        textAlign: "center",
                        color: "#666",
                        padding: 20,
                      }}
                    >
                      Carregando detalhes da venda...
                    </div>
                  ) : venda ? (
                    <>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          marginBottom: 15,
                          borderBottom: "2px solid #007BFF",
                          paddingBottom: 10,
                        }}
                      >
                        <h4 style={{ margin: 0, color: "#007BFF" }}>
                          🧾 Detalhes da Venda #{venda.id}
                        </h4>
                        <button
                          onClick={onFechar}
                          style={{
                            background: "#dc3545",
                            color: "#fff",
                            border: "none",
                            borderRadius: 4,
                            padding: "6px 12px",
                            cursor: "pointer",
                            fontWeight: "bold",
                            fontSize: 13,
                          }}
                        >
                          ✕ Fechar
                        </button>
                      </div>

                      {/* Informações do Cliente */}
                      <div
                        style={{
                          backgroundColor: "#e7f3ff",
                          padding: 12,
                          borderRadius: 6,
                          marginBottom: 15,
                          border: "1px solid #007BFF",
                        }}
                      >
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "1fr 1fr",
                            gap: 10,
                            fontSize: 14,
                          }}
                        >
                          <div>
                            <strong>👤 Cliente:</strong>{" "}
                            <CustomerIdentity
                              code={venda.cliente?.codigo || venda.cliente_id || venda.cliente?.id}
                              customer={venda.cliente}
                              fallback="N/A"
                              layout="inline"
                              name={venda.nome_cliente}
                              nameClassName="font-medium text-slate-800"
                              record={venda}
                            />
                          </div>
                          <div>
                            <strong>📅 Data:</strong>{" "}
                            {venda.data_venda
                              ? new Date(
                                  venda.data_venda,
                                ).toLocaleString("pt-BR")
                              : "N/A"}
                          </div>

                          {venda.cliente?.telefone && (
                            <div>
                              <strong>📞 Telefone:</strong>{" "}
                              {venda.cliente.telefone}
                            </div>
                          )}
                          {venda.cliente?.celular && (
                            <div>
                              <strong>📱 Celular:</strong>{" "}
                              {venda.cliente.celular}
                            </div>
                          )}
                          {venda.cliente?.email && (
                            <div style={{ gridColumn: "1 / -1" }}>
                              <strong>📧 Email:</strong>{" "}
                              {venda.cliente.email}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Informações Financeiras */}
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr 1fr",
                          gap: 10,
                          fontSize: 14,
                          marginBottom: 15,
                        }}
                      >
                        <div
                          style={{
                            padding: 10,
                            backgroundColor: "#d4edda",
                            borderRadius: 4,
                            border: "1px solid #28a745",
                          }}
                        >
                          <div
                            style={{
                              fontSize: 11,
                              color: "#155724",
                              marginBottom: 3,
                            }}
                          >
                            VALOR TOTAL
                          </div>
                          <div
                            style={{
                              fontWeight: "bold",
                              fontSize: 16,
                              color: "#155724",
                            }}
                          >
                            R${" "}
                            {parseFloat(
                              venda.valor_total ||
                                venda.total ||
                                0,
                            ).toFixed(2)}
                          </div>
                        </div>
                        <div
                          style={{
                            padding: 10,
                            backgroundColor: "#fff",
                            borderRadius: 4,
                            border: "1px solid #ddd",
                          }}
                        >
                          <div
                            style={{
                              fontSize: 11,
                              color: "#666",
                              marginBottom: 3,
                            }}
                          >
                            PAGAMENTO
                          </div>
                          <div style={{ fontWeight: "bold", fontSize: 14 }}>
                            {venda.forma_pagamento || "N/A"}
                          </div>
                        </div>
                        <div
                          style={{
                            padding: 10,
                            backgroundColor: "#fff",
                            borderRadius: 4,
                            border: "1px solid #ddd",
                          }}
                        >
                          <div
                            style={{
                              fontSize: 11,
                              color: "#666",
                              marginBottom: 3,
                            }}
                          >
                            STATUS
                          </div>
                          <div style={{ fontWeight: "bold", fontSize: 14 }}>
                            {venda.status_pagamento || "N/A"}
                          </div>
                        </div>
                      </div>

                      {venda.endereco_entrega && (
                        <div
                          style={{
                            padding: 12,
                            backgroundColor: "#e3f2fd",
                            borderRadius: 6,
                            marginBottom: 15,
                            border: "1px solid #2196F3",
                          }}
                        >
                          <div
                            style={{
                              fontWeight: "bold",
                              marginBottom: 5,
                              color: "#1976D2",
                            }}
                          >
                            📍 Endereço de Entrega
                          </div>
                          <div style={{ color: "#424242", fontSize: 14 }}>
                            {venda.endereco_entrega}
                          </div>
                        </div>
                      )}

                      {venda.observacoes && (
                        <div
                          style={{
                            padding: 12,
                            backgroundColor: "#fff3cd",
                            borderRadius: 6,
                            marginBottom: 15,
                            border: "1px solid #ffc107",
                          }}
                        >
                          <div
                            style={{
                              fontWeight: "bold",
                              marginBottom: 5,
                              color: "#f57c00",
                            }}
                          >
                            💬 Observações
                          </div>
                          <div style={{ color: "#424242", fontSize: 14 }}>
                            {venda.observacoes}
                          </div>
                        </div>
                      )}

                      {venda.itens &&
                        venda.itens.length > 0 && (
                          <div>
                            <div
                              style={{
                                fontWeight: "bold",
                                fontSize: 15,
                                marginBottom: 10,
                                color: "#424242",
                              }}
                            >
                              🛒 Itens da Venda ({venda.itens.length})
                            </div>
                            <div
                              style={{
                                backgroundColor: "#fff",
                                borderRadius: 6,
                                border: "1px solid #ddd",
                                overflow: "hidden",
                                boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                              }}
                            >
                              {venda.itens.map((item, idx) => (
                                <div
                                  key={idx}
                                  style={{
                                    padding: 12,
                                    borderBottom:
                                      idx < venda.itens.length - 1
                                        ? "1px solid #eee"
                                        : "none",
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                    backgroundColor:
                                      idx % 2 === 0 ? "#fafafa" : "#fff",
                                  }}
                                >
                                  <div style={{ flex: 1 }}>
                                    <ProductIdentity
                                      code={item.produto?.codigo || item.produto_codigo}
                                      name={
                                        item.produto?.nome ||
                                        item.servico?.nome ||
                                        item.produto_nome ||
                                        item.servico_descricao ||
                                        "Item"
                                      }
                                      product={item}
                                      nameClassName="font-semibold text-slate-800"
                                    />
                                  </div>
                                  <div
                                    style={{
                                      textAlign: "right",
                                      minWidth: 120,
                                    }}
                                  >
                                    <div
                                      style={{
                                        color: "#666",
                                        fontSize: 13,
                                        marginBottom: 2,
                                      }}
                                    >
                                      {item.quantidade} × R${" "}
                                      {parseFloat(
                                        item.valor_unitario ||
                                          item.preco_unitario ||
                                          0,
                                      ).toFixed(2)}
                                    </div>
                                    <div
                                      style={{
                                        fontSize: 15,
                                        color: "#28a745",
                                        fontWeight: "bold",
                                      }}
                                    >
                                      R${" "}
                                      {parseFloat(
                                        (item.quantidade || 0) *
                                          (item.valor_unitario ||
                                            item.preco_unitario ||
                                            0),
                                      ).toFixed(2)}
                                    </div>
                                  </div>
                                </div>
                              ))}

                              {/* Total geral */}
                              <div
                                style={{
                                  padding: 14,
                                  backgroundColor: "#1976D2",
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "center",
                                  color: "#fff",
                                }}
                              >
                                <span
                                  style={{ fontWeight: "bold", fontSize: 16 }}
                                >
                                  TOTAL DA VENDA
                                </span>
                                <span
                                  style={{ fontWeight: "bold", fontSize: 18 }}
                                >
                                  R${" "}
                                  {parseFloat(
                                    venda.valor_total ||
                                      venda.total ||
                                      0,
                                  ).toFixed(2)}
                                </span>
                              </div>
                            </div>
                          </div>
                        )}
                    </>
                  ) : null}
                </div>
  );
}

export default RotaVendaDetalhes;
