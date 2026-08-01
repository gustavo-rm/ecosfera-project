import { Check } from 'lucide-react';

interface RememberMeProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
}

/** Checkbox minimalista acessível: input nativo invisível sobre a caixa
 *  estilizada, preservando foco por teclado e semântica. */
export function RememberMe({ checked, onChange }: RememberMeProps) {
  return (
    <label className="flex cursor-pointer select-none items-center gap-2 text-sm text-white/70">
      <span
        className={`relative flex h-4.5 w-4.5 items-center justify-center rounded-md border transition-all duration-200 ${
          checked ? 'border-cyan bg-cyan/20' : 'border-white/25 bg-white/5'
        }`}
      >
        <input
          type="checkbox"
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
          className="absolute inset-0 cursor-pointer opacity-0"
        />
        <Check
          className={`h-3 w-3 text-cyan transition-opacity duration-200 ${
            checked ? 'opacity-100' : 'opacity-0'
          }`}
          strokeWidth={3}
        />
      </span>
      Remember me
    </label>
  );
}
