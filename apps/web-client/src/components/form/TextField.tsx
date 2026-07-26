import type { HTMLInputTypeAttribute } from 'react';
import type { LucideIcon } from 'lucide-react';
import { FieldShell } from './FieldShell';

interface TextFieldProps {
  id: string;
  label: string;
  icon: LucideIcon;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: HTMLInputTypeAttribute;
  autoComplete?: string;
}

export function TextField({
  id,
  label,
  icon,
  value,
  onChange,
  placeholder,
  type = 'text',
  autoComplete,
}: TextFieldProps) {
  return (
    <FieldShell icon={icon}>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        aria-label={label}
        className="h-full flex-1 bg-transparent text-sm text-soft outline-none placeholder:text-white/35"
      />
    </FieldShell>
  );
}
