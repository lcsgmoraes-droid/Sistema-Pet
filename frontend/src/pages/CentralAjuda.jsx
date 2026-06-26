/**
 * CentralAjuda.jsx
 * Base de conhecimento completa do Sistema Pet.
 * Pesquisável por palavra-chave, organizada por módulo.
 */
import { useMemo, useState } from "react";
import { FiBookOpen, FiChevronDown, FiChevronUp, FiSearch } from "react-icons/fi";

import { BASE_CONHECIMENTO } from "./centralAjuda/centralAjudaKnowledge";

/* ──────────────────────────────────────────────────────────────
   BASE DE CONHECIMENTO — adicione artigos aqui
────────────────────────────────────────────────────────────── */
const COR_CLASSES = {
  indigo: {
    bg: "bg-indigo-50",
    text: "text-indigo-700",
    border: "border-indigo-200",
    icon: "text-indigo-500",
    tab: "bg-indigo-600 text-white",
  },
  blue: {
    bg: "bg-blue-50",
    text: "text-blue-700",
    border: "border-blue-200",
    icon: "text-blue-500",
    tab: "bg-blue-600 text-white",
  },
  green: {
    bg: "bg-green-50",
    text: "text-green-700",
    border: "border-green-200",
    icon: "text-green-500",
    tab: "bg-green-600 text-white",
  },
  orange: {
    bg: "bg-orange-50",
    text: "text-orange-700",
    border: "border-orange-200",
    icon: "text-orange-500",
    tab: "bg-orange-600 text-white",
  },
  yellow: {
    bg: "bg-yellow-50",
    text: "text-yellow-700",
    border: "border-yellow-200",
    icon: "text-yellow-500",
    tab: "bg-yellow-500 text-white",
  },
  purple: {
    bg: "bg-purple-50",
    text: "text-purple-700",
    border: "border-purple-200",
    icon: "text-purple-500",
    tab: "bg-purple-600 text-white",
  },
  teal: {
    bg: "bg-teal-50",
    text: "text-teal-700",
    border: "border-teal-200",
    icon: "text-teal-500",
    tab: "bg-teal-600 text-white",
  },
  gray: {
    bg: "bg-gray-50",
    text: "text-gray-700",
    border: "border-gray-200",
    icon: "text-gray-500",
    tab: "bg-gray-600 text-white",
  },
};

/* Renderiza parágrafo com **negrito** */
const Paragrafo = ({ texto }) => {
  const partes = texto.split(/\*\*(.*?)\*\*/g);
  return (
    <p className="text-sm text-gray-700 leading-relaxed">
      {partes.map((parte, i) =>
        i % 2 === 1 ? (
          <strong key={i} className="font-semibold text-gray-900">
            {parte}
          </strong>
        ) : (
          parte
        ),
      )}
    </p>
  );
};

