import { Controller, Inject, Query, Res } from '@nestjs/common';
import type { Response } from 'express';

import { ArmazenamentoFalso } from '../../../shared/armazenamento/fake';
import {
  OBJECT_STORAGE,
  type ObjectStorage,
} from '../../../shared/armazenamento/portas';
import { Autorizacao } from '../../../shared/autorizacao/autorizacao.decorator';
import { definirEndpoint, Endpoint } from '../../../shared/http/contrato';
import {
  ErroAcessoNegado,
  ErroNaoEncontrado,
} from '../../../shared/kernel/erros';

const Contrato = definirEndpoint({
  operationId: 'fakeSignedFile',
  metodo: 'GET',
  caminho: '/files',
  tag: 'internal',
  resumo: 'Download por URL assinada do armazenamento FALSO (só dev/teste)',
  seguranca: 'publico',
  sucesso: 200,
  interna: true,
  respostas: {
    200: { descricao: 'Arquivo', tipoConteudo: 'application/octet-stream' },
    403: { descricao: 'URL inválida ou expirada' },
  },
});

/** Só existe de verdade com o armazenamento FALSO; com S3 a URL assinada aponta para o MinIO/S3. */
@Controller()
export class ArquivosController {
  constructor(
    @Inject(OBJECT_STORAGE) private readonly storage: ObjectStorage,
  ) {}

  @Endpoint(Contrato)
  @Autorizacao({
    publico: true,
    motivo:
      'a própria URL é a credencial (assinada por HMAC e com validade curta)',
  })
  async baixar(@Query() q: Record<string, string>, @Res() res: Response) {
    if (!(this.storage instanceof ArmazenamentoFalso))
      throw new ErroNaoEncontrado('Rota');
    const f = await this.storage.abrir(q);
    if (!f) throw new ErroAcessoNegado('URL inválida ou expirada');
    res.setHeader('Content-Type', f.tipo);
    res.setHeader(
      'Content-Disposition',
      `attachment; filename="${f.nome.replace(/[^\w.-]/g, '_')}"`,
    );
    res.setHeader('Cache-Control', 'no-store');
    res.send(f.corpo);
  }
}
