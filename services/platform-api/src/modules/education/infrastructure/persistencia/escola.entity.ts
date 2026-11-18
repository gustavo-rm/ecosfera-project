import { Column, Entity, PrimaryGeneratedColumn } from 'typeorm';

import { AGORA } from '../../../../shared/database/colunas';

/** platform.school — a escola é o tenant (RNF-013). */
@Entity({ name: 'school', schema: 'platform' })
export class EscolaEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'school_pkey' })
  id: string;

  @Column({ type: 'text' })
  name: string;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;

  @Column({ type: 'timestamptz', name: 'updated_at', default: AGORA })
  updatedAt: Date;
}
