// Precisa ser o primeiro import do processo: instrumenta http/express/pg/ioredis.
import { iniciarRastreamento } from './shared/observabilidade/rastreamento';

iniciarRastreamento();
