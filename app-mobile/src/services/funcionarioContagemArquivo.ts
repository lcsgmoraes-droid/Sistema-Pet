type ArquivoGerado = {
  filename: string;
  mime_type: string;
};

type ArquivoLocal = {
  uri: string;
  contentUri?: string | null;
};

type NativeFileShare = {
  shareFile?: (uri: string, mimeType: string, title: string) => Promise<unknown>;
};

type ShareContent = {
  title?: string;
  message?: string;
  url?: string;
};

type CompartilharArquivoDeps = {
  platform: string;
  nativeShare?: NativeFileShare | null;
  share: (content: ShareContent) => Promise<unknown>;
};

export async function compartilharArquivoGerado(
  arquivo: ArquivoGerado,
  file: ArquivoLocal,
  deps: CompartilharArquivoDeps,
): Promise<void> {
  const filename = arquivo.filename || "contagem.pdf";
  const mimeType = arquivo.mime_type || "application/octet-stream";

  if (deps.platform === "android") {
    if (!deps.nativeShare?.shareFile) {
      throw new Error(
        "Para enviar PDF/Excel como anexo, atualize o aplicativo instalado.",
      );
    }

    const uriCompartilhavel = file.contentUri || "";
    if (!uriCompartilhavel.startsWith("content://")) {
      throw new Error("Nao foi possivel preparar o arquivo para compartilhar.");
    }

    await deps.nativeShare.shareFile(uriCompartilhavel, mimeType, filename);
    return;
  }

  await deps.share({
    title: filename,
    url: file.uri,
  });
}
