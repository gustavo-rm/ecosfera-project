/** Emite credencial de serviço de curta duração (ex.: para o ai-sim-service chamar /internal/consent). */
import { ServicoDeTokens } from '../src/modules/identity/infrastructure/tokens';

const segredo = process.env.SERVICE_TOKEN_SECRET;
const servico = process.argv[2] ?? 'ai-sim-service';
if (!segredo) {
  console.error('Defina SERVICE_TOKEN_SECRET.');
  process.exit(2);
}
void ServicoDeTokens.emitirTokenDeServico(
  segredo,
  servico,
  Number(process.argv[3] ?? 300),
).then((t) => console.log(t));
