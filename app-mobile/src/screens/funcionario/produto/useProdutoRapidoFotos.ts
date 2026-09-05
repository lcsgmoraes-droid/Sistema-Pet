import * as ImagePicker from "expo-image-picker";
import { useEffect, useRef, useState } from "react";
import { Alert, Linking } from "react-native";
import { enviarFotoProdutoRapido, FotoProdutoRapido } from "../../../services/funcionarioProdutos.service";
import { erroCadastroProduto } from "../../../utils/produtoRapido";

export function useProdutoRapidoFotos() {
  const [fotos, setFotos] = useState<FotoProdutoRapido[]>([]);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");
  const emCurso = useRef(false);
  const ativo = useRef(true);
  const lista = useRef<FotoProdutoRapido[]>([]);
  useEffect(() => { ativo.current = true; return () => { ativo.current = false; }; }, []);

  function atualizar(novas: FotoProdutoRapido[]) {
    lista.current = novas;
    if (ativo.current) setFotos(novas);
  }

  async function adicionar(origem: "camera" | "galeria") {
    if (emCurso.current || lista.current.length >= 5) return;
    emCurso.current = true; setOcupado(true); setErro("");
    try {
      if (origem === "camera") {
        const permissao = await ImagePicker.requestCameraPermissionsAsync();
        if (!permissao.granted) {
          Alert.alert("Permitir câmera", "Permita a câmera nas configurações ou escolha uma foto da galeria.", [
            { text: "Agora não", style: "cancel" },
            { text: "Configurações", onPress: () => { void Linking.openSettings(); } },
          ]);
          return;
        }
      }
      const opcoes: ImagePicker.ImagePickerOptions = {
        mediaTypes: ["images"], allowsEditing: true, aspect: [1, 1], quality: 0.8,
        preferredAssetRepresentationMode: ImagePicker.UIImagePickerPreferredAssetRepresentationMode.Compatible,
      };
      const resultado = origem === "camera"
        ? await ImagePicker.launchCameraAsync(opcoes)
        : await ImagePicker.launchImageLibraryAsync(opcoes);
      if (!ativo.current || resultado.canceled || !resultado.assets[0]) return;
      const asset = resultado.assets[0];
      const type = asset.mimeType || "image/jpeg";
      if (!["image/jpeg", "image/png", "image/webp"].includes(type)) {
        setErro("Escolha uma foto JPG, PNG ou WebP, ou tire uma foto pela câmera.");
        return;
      }
      if ((asset.fileSize || 0) > 10 * 1024 * 1024) {
        setErro("A foto deve ter até 10 MB. Escolha uma imagem menor.");
        return;
      }
      if (!lista.current.some((foto) => foto.uri === asset.uri)) {
        const ext = type === "image/png" ? "png" : type === "image/webp" ? "webp" : "jpg";
        atualizar([...lista.current, { uri: asset.uri, type, name: `produto.${ext}` }]);
      }
    } catch {
      if (ativo.current) setErro("Não foi possível selecionar a foto. Tente novamente ou use a galeria.");
    } finally {
      emCurso.current = false;
      if (ativo.current) setOcupado(false);
    }
  }

  async function enviar(produtoId: number) {
    if (emCurso.current) return;
    emCurso.current = true;
    if (ativo.current) { setOcupado(true); setErro(""); }
    try {
      for (const foto of lista.current.filter((item) => !item.enviada)) {
        if (!ativo.current) break;
        await enviarFotoProdutoRapido(produtoId, foto);
        atualizar(lista.current.map((item) => item.uri === foto.uri ? { ...item, enviada: true } : item));
      }
    } catch (error) {
      if (ativo.current) setErro(erroCadastroProduto(error, "O produto foi salvo, mas há fotos pendentes. Tente enviar as fotos novamente."));
    } finally {
      emCurso.current = false;
      if (ativo.current) setOcupado(false);
    }
  }

  function remover(uri: string) { if (!emCurso.current) atualizar(lista.current.filter((foto) => foto.uri !== uri)); }
  function limpar() { if (!emCurso.current) { atualizar([]); setErro(""); } }
  return { fotos, ocupado, erro, adicionar, remover, enviar, limpar, pendentes: fotos.some((foto) => !foto.enviada) };
}
