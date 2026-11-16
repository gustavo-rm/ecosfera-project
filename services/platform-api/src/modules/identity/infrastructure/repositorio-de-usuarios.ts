import type { DataSource, Repository } from 'typeorm';

import type { Json } from '../../../shared/database/colunas';
import type { Papel } from '../../../shared/kernel/papeis';
import type { RepositorioDeUsuarios } from '../domain/portas';
import { mesclarPreferencias, type MudancaDePreferencias, Usuario } from '../domain/usuario';
import { UsuarioEntity } from './persistencia/usuario.entity';

export function paraDominio(e: UsuarioEntity): Usuario {
  return new Usuario(
    e.id,
    e.schoolId,
    e.name,
    e.email,
    e.role,
    e.isMinor,
    e.status,
    mesclarPreferencias(e.preferences as MudancaDePreferencias, {}),
    e.passwordHash,
  );
}

export class RepositorioDeUsuariosTypeorm implements RepositorioDeUsuarios {
  private readonly repo: Repository<UsuarioEntity>;
  constructor(ds: DataSource) {
    this.repo = ds.getRepository(UsuarioEntity);
  }

  async porId(id: string): Promise<Usuario | null> {
    const e = await this.repo.findOneBy({ id });
    return e ? paraDominio(e) : null;
  }

  async porEmail(email: string): Promise<Usuario | null> {
    const e = await this.repo.findOneBy({ email });
    return e ? paraDominio(e) : null;
  }

  async salvar(u: Usuario): Promise<void> {
    await this.repo.update(
      { id: u.id },
      {
        schoolId: u.escolaId,
        name: u.nome,
        email: u.email,
        role: u.papel,
        isMinor: u.menor,
        status: u.situacao,
        preferences: u.preferencias as unknown as Json,
        passwordHash: u.senhaHash,
        pseudonymizedAt: u.situacao === 'pseudonymized' ? new Date() : null,
        updatedAt: new Date(),
      },
    );
  }

  async inserir(u: Omit<Usuario, 'id' | 'podeAutenticar' | 'alterarPapel' | 'pseudonimizar'>): Promise<Usuario> {
    const e = await this.repo.save(
      this.repo.create({
        schoolId: u.escolaId,
        name: u.nome,
        email: u.email,
        role: u.papel,
        isMinor: u.menor,
        status: u.situacao,
        preferences: u.preferencias as unknown as Json,
        passwordHash: u.senhaHash,
      }),
    );
    return paraDominio(e);
  }

  async listarDaEscola(escolaId: string, papel: Papel | undefined, pagina: number, tamanho: number) {
    const [itens, total] = await this.repo.findAndCount({
      where: { schoolId: escolaId, ...(papel ? { role: papel } : {}) },
      order: { createdAt: 'ASC', id: 'ASC' },
      skip: (pagina - 1) * tamanho,
      take: tamanho,
    });
    return { itens: itens.map(paraDominio), total };
  }
}
