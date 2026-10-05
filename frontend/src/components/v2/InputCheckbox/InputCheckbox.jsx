import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

const InputCheckbox = forwardRef(function InputCheckbox(
  { checked = false, indeterminate = false, rotulo, className = "", ...rest },
  ref,
) {
  const internoRef = useRef(null);
  useImperativeHandle(ref, () => internoRef.current);

  useEffect(() => {
    if (internoRef.current) internoRef.current.indeterminate = indeterminate;
  }, [indeterminate]);

  useEffect(() => {
    if (import.meta.env.DEV && !rotulo) {
      console.warn("InputCheckbox sem rotulo: o leitor de tela fica sem nome para o controle.");
    }
  }, [rotulo]);

  return (
    <label className="inline-flex h-11 w-11 cursor-pointer items-center justify-center">
      <input
        {...rest}
        ref={internoRef}
        type="checkbox"
        checked={checked}
        aria-label={rotulo}
        className={`h-4 w-4 cursor-pointer rounded border-slate-300 accent-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-600 dark:bg-slate-900 ${className}`}
      />
    </label>
  );
});

export default InputCheckbox;
