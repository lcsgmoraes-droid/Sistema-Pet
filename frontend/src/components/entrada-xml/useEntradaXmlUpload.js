import { useState } from 'react';

export default function useEntradaXmlUpload({
  api,
  carregarDados,
  toast,
}) {
  const [uploadingFile, setUploadingFile] = useState(false);
  const [uploadingLote, setUploadingLote] = useState(false);
  const [mostrarModalLote, setMostrarModalLote] = useState(false);
  const [resultadoLote, setResultadoLote] = useState(null);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    console.log('📤 [EntradaXML] Upload iniciado');
    console.log('  - Arquivo selecionado:', file?.name);
    console.log('  - Tamanho:', file?.size, 'bytes');
    console.log('  - Tipo:', file?.type);

    if (!file) {
      console.warn('⚠️ [EntradaXML] Nenhum arquivo selecionado');
      return;
    }

    if (!file.name.toLowerCase().endsWith('.xml')) {
      console.error('❌ [EntradaXML] Arquivo nao é XML:', file.name);
      toast.error('❌ Por favor, selecione um arquivo XML');
      return;
    }

    setUploadingFile(true);
    const formData = new FormData();
    formData.append('file', file);

    console.log('🚀 [EntradaXML] Enviando arquivo para:', `/notas-entrada/upload`);
    console.log('📦 [EntradaXML] FormData preparado:', file.name, file.size, 'bytes');

    try {
      const response = await api.post(`/notas-entrada/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log('✅ [EntradaXML] Upload bem-sucedido!');
      console.log('  - Response data:', response.data);

      const itensVinculados = response.data.produtos_vinculados || 0;
      const totalItens = response.data.itens_total || 0;

      console.log(`📊 [EntradaXML] Produtos vinculados: ${itensVinculados}/${totalItens}`);

      if (response.data.fornecedor_criado_automaticamente) {
        toast.success(
          `🏢 Novo fornecedor cadastrado: ${response.data.fornecedor}`,
          { duration: 4000 }
        );
      }

      if (response.data.produtos_reativados > 0) {
        toast.success(
          `♻️ ${response.data.produtos_reativados} produto(s) inativo(s) reativado(s) automaticamente`,
          { duration: 4000 }
        );
      }

      toast.success(
        `✅ NF-e ${response.data.numero_nota} processada! ${itensVinculados}/${totalItens} produtos vinculados automaticamente`,
        { duration: 5000 }
      );

      carregarDados();
      event.target.value = '';
    } catch (error) {
      console.error('❌ [EntradaXML] ERRO no upload:');
      console.error('  - Mensagem:', error.message);
      console.error('  - Response data:', error.response?.data);
      console.error('  - Status:', error.response?.status);
      console.error('  - Headers:', error.response?.headers);
      console.error('  - Stack completo:', error.stack);

      const errorMsg = error.response?.data?.detail || error.message || 'Erro ao processar XML da NF-e';
      console.error('  - Mensagem para usuario:', errorMsg);

      toast.error(`❌ ${errorMsg}`);
    } finally {
      setUploadingFile(false);
      console.log('🏁 [EntradaXML] Upload finalizado');
    }
  };

  const handleMultipleFilesUpload = async (event) => {
    const files = Array.from(event.target.files);
    console.log('📦 [EntradaXML] Upload em lote iniciado -', files.length, 'arquivos');

    if (files.length === 0) {
      console.warn('⚠️ [EntradaXML] Nenhum arquivo selecionado');
      return;
    }

    const invalidFiles = files.filter((f) => !f.name.toLowerCase().endsWith('.xml'));
    if (invalidFiles.length > 0) {
      toast.error(`❌ ${invalidFiles.length} arquivo(s) nao são XML: ${invalidFiles.map((f) => f.name).join(', ')}`);
      return;
    }

    setUploadingLote(true);
    setMostrarModalLote(true);
    setResultadoLote(null);

    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    console.log('🚀 [EntradaXML] Enviando', files.length, 'arquivos para:', `/notas-entrada/upload-lote`);

    try {
      const response = await api.post(`/notas-entrada/upload-lote`, formData);

      console.log('✅ [EntradaXML] Upload em lote bem-sucedido!');
      console.log('  - Response:', response.data);

      setResultadoLote(response.data);

      if (response.data.sucessos > 0) {
        toast.success(
          `✅ ${response.data.sucessos}/${response.data.total_arquivos} nota(s) processada(s) com sucesso!`,
          { duration: 5000 }
        );
      }

      if (response.data.erros > 0) {
        toast.error(
          `⚠️ ${response.data.erros}/${response.data.total_arquivos} nota(s) com erro`,
          { duration: 5000 }
        );
      }

      carregarDados();
      event.target.value = '';
    } catch (error) {
      console.error('❌ [EntradaXML] ERRO no upload em lote:', error);
      toast.error(`❌ Erro ao processar lote: ${error.response?.data?.detail || error.message}`);
      setMostrarModalLote(false);
    } finally {
      setUploadingLote(false);
    }
  };

  const fecharResultadoLote = () => {
    setMostrarModalLote(false);
    setResultadoLote(null);
  };

  return {
    fecharResultadoLote,
    handleFileUpload,
    handleMultipleFilesUpload,
    mostrarModalLote,
    resultadoLote,
    uploadingFile,
    uploadingLote,
  };
}
