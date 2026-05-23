import { useRef } from 'react';
import PropTypes from 'prop-types';
import { FileText, FileUp, Files, Search, Settings } from 'lucide-react';
import ActionButton from '../ui/ActionButton';
import PageHeader from '../ui/PageHeader';

function FileInputAction({
  accept,
  disabled,
  icon,
  label,
  loading,
  loadingLabel,
  multiple,
  onChange,
}) {
  const inputRef = useRef(null);

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={onChange}
        disabled={disabled}
        className="hidden"
      />
      <ActionButton
        type="button"
        icon={icon}
        intent="create"
        loading={loading}
        disabled={disabled}
        size="md"
        onClick={() => inputRef.current?.click()}
      >
        {loading ? loadingLabel : label}
      </ActionButton>
    </>
  );
}

FileInputAction.propTypes = {
  accept: PropTypes.string.isRequired,
  disabled: PropTypes.bool,
  icon: PropTypes.elementType.isRequired,
  label: PropTypes.string.isRequired,
  loading: PropTypes.bool,
  loadingLabel: PropTypes.string.isRequired,
  multiple: PropTypes.bool,
  onChange: PropTypes.func.isRequired,
};

FileInputAction.defaultProps = {
  disabled: false,
  loading: false,
  multiple: false,
};

export default function EntradaXmlHeader({
  mostrarConfigSefaz,
  mostrarPainelSefaz,
  onToggleConfigSefaz,
  onTogglePainelSefaz,
  onUploadPdf,
  onUploadLote,
  onUploadXml,
  uploadingFile,
  uploadingLote,
  uploadingPdf,
}) {
  const uploadBloqueado = uploadingFile || uploadingLote || uploadingPdf;

  return (
    <PageHeader
      className="mb-6"
      title="Central NF-e Entradas"
      subtitle="Gerencie todas as notas fiscais de entrada via upload ou direto da SEFAZ."
      actions={(
        <>
          <FileInputAction
            accept=".xml"
            icon={FileUp}
            label="Importar XML"
            loading={uploadingFile}
            loadingLabel="Processando..."
            disabled={uploadBloqueado}
            onChange={onUploadXml}
          />
          <ActionButton
            type="button"
            icon={FileText}
            intent="create"
            tone="soft"
            loading={uploadingPdf}
            disabled={uploadBloqueado}
            size="md"
            onClick={onUploadPdf}
          >
            {uploadingPdf ? 'Processando PDF...' : 'Importar PDF'}
          </ActionButton>
          <FileInputAction
            accept=".xml"
            icon={Files}
            label="Importar varios XML"
            loading={uploadingLote}
            loadingLabel="Processando lote..."
            disabled={uploadBloqueado}
            multiple
            onChange={onUploadLote}
          />
          <ActionButton
            type="button"
            icon={Search}
            intent="create"
            tone={mostrarPainelSefaz ? 'solid' : 'soft'}
            size="md"
            onClick={onTogglePainelSefaz}
          >
            Buscar pela SEFAZ
          </ActionButton>
          <ActionButton
            type="button"
            icon={Settings}
            intent="neutral"
            tone={mostrarConfigSefaz ? 'solid' : 'soft'}
            size="md"
            onClick={onToggleConfigSefaz}
          >
            Configurar SEFAZ
          </ActionButton>
        </>
      )}
    />
  );
}

EntradaXmlHeader.propTypes = {
  mostrarConfigSefaz: PropTypes.bool.isRequired,
  mostrarPainelSefaz: PropTypes.bool.isRequired,
  onToggleConfigSefaz: PropTypes.func.isRequired,
  onTogglePainelSefaz: PropTypes.func.isRequired,
  onUploadLote: PropTypes.func.isRequired,
  onUploadPdf: PropTypes.func.isRequired,
  onUploadXml: PropTypes.func.isRequired,
  uploadingFile: PropTypes.bool.isRequired,
  uploadingLote: PropTypes.bool.isRequired,
  uploadingPdf: PropTypes.bool.isRequired,
};
