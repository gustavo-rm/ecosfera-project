import {
  API,
  type AppDeTeste,
  bearer,
  criarApp,
  criarEscola,
  criarUsuario,
  type UsuarioDeTeste,
} from '../support/app';

describe('Educação: escolas, turmas, trilhas, missões BNCC (RF-001, 005, 061, 062)', () => {
  let t: AppDeTeste;
  let escolaA: string;
  let escolaB: string;
  let operador: UsuarioDeTeste;
  let profA: UsuarioDeTeste;
  let profA2: UsuarioDeTeste;
  let profB: UsuarioDeTeste;
  let coordA: UsuarioDeTeste;
  let alunoA: UsuarioDeTeste;
  let alunoB: UsuarioDeTeste;
  let turmaA: string;

  beforeAll(async () => {
    t = await criarApp();
    escolaA = await criarEscola(t);
    escolaB = await criarEscola(t);
    operador = await criarUsuario(t, 'platform_admin', null);
    profA = await criarUsuario(t, 'teacher', escolaA);
    profA2 = await criarUsuario(t, 'teacher', escolaA);
    profB = await criarUsuario(t, 'teacher', escolaB);
    coordA = await criarUsuario(t, 'coordinator', escolaA);
    alunoA = await criarUsuario(t, 'student', escolaA);
    alunoB = await criarUsuario(t, 'student', escolaB);
  });
  afterAll(() => t.fechar());

  it('operador cria escola com admin inicial; admin de escola não pode criar escola', async () => {
    const r = await t
      .http()
      .post(`${API}/schools`)
      .set(...bearer(operador))
      .send({
        name: 'Escola Nova',
        admin: {
          name: 'Diretora',
          email: `dir.${Date.now()}@x.local`,
          password: 'Diretora-segura-1',
        },
      });
    expect(r.status).toBe(201);
    expect(r.body.admin).toMatchObject({
      role: 'admin',
      schoolId: r.body.school.id,
    });
    expect(
      (
        await t
          .http()
          .post(`${API}/schools`)
          .set(...bearer(profA))
          .send({ name: 'X', admin: { name: 'a', email: 'a@b.cd' } })
      ).status,
    ).toBe(403);
  });

  it('professor cria turma com trilha; aluno não pode criar turma', async () => {
    const r = await t
      .http()
      .post(`${API}/classes`)
      .set(...bearer(profA))
      .send({ name: '7º A', year: 7, trackLevel: 'fundamental_ii' });
    expect(r.status).toBe(201);
    expect(r.body).toMatchObject({
      teacherUserId: profA.id,
      schoolId: escolaA,
      trackLevel: 'fundamental_ii',
    });
    turmaA = r.body.id;
    expect(
      (
        await t
          .http()
          .post(`${API}/classes`)
          .set(...bearer(alunoA))
          .send({ name: 'x' })
      ).status,
    ).toBe(403);
  });

  it('matrícula: aluno da escola entra; aluno de outra escola é recusado', async () => {
    const ok = await t
      .http()
      .post(`${API}/classes/${turmaA}/students`)
      .set(...bearer(profA))
      .send({ studentIds: [alunoA.id] });
    expect(ok.status).toBe(200);
    expect(ok.body.enrolled).toEqual([alunoA.id]);
    const de_novo = await t
      .http()
      .post(`${API}/classes/${turmaA}/students`)
      .set(...bearer(profA))
      .send({ studentIds: [alunoA.id] });
    expect(de_novo.body.alreadyEnrolled).toEqual([alunoA.id]);
    const outra = await t
      .http()
      .post(`${API}/classes/${turmaA}/students`)
      .set(...bearer(profA))
      .send({ studentIds: [alunoB.id] });
    expect(outra.status).toBe(422);
  });

  it('isolamento: professor da escola B não vê turma da escola A (404); colega da mesma escola recebe 403', async () => {
    expect(
      (
        await t
          .http()
          .get(`${API}/classes/${turmaA}`)
          .set(...bearer(profB))
      ).status,
    ).toBe(404);
    expect(
      (
        await t
          .http()
          .post(`${API}/classes/${turmaA}/students`)
          .set(...bearer(profB))
          .send({ studentIds: [alunoB.id] })
      ).status,
    ).toBe(404);
    expect(
      (
        await t
          .http()
          .get(`${API}/classes/${turmaA}/students`)
          .set(...bearer(profA2))
      ).status,
    ).toBe(403);
    expect(
      (
        await t
          .http()
          .get(`${API}/classes/${turmaA}/students`)
          .set(...bearer(coordA))
      ).status,
    ).toBe(200);
  });

  it('aluno vê só as próprias turmas e lê a turma em que está, mas não a lista de alunos', async () => {
    const r = await t
      .http()
      .get(`${API}/classes`)
      .set(...bearer(alunoA));
    expect(r.body.items.map((x: { id: string }) => x.id)).toEqual([turmaA]);
    expect(
      (
        await t
          .http()
          .get(`${API}/classes/${turmaA}`)
          .set(...bearer(alunoA))
      ).status,
    ).toBe(200);
    expect(
      (
        await t
          .http()
          .get(`${API}/classes/${turmaA}/students`)
          .set(...bearer(alunoA))
      ).status,
    ).toBe(403);
    expect(
      (
        await t
          .http()
          .get(`${API}/classes`)
          .set(...bearer(alunoB))
      ).body.items,
    ).toEqual([]);
  });

  it('PATCH /classes/{id}/track define a trilha', async () => {
    const r = await t
      .http()
      .patch(`${API}/classes/${turmaA}/track`)
      .set(...bearer(profA))
      .send({ level: 'medio' });
    expect(r.status).toBe(200);
    expect(r.body.trackLevel).toBe('medio');
    expect(
      (
        await t
          .http()
          .patch(`${API}/classes/${turmaA}/track`)
          .set(...bearer(profA))
          .send({ level: 'superior' })
      ).status,
    ).toBe(422);
  });

  it('missão exige habilidade BNCC existente (422) e publica para a turma', async () => {
    const sem = await t
      .http()
      .post(`${API}/missions`)
      .set(...bearer(profA))
      .send({
        title: 'Efeito estufa',
        objective: 'Relacionar CO2 e temperatura',
        trackLevel: 'fundamental_ii',
        bnccCodes: [],
      });
    expect(sem.status).toBe(422);
    const inexistente = await t
      .http()
      .post(`${API}/missions`)
      .set(...bearer(profA))
      .send({
        title: 'Efeito estufa',
        objective: 'x',
        trackLevel: 'fundamental_ii',
        bnccCodes: ['EF07CI13', 'EF99XX99'],
      });
    expect(inexistente.status).toBe(422);
    expect(JSON.stringify(inexistente.body.errors)).toContain('EF99XX99');
    const ok = await t
      .http()
      .post(`${API}/missions`)
      .set(...bearer(profA))
      .send({
        title: 'Efeito estufa',
        objective: 'Relacionar CO2 e temperatura',
        trackLevel: 'fundamental_ii',
        bnccCodes: ['ef07ci13', 'EF07CI12'],
        parameters: { co2: 400 },
        classIds: [turmaA],
      });
    expect(ok.status).toBe(201);
    expect(ok.body).toMatchObject({
      status: 'published',
      bnccCodes: ['EF07CI12', 'EF07CI13'],
      classIds: [turmaA],
    });
    const lista = await t
      .http()
      .get(`${API}/missions?classId=${turmaA}`)
      .set(...bearer(alunoA));
    expect(lista.status).toBe(200);
    expect(lista.body.items).toHaveLength(1);
    expect(
      (
        await t
          .http()
          .get(`${API}/missions/${ok.body.id as string}`)
          .set(...bearer(alunoB))
      ).status,
    ).toBe(404);
    expect(
      (
        await t
          .http()
          .get(`${API}/missions?classId=${turmaA}`)
          .set(...bearer(alunoB))
      ).status,
    ).toBe(404);
    expect(
      (
        await t
          .http()
          .post(`${API}/missions/${ok.body.id as string}/publish`)
          .set(...bearer(profA2))
          .send({ classIds: [turmaA] })
      ).status,
    ).toBe(403);
  });

  it('catálogo é dado: operador revisa habilidade sem deploy; professor não', async () => {
    const lista = await t
      .http()
      .get(`${API}/curriculum/bncc-skills?competency=DATA_LITERACY`)
      .set(...bearer(profA));
    expect(lista.status).toBe(200);
    expect(
      lista.body.items.every(
        (h: { validationStatus: string }) =>
          h.validationStatus === 'pending_validation',
      ),
    ).toBe(true);
    expect(
      (
        await t
          .http()
          .patch(`${API}/curriculum/bncc-skills/EF07MA36`)
          .set(...bearer(profA))
          .send({ validationStatus: 'validated' })
      ).status,
    ).toBe(403);
    const r = await t
      .http()
      .patch(`${API}/curriculum/bncc-skills/EF07MA36`)
      .set(...bearer(operador))
      .send({ validationStatus: 'validated', catalogVersion: '2026.1' });
    expect(r.status).toBe(200);
    expect(r.body).toMatchObject({
      code: 'EF07MA36',
      validationStatus: 'validated',
      catalogVersion: '2026.1',
    });
    const inativa = await t
      .http()
      .patch(`${API}/curriculum/bncc-skills/EF07MA37`)
      .set(...bearer(operador))
      .send({ active: false });
    expect(inativa.body.active).toBe(false);
    const missao = await t
      .http()
      .post(`${API}/missions`)
      .set(...bearer(profA))
      .send({
        title: 'x',
        objective: 'y',
        trackLevel: 'fundamental_ii',
        bnccCodes: ['EF07MA37'],
      });
    expect(missao.status).toBe(422);
  });
});
