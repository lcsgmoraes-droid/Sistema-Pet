export default function MotivoConsultaField({
  form,
  setCampo,
  css,
  renderCampo,
}) {
  return renderCampo("Motivo da consulta", true)(
    <textarea
      value={form.motivo_consulta}
      onChange={(event) => setCampo("motivo_consulta", event.target.value)}
      className={css.textarea}
      placeholder="Descreva o motivo da consulta..."
    />
  );
}
