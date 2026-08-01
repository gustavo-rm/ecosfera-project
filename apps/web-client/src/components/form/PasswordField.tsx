'use client';

import { useState } from 'react';
import { Eye, EyeOff, Lock } from 'lucide-react';
import { FieldShell } from './FieldShell';

interface PasswordFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function PasswordField({ id, label, value, onChange, placeholder }: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  const Toggle = visible ? EyeOff : Eye;

  return (
    <FieldShell
      icon={Lock}
      trailing={
        <button
          type="button"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? 'Ocultar senha' : 'Mostrar senha'}
          aria-pressed={visible}
          className="shrink-0 rounded-md text-white/40 outline-none transition-colors hover:text-cyan focus-visible:text-cyan"
        >
          <Toggle className="h-4.5 w-4.5" strokeWidth={1.75} />
        </button>
      }
    >
      <input
        id={id}
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        autoComplete="current-password"
        aria-label={label}
        className="h-full flex-1 bg-transparent text-sm text-soft outline-none placeholder:text-white/35"
      />
    </FieldShell>
  );
}
