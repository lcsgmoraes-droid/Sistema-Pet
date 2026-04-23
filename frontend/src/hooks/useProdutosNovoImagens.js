import { useState } from 'react';
import api from '../api';
import { deleteImagemProduto, uploadImagemProduto } from '../api/produtos';

const MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024;

export default function useProdutosNovoImagens({ id, setImagens }) {
  const [uploadingImage, setUploadingImage] = useState(false);

  const recarregarImagens = async () => {
    const imagensRes = await api.get(`/produtos/${id}/imagens`);
    setImagens(imagensRes.data || []);
  };

  const handleUploadImagem = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    const maxSize = MAX_UPLOAD_SIZE_BYTES;

    for (const file of files) {
      if (!allowedTypes.includes(file.type)) {
        alert(`${file.name}: Apenas JPG, PNG e WebP são permitidos`);
        return;
      }
      if (file.size > maxSize) {
        alert(`${file.name}: Imagem deve ter no máximo 10MB`);
        return;
      }
    }

    try {
      setUploadingImage(true);

      const uploadedImages = [];
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        try {
          const response = await uploadImagemProduto(id, formData);
          uploadedImages.push(response.data);
        } catch (error) {
          console.error(`Erro ao enviar ${file.name}:`, error);
          alert(
            `Erro ao enviar ${file.name}: ${error.response?.data?.detail || 'Erro desconhecido'}`,
          );
        }
      }

      await recarregarImagens();
      alert(`${uploadedImages.length} imagem(ns) enviada(s) com sucesso!`);
    } catch (error) {
      console.error('Erro ao enviar imagens:', error);
      alert(error.response?.data?.detail || 'Erro ao enviar imagens');
    } finally {
      setUploadingImage(false);
      e.target.value = '';
    }
  };

  const handleDeleteImagem = async (imagemId) => {
    if (!window.confirm('Deseja realmente excluir esta imagem?')) {
      return;
    }

    try {
      await deleteImagemProduto(imagemId);
      await recarregarImagens();
      alert('Imagem excluída com sucesso!');
    } catch (error) {
      console.error('Erro ao excluir imagem:', error);
      alert('Erro ao excluir imagem');
    }
  };

  const handleSetPrincipal = async (imagemId) => {
    try {
      await api.put(`/produtos/imagens/${imagemId}`, { principal: true });
      await recarregarImagens();
      alert('Imagem principal atualizada!');
    } catch (error) {
      console.error('Erro ao definir imagem principal:', error);
      alert('Erro ao definir imagem principal');
    }
  };

  return {
    uploadingImage,
    handleUploadImagem,
    handleDeleteImagem,
    handleSetPrincipal,
  };
}
