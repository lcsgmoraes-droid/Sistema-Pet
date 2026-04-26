export default function ExameIAIntro({ compacto = false }) {
  return (
    <div className="rounded-lg border border-indigo-100 bg-white px-3 py-3 text-xs text-indigo-700">
      <p className="font-medium text-indigo-800">O que esta IA ja pode ajudar agora</p>
      <p className="mt-1">
        {compacto
          ? "Processa hemograma, bioquimica, laudos em PDF e imagem anexada ao exame. Para raio-x, ultrassom e outras imagens, a IA ajuda como apoio clinico e nao substitui o laudo do especialista."
          : "Processa hemograma, bioquimica, laudos em PDF e imagem anexada ao exame. Para imagem, ajuda a revisar raio-x, ultrassom e outros arquivos visuais como apoio clinico, sem substituir o laudo do especialista."}
      </p>
    </div>
  );
}