/* Card de artigo expansível */
const CardArtigo = ({ artigo, corClasses, destaqueTexto }) => {
  const [aberto, setAberto] = useState(!!destaqueTexto);

  const tituloDestacado = destaqueTexto
    ? artigo.titulo.replace(
        new RegExp(`(${destaqueTexto})`, "gi"),
        '<mark class="bg-yellow-200 rounded px-0.5">$1</mark>',
      )
    : artigo.titulo;

  return (
    <div
      className={`border rounded-xl overflow-hidden transition-shadow ${aberto ? "shadow-md border-gray-300" : "border-gray-200 hover:border-gray-300"}`}
    >
      <button
        onClick={() => setAberto(!aberto)}
        className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left hover:bg-gray-50 transition-colors"
      >
        <span
          className="text-sm font-semibold text-gray-800"
          dangerouslySetInnerHTML={{ __html: tituloDestacado }}
        />
        <span className="flex-shrink-0">
          {aberto ? (
            <FiChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <FiChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </span>
      </button>
      {aberto && (
        <div className={`px-5 pb-5 space-y-2 ${corClasses.bg} border-t border-gray-100`}>
          {artigo.conteudo.map((linha, i) => (
            <Paragrafo key={i} texto={linha} />
          ))}
        </div>
      )}
    </div>
  );
};

/* ──────────────────────────────────────────────────────────────
   Componente principal
────────────────────────────────────────────────────────────── */
const CentralAjuda = () => {
  const [busca, setBusca] = useState("");
  const [moduloAtivo, setModuloAtivo] = useState(null); // null = todos

  /* Filtra artigos pela busca */
  const resultados = useMemo(() => {
    const termo = busca.toLowerCase().trim();
    if (!termo && !moduloAtivo) return null; // sem filtro: mostra normal

    return BASE_CONHECIMENTO.flatMap((mod) => {
      if (moduloAtivo && mod.modulo !== moduloAtivo) return [];
      return mod.artigos
        .filter((a) => {
          if (!termo) return true;
          return (
            a.titulo.toLowerCase().includes(termo) ||
            a.tags.some((t) => t.includes(termo)) ||
            a.conteudo.some((c) => c.toLowerCase().includes(termo))
          );
        })
        .map((a) => ({ ...a, _modulo: mod }));
    });
  }, [busca, moduloAtivo]);

  const totalArtigos = BASE_CONHECIMENTO.reduce((acc, m) => acc + m.artigos.length, 0);

  return (
    <div className="max-w-4xl mx-auto py-6 px-4">
      {/* Cabeçalho da central */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-indigo-50 text-indigo-700 px-4 py-1.5 rounded-full text-sm font-medium mb-3">
          <FiBookOpen className="w-4 h-4" />
          {totalArtigos} artigos de ajuda
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Como posso te ajudar?</h2>
        <p className="text-gray-500 text-sm">
          Pesquise por qualquer dúvida ou navegue pelos módulos abaixo.
        </p>
      </div>

      {/* Barra de busca */}
      <div className="relative mb-6">
        <FiSearch className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar por dúvida, funcionalidade ou palavra-chave..."
          className="w-full pl-12 pr-4 py-3.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent shadow-sm"
        />
        {busca && (
          <button
            onClick={() => setBusca("")}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-lg"
          >
            ×
          </button>
        )}
      </div>

      {/* Filtro por módulo (chips) */}
      <div className="flex flex-wrap gap-2 mb-8">
        <button
          onClick={() => setModuloAtivo(null)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
            !moduloAtivo
              ? "bg-gray-800 text-white border-gray-800"
              : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"
          }`}
        >
          Todos
        </button>
        {BASE_CONHECIMENTO.map((mod) => {
          const cores = COR_CLASSES[mod.cor] || COR_CLASSES.gray;
          const ativo = moduloAtivo === mod.modulo;
          return (
            <button
              key={mod.modulo}
              onClick={() => setModuloAtivo(ativo ? null : mod.modulo)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                ativo
                  ? `${cores.tab} border-transparent`
                  : `bg-white text-gray-600 border-gray-300 hover:border-gray-400`
              }`}
            >
              {mod.label}
            </button>
          );
        })}
      </div>

      {/* Resultados de busca */}
      {resultados !== null ? (
        <div>
          {resultados.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <FiSearch className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p className="text-base font-medium">Nenhum resultado encontrado</p>
              <p className="text-sm mt-1">
                Tente palavras diferentes ou{" "}
                <button
                  onClick={() => {
                    setBusca("");
                    setModuloAtivo(null);
                  }}
                  className="text-indigo-600 underline"
                >
                  navegue por módulo
                </button>
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-gray-500 mb-4">
                {resultados.length} resultado
                {resultados.length !== 1 ? "s" : ""} encontrado
                {resultados.length !== 1 ? "s" : ""}
                {busca && (
                  <>
                    {" "}
                    para <strong className="text-gray-700">"{busca}"</strong>
                  </>
                )}
              </p>
              {resultados.map((artigo, i) => {
                const cors = COR_CLASSES[artigo._modulo.cor] || COR_CLASSES.gray;
                return (
                  <div key={i}>
                    <div className={`text-xs font-medium ${cors.text} mb-1 px-1`}>
                      {artigo._modulo.label}
                    </div>
                    <CardArtigo artigo={artigo} corClasses={cors} destaqueTexto={busca} />
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        /* Exibição normal por módulo */
        <div className="space-y-10">
          {BASE_CONHECIMENTO.map((mod) => {
            const cors = COR_CLASSES[mod.cor] || COR_CLASSES.gray;
            const Icone = mod.icone;
            return (
              <section key={mod.modulo}>
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className={`w-9 h-9 rounded-xl ${cors.bg} flex items-center justify-center flex-shrink-0`}
                  >
                    <Icone className={`w-5 h-5 ${cors.icon}`} />
                  </div>
                  <h3 className="text-base font-bold text-gray-900">{mod.label}</h3>
                  <span className="text-xs text-gray-400 font-normal">
                    {mod.artigos.length} artigo
                    {mod.artigos.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="space-y-2">
                  {mod.artigos.map((artigo, i) => (
                    <CardArtigo key={i} artigo={artigo} corClasses={cors} destaqueTexto={null} />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default CentralAjuda;
