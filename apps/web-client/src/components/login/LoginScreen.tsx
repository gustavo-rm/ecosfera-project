import { SpaceBackdrop } from '@/components/background/SpaceBackdrop';
import { SunFlare } from '@/components/background/SunFlare';
import { PlanetSceneClient } from '@/components/planet/PlanetSceneClient';
import { BrandLogo } from '@/components/logo/BrandLogo';
import { LoginCard } from './LoginCard';
import { LoginForm } from '@/components/form/LoginForm';

/**
 * Composição da tela de login em camadas:
 *  0 — fundo espacial (CSS)      1 — cena WebGL do planeta
 *  2 — Sol/lens flare (CSS)      3 — interface (logo + cartão)
 *
 * O posicionamento do cartão muda por breakpoint: à direita e centralizado
 * verticalmente em desktop/notebook, centralizado em tablet e no rodapé no
 * mobile (deixando o topo livre para o planeta).
 */
export function LoginScreen() {
  return (
    <main className="relative min-h-[100dvh] w-full overflow-hidden bg-space-void">
      <SpaceBackdrop />
      <PlanetSceneClient />
      <SunFlare />

      <div className="absolute left-6 top-6 z-40 sm:left-10 sm:top-8">
        <BrandLogo />
      </div>

      <div className="relative z-30 flex min-h-[100dvh] w-full flex-col items-center justify-end px-5 pb-10 pt-[42vh] md:justify-center md:px-10 md:pt-10 lg:items-end lg:px-[7vw]">
        <div className="w-full max-w-[440px] md:max-w-[470px] lg:max-w-[430px]">
          <LoginCard>
            <LoginForm />
          </LoginCard>
        </div>
      </div>
    </main>
  );
}
