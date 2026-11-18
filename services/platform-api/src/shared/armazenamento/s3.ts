import {
  DeleteObjectCommand,
  GetObjectCommand,
  PutObjectCommand,
  S3Client,
} from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

import type { ObjectStorage } from './portas';

/** MinIO/S3 real. URLs assinadas de curta duração; buckets privados. */
export class ArmazenamentoS3 implements ObjectStorage {
  readonly nome = 's3';
  private readonly cliente: S3Client;
  private readonly assinador: S3Client;

  constructor(o: {
    endpoint?: string;
    publicEndpoint?: string;
    region: string;
    accessKey?: string;
    secretKey?: string;
    forcePathStyle: boolean;
  }) {
    const base = {
      region: o.region,
      forcePathStyle: o.forcePathStyle,
      ...(o.accessKey && o.secretKey
        ? {
            credentials: {
              accessKeyId: o.accessKey,
              secretAccessKey: o.secretKey,
            },
          }
        : {}),
    };
    this.cliente = new S3Client({
      ...base,
      ...(o.endpoint ? { endpoint: o.endpoint } : {}),
    });
    // A URL entregue ao navegador usa o endpoint público (o interno pode não ser alcançável de fora).
    this.assinador = new S3Client({
      ...base,
      ...((o.publicEndpoint ?? o.endpoint)
        ? { endpoint: o.publicEndpoint ?? o.endpoint }
        : {}),
    });
  }

  async gravar(
    bucket: string,
    chave: string,
    corpo: Buffer,
    tipo: string,
  ): Promise<void> {
    await this.cliente.send(
      new PutObjectCommand({
        Bucket: bucket,
        Key: chave,
        Body: corpo,
        ContentType: tipo,
        ServerSideEncryption: undefined,
      }),
    );
  }

  urlAssinada(
    bucket: string,
    chave: string,
    ttl: number,
    nome: string,
  ): Promise<string> {
    return getSignedUrl(
      this.assinador,
      new GetObjectCommand({
        Bucket: bucket,
        Key: chave,
        ResponseContentDisposition: `attachment; filename="${nome}"`,
      }),
      { expiresIn: ttl },
    );
  }

  async remover(bucket: string, chave: string): Promise<void> {
    await this.cliente.send(
      new DeleteObjectCommand({ Bucket: bucket, Key: chave }),
    );
  }
}
