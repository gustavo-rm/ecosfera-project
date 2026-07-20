import 'reflect-metadata';
import 'dotenv/config';
import { DataSource } from 'typeorm';

/**
 * DataSource usado pela CLI de migrations do TypeORM.
 * O schema relacional autoritativo vive em "platform" (ver init do Postgres).
 * `synchronize` é SEMPRE false: schema evolui exclusivamente por migration.
 */
export default new DataSource({
  type: 'postgres',
  url: process.env.DATABASE_URL,
  schema: 'platform',
  entities: ['src/**/*.entity.{ts,js}'],
  migrations: ['src/infrastructure/database/migrations/*.{ts,js}'],
  migrationsTableName: 'platform_migrations',
  synchronize: false,
  logging: process.env.DB_LOGGING === 'true',
});
