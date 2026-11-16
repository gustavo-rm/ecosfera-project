import { CreateBucketCommand, S3Client } from '@aws-sdk/client-s3';
import {
  GenericContainer,
  type StartedTestContainer,
  Wait,
} from 'testcontainers';

import { ArmazenamentoS3 } from '../../src/shared/armazenamento/s3';

describe('ObjectStorage real (MinIO S3): URL assinada curta, bucket privado', () => {
  let minio: StartedTestContainer;
  let endpoint: string;
  let s3: ArmazenamentoS3;

  beforeAll(async () => {
    minio = await new GenericContainer('chainguard/minio:latest')
      .withEnvironment({
        MINIO_ROOT_USER: 'teste',
        MINIO_ROOT_PASSWORD: 'senha-de-teste-123',
      })
      .withCommand(['server', '/tmp/data'])
      .withExposedPorts(9000)
      .withWaitStrategy(Wait.forHttp('/minio/health/live', 9000))
      .start();
    endpoint = `http://${minio.getHost()}:${minio.getMappedPort(9000)}`;
    const cfg = {
      endpoint,
      region: 'us-east-1',
      accessKey: 'teste',
      secretKey: 'senha-de-teste-123',
      forcePathStyle: true,
    };
    await new S3Client({
      region: cfg.region,
      endpoint,
      forcePathStyle: true,
      credentials: {
        accessKeyId: 'teste',
        secretAccessKey: 'senha-de-teste-123',
      },
    }).send(new CreateBucketCommand({ Bucket: 'exports' }));
    s3 = new ArmazenamentoS3(cfg);
  }, 120000);
  afterAll(() => minio?.stop());

  it('grava, baixa pela URL assinada, e a URL expira', async () => {
    await s3.gravar(
      'exports',
      'e1/r.csv',
      Buffer.from('a,b\n1,2\n'),
      'text/csv',
    );
    const url = await s3.urlAssinada('exports', 'e1/r.csv', 1, 'r.csv');
    const ok = await fetch(url);
    expect(ok.status).toBe(200);
    expect(await ok.text()).toBe('a,b\n1,2\n');
    expect(ok.headers.get('content-disposition')).toContain('r.csv');
    await new Promise((r) => setTimeout(r, 2100));
    expect((await fetch(url)).status).toBe(403);
  });

  it('sem assinatura o objeto não é público', async () => {
    expect((await fetch(`${endpoint}/exports/e1/r.csv`)).status).toBe(403);
  });

  it('remoção (retenção) apaga o objeto', async () => {
    await s3.remover('exports', 'e1/r.csv');
    const url = await s3.urlAssinada('exports', 'e1/r.csv', 60, 'r.csv');
    expect((await fetch(url)).status).toBe(404);
  });
});
