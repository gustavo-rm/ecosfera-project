import { Check, Column, Entity, PrimaryGeneratedColumn, Unique } from 'typeorm';

import { AGORA } from '../../../../shared/database/colunas';

/** platform.consent_text — textos legais versionados (placeholders para revisão jurídica). */
@Entity({ name: 'consent_text', schema: 'platform' })
@Unique('consent_text_purpose_version_locale_key', ['purpose', 'version', 'locale'])
@Check('consent_text_review_status_check', `review_status IN ('pending_legal_review', 'approved', 'retired')`)
export class TextoDeConsentimentoEntity {
  @PrimaryGeneratedColumn('uuid', { primaryKeyConstraintName: 'consent_text_pkey' })
  id: string;

  @Column({ type: 'text' })
  purpose: string;

  @Column({ type: 'text' })
  version: string;

  @Column({ type: 'text', default: 'pt-BR' })
  locale: string;

  @Column({ type: 'text' })
  body: string;

  @Column({ type: 'text', name: 'review_status', default: 'pending_legal_review' })
  reviewStatus: string;

  @Column({ type: 'timestamptz', name: 'created_at', default: AGORA })
  createdAt: Date;
}
