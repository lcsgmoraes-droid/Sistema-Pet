export default function useProdutosNovoRecorrencia({ handleChange }) {
  const handleTipoRecorrenciaChange = (valor) => {
    handleChange('tipo_recorrencia', valor);

    if (valor === 'daily') handleChange('intervalo_dias', '1');
    else if (valor === 'weekly') handleChange('intervalo_dias', '7');
    else if (valor === 'monthly') handleChange('intervalo_dias', '30');
    else if (valor === 'yearly') handleChange('intervalo_dias', '365');
  };

  return { handleTipoRecorrenciaChange };
}
