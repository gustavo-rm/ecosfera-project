import type { Logger } from 'pino';

import { ErroNaoImplementado } from '../../../shared/kernel/erros';
import type { Mailer, MensagemDeEmail } from '../domain/portas';

/**
 * FAKE: não envia e-mail. Guarda as mensagens em memória (só dev/teste) e registra no log
 * o assunto. O conteúdo sensível (token) só aparece em log fora de produção — e o fake
 * nunca liga em produção (validação de configuração).
 */
export class MailerFalso implements Mailer {
  readonly caixa: MensagemDeEmail[] = [];
  constructor(
    private readonly logger: Logger,
    private readonly mostrarConteudo: boolean,
  ) {}
  enviar(m: MensagemDeEmail): Promise<void> {
    this.caixa.push(m);
    if (this.caixa.length > 200) this.caixa.shift();
    this.logger.info(
      { fake: 'Mailer', subject: m.assunto, ...(this.mostrarConteudo || !m.sensivel ? { body: m.texto } : {}) },
      '[FAKE Mailer] mensagem não enviada (adaptador falso)',
    );
    return Promise.resolve();
  }
}

/** Real e explícito: envio de e-mail desligado. A redefinição por e-mail responde 501 com orientação. */
export class MailerDesligado implements Mailer {
  enviar(): Promise<void> {
    return Promise.reject(
      new ErroNaoImplementado('Envio de e-mail não configurado nesta implantação. Peça ao administrador da escola.'),
    );
  }
}
