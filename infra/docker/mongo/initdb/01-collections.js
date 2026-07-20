// ECOSFERA — inicialização do MongoDB (executa apenas na 1ª subida do volume).
// Cria as coleções do estado de simulação e índices essenciais.
// O `db` aqui já aponta para MONGO_INITDB_DATABASE (ecosfera).

db.createCollection("planet_state"); // estado aninhado do planeta, por era/checkpoint
db.createCollection("species");      // genoma + traços das espécies
db.createCollection("ecosystem");    // relações do ecossistema
db.createCollection("event_log");    // log de eventos da simulação
db.createCollection("telemetry");    // eventos brutos de sessão (stealth assessment)

// Índices de acesso mais quente.
db.planet_state.createIndex({ planetId: 1, era: 1 });
db.species.createIndex({ planetId: 1 });
db.ecosystem.createIndex({ planetId: 1 });
db.event_log.createIndex({ planetId: 1, ts: -1 });
db.telemetry.createIndex({ sessionId: 1, ts: -1 });
db.telemetry.createIndex({ planetId: 1, ts: -1 });
