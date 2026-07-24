'use client';

import { useState, type FormEvent } from 'react';
import { Mail } from 'lucide-react';
import { TextField } from './TextField';
import { PasswordField } from './PasswordField';
import { RememberMe } from './RememberMe';
import { FormDivider } from './FormDivider';
import { PrimaryButton } from '@/components/buttons/PrimaryButton';
import { SecondaryButton } from '@/components/buttons/SecondaryButton';

/** Formulário de acesso. Mantém apenas o estado local dos campos — a
 *  integração com autenticação fica a cargo de quem consumir a tela. */
export function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
      <header className="text-center">
        <p className="text-sm text-white/55">Welcome to</p>
        <h1 className="mt-1 pl-[0.35em] text-[2rem] font-semibold tracking-[0.35em] text-soft sm:text-[2.15rem]">
          ECOSFERA
        </h1>
        <p className="mt-2 text-sm text-white/45">Continue shaping your living planet.</p>
      </header>

      <div className="flex flex-col gap-3">
        <TextField
          id="email"
          label="Email"
          icon={Mail}
          type="email"
          placeholder="Email"
          autoComplete="email"
          value={email}
          onChange={setEmail}
        />
        <PasswordField
          id="password"
          label="Senha"
          placeholder="Password"
          value={password}
          onChange={setPassword}
        />
      </div>

      <div className="flex items-center justify-between">
        <RememberMe checked={remember} onChange={setRemember} />
        <a
          href="#"
          className="rounded text-sm font-medium text-cyan/90 outline-none transition-colors hover:text-cyan focus-visible:text-cyan"
        >
          Forgot password?
        </a>
      </div>

      <div className="flex flex-col gap-4">
        <PrimaryButton>Enter my planet</PrimaryButton>
        <FormDivider />
        <SecondaryButton>Create account</SecondaryButton>
      </div>
    </form>
  );
}
