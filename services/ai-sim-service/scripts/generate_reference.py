"""Extrator determinístico da espinha factual do guia de referência do ai-sim-service.

Percorre ``src/ecosfera_ai/**`` com o módulo ``ast`` da biblioteca padrão — sem regex e
sem importar/executar o código auditado — e emite um JSON com módulos, classes, funções,
campos, constantes e o conteúdo dos ``*.yaml`` de ciência versionada.

A saída é a FONTE FACTUAL do guia em ``docs/reference/``: assinaturas, defaults e valores
de parâmetros vêm daqui, nunca de memória. Re-execute após mudanças no código para
detectar o que o guia precisa refletir.

Uso:
    uv run python scripts/generate_reference.py            # JSON no stdout
    uv run python scripts/generate_reference.py -o out.json
    uv run python scripts/generate_reference.py --root src/ecosfera_ai --summary
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml

# ─────────────────────────────────────────────────────────────────────────────
# Configuração de varredura
# ─────────────────────────────────────────────────────────────────────────────

#: Diretório-raiz padrão do código de produção auditado (relativo à raiz do serviço).
DEFAULT_SOURCE_ROOT = "src/ecosfera_ai"

#: Diretórios adicionais varridos em busca de YAML de ciência versionada.
DEFAULT_YAML_ROOTS = ("src/ecosfera_ai", "configs")

#: Nenhum arquivo sob estes segmentos entra no guia (testes e artefatos gerados).
EXCLUDED_DIR_NAMES = frozenset({"__pycache__", "tests", ".venv", ".ruff_cache", ".mypy_cache"})

#: YAML de infraestrutura, fora do escopo de ciência versionada.
EXCLUDED_YAML_NAMES = frozenset({"docker-compose.yml"})

#: Bases que marcam uma classe como Protocol/Enum/TypedDict para o guia.
PROTOCOL_BASES = frozenset({"Protocol", "typing.Protocol", "t.Protocol"})
ENUM_BASES = frozenset({"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag", "enum.Enum"})


# ─────────────────────────────────────────────────────────────────────────────
# Modelo do relatório
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class FunctionInfo:
    """Uma função de módulo ou método de classe, com assinatura textual completa."""

    name: str
    qualname: str
    lineno: int
    signature: str
    returns: str | None
    is_async: bool
    decorators: list[str]
    doc: str | None


@dataclass
class AttributeInfo:
    """Um atributo de classe, campo de dataclass, membro de Enum ou constante de módulo."""

    name: str
    annotation: str | None
    default: str | None
    lineno: int
    doc: str | None = None


@dataclass
class ClassInfo:
    """Uma classe do módulo, com suas bases, campos e métodos."""

    name: str
    lineno: int
    bases: list[str]
    decorators: list[str]
    is_dataclass: bool
    is_protocol: bool
    is_enum: bool
    doc: str | None
    attributes: list[AttributeInfo] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """Um arquivo ``.py`` de produção: docstring de topo, classes, funções e constantes."""

    path: str
    module: str
    loc: int
    doc: str | None
    imports: list[str] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    constants: list[AttributeInfo] = field(default_factory=list)


@dataclass
class YamlInfo:
    """Um arquivo de ciência versionada: chaves achatadas + árvore original."""

    path: str
    flat: dict[str, Any]
    tree: Any


@dataclass
class Report:
    """A saída completa do extrator."""

    generated_at: str
    commit: str
    source_root: str
    modules: list[ModuleInfo]
    yaml_files: list[YamlInfo]


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de leitura de AST
# ─────────────────────────────────────────────────────────────────────────────


def _src(node: ast.AST | None) -> str | None:
    """Devolve o código-fonte de um nó como texto, ou ``None`` se não houver nó."""
    if node is None:
        return None
    return ast.unparse(node)


def _first_doc_line(node: ast.AST) -> str | None:
    """Primeira linha do docstring do nó (sem quebras), ou ``None`` se não houver."""
    if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
        return None
    raw = ast.get_docstring(node, clean=True)
    if not raw:
        return None
    return raw.strip().splitlines()[0].strip()


def _decorator_names(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Nomes textuais dos decoradores, na ordem em que aparecem no código."""
    return [ast.unparse(d) for d in node.decorator_list]


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Assinatura textual completa, com anotações e defaults exatos do código."""
    args = node.args
    parts: list[str] = []

    positional = args.posonlyargs + args.args
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(args.defaults))
    defaults += list(args.defaults)

    for index, (arg, default) in enumerate(zip(positional, defaults, strict=True)):
        rendered = arg.arg
        if arg.annotation is not None:
            rendered += f": {ast.unparse(arg.annotation)}"
        if default is not None:
            separator = " = " if arg.annotation else "="
            rendered += f"{separator}{ast.unparse(default)}"
        parts.append(rendered)
        if args.posonlyargs and index == len(args.posonlyargs) - 1:
            parts.append("/")

    if args.vararg is not None:
        rendered = f"*{args.vararg.arg}"
        if args.vararg.annotation is not None:
            rendered += f": {ast.unparse(args.vararg.annotation)}"
        parts.append(rendered)
    elif args.kwonlyargs:
        parts.append("*")

    for arg, kw_default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        rendered = arg.arg
        if arg.annotation is not None:
            rendered += f": {ast.unparse(arg.annotation)}"
        if kw_default is not None:
            rendered += (
                f" = {ast.unparse(kw_default)}" if arg.annotation else f"={ast.unparse(kw_default)}"
            )
        parts.append(rendered)

    if args.kwarg is not None:
        rendered = f"**{args.kwarg.arg}"
        if args.kwarg.annotation is not None:
            rendered += f": {ast.unparse(args.kwarg.annotation)}"
        parts.append(rendered)

    returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
    return f"{prefix}{node.name}({', '.join(parts)}){returns}"


def _function_info(
    node: ast.FunctionDef | ast.AsyncFunctionDef, *, parent: str | None = None
) -> FunctionInfo:
    """Converte um nó de função/método no registro do relatório."""
    return FunctionInfo(
        name=node.name,
        qualname=f"{parent}.{node.name}" if parent else node.name,
        lineno=node.lineno,
        signature=_signature(node),
        returns=_src(node.returns),
        is_async=isinstance(node, ast.AsyncFunctionDef),
        decorators=_decorator_names(node),
        doc=_first_doc_line(node),
    )


def _is_constant_name(name: str) -> bool:
    """Verdadeiro para NOME_MAIUSCULO (constante de módulo), incluindo ``_PRIVADA``."""
    stripped = name.lstrip("_")
    return bool(stripped) and stripped.upper() == stripped and any(c.isalpha() for c in stripped)


def _assignments(body: Iterable[ast.stmt]) -> Iterator[tuple[str, str | None, str | None, int]]:
    """Itera ``(nome, anotação, default, linha)`` das atribuições diretas de um corpo."""
    for stmt in body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            yield stmt.target.id, _src(stmt.annotation), _src(stmt.value), stmt.lineno
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    yield target.id, None, _src(stmt.value), stmt.lineno


def _attribute_docs(body: list[ast.stmt]) -> dict[str, str]:
    """Mapeia atributo → docstring quando a string literal segue a atribuição (PEP 258)."""
    docs: dict[str, str] = {}
    for previous, current in pairwise(body):
        if not (
            isinstance(current, ast.Expr)
            and isinstance(current.value, ast.Constant)
            and isinstance(current.value.value, str)
        ):
            continue
        target: str | None = None
        if isinstance(previous, ast.AnnAssign) and isinstance(previous.target, ast.Name):
            target = previous.target.id
        elif (
            isinstance(previous, ast.Assign)
            and len(previous.targets) == 1
            and isinstance(previous.targets[0], ast.Name)
        ):
            target = previous.targets[0].id
        if target is not None:
            docs[target] = current.value.value.strip().splitlines()[0].strip()
    return docs


def _class_info(node: ast.ClassDef) -> ClassInfo:
    """Converte um nó de classe no registro do relatório, com campos e métodos."""
    bases = [ast.unparse(b) for b in node.bases]
    decorators = _decorator_names(node)
    docs = _attribute_docs(node.body)

    attributes = [
        AttributeInfo(
            name=name,
            annotation=annotation,
            default=default,
            lineno=lineno,
            doc=docs.get(name),
        )
        for name, annotation, default, lineno in _assignments(node.body)
    ]
    methods = [
        _function_info(child, parent=node.name)
        for child in node.body
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
    ]

    return ClassInfo(
        name=node.name,
        lineno=node.lineno,
        bases=bases,
        decorators=decorators,
        is_dataclass=any("dataclass" in d for d in decorators),
        is_protocol=any(b in PROTOCOL_BASES for b in bases),
        is_enum=any(b in ENUM_BASES for b in bases),
        doc=_first_doc_line(node),
        attributes=attributes,
        methods=methods,
    )


def _module_imports(tree: ast.Module) -> list[str]:
    """Módulos importados no topo do arquivo — usado para inferir acoplamentos."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return sorted(set(found))


def parse_module(path: Path, source_root: Path) -> ModuleInfo:
    """Lê um arquivo ``.py`` e devolve seu registro factual (sem executá-lo)."""
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))

    relative = path.relative_to(source_root.parent.parent)
    dotted = ".".join(path.relative_to(source_root.parent).with_suffix("").parts)

    return ModuleInfo(
        path=relative.as_posix(),
        module=dotted,
        loc=len(text.splitlines()),
        doc=_first_doc_line(tree),
        imports=_module_imports(tree),
        classes=[_class_info(n) for n in tree.body if isinstance(n, ast.ClassDef)],
        functions=[
            _function_info(n)
            for n in tree.body
            if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
        ],
        constants=[
            AttributeInfo(
                name=name,
                annotation=annotation,
                default=default,
                lineno=lineno,
                doc=_attribute_docs(tree.body).get(name),
            )
            for name, annotation, default, lineno in _assignments(tree.body)
            if _is_constant_name(name)
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# YAML de ciência versionada
# ─────────────────────────────────────────────────────────────────────────────


def _flatten(node: Any, prefix: str = "") -> dict[str, Any]:
    """Achata um YAML em ``chave.pontilhada -> valor escalar`` para a Mesa de Calibração."""
    flat: dict[str, Any] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            flat.update(_flatten(value, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            flat.update(_flatten(value, f"{prefix}[{index}]"))
    else:
        flat[prefix] = node
    return flat


def parse_yaml(path: Path, repo_root: Path) -> YamlInfo:
    """Lê um YAML de parâmetros e devolve chaves achatadas + árvore original."""
    tree = yaml.safe_load(path.read_text(encoding="utf-8"))
    return YamlInfo(
        path=path.relative_to(repo_root).as_posix(),
        flat=_flatten(tree),
        tree=tree,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Varredura
# ─────────────────────────────────────────────────────────────────────────────


def _walk(root: Path, suffixes: tuple[str, ...]) -> Iterator[Path]:
    """Percorre ``root`` devolvendo arquivos com os sufixos pedidos, pulando exclusões."""
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if EXCLUDED_DIR_NAMES & set(path.parts):
            continue
        yield path


def _git_commit(repo_root: Path) -> str:
    """Hash curto do HEAD, ou ``"desconhecido"`` fora de um repositório git."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "desconhecido"
    return result.stdout.strip()


def build_report(repo_root: Path, source_root: Path, yaml_roots: Iterable[Path]) -> Report:
    """Monta o relatório completo: módulos de produção + YAML de ciência versionada."""
    modules = [parse_module(path, source_root) for path in _walk(source_root, (".py",))]

    yaml_files: list[YamlInfo] = []
    seen: set[Path] = set()
    for yaml_root in yaml_roots:
        if not yaml_root.exists():
            continue
        for path in _walk(yaml_root, (".yaml", ".yml")):
            if path in seen or path.name in EXCLUDED_YAML_NAMES:
                continue
            seen.add(path)
            yaml_files.append(parse_yaml(path, repo_root))

    return Report(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        commit=_git_commit(repo_root),
        source_root=source_root.relative_to(repo_root).as_posix(),
        modules=modules,
        yaml_files=sorted(yaml_files, key=lambda y: y.path),
    )


def summarize(report: Report) -> str:
    """Contagens de conferência para o relatório final da auditoria."""
    classes = sum(len(m.classes) for m in report.modules)
    methods = sum(len(c.methods) for m in report.modules for c in m.classes)
    functions = sum(len(m.functions) for m in report.modules)
    constants = sum(len(m.constants) for m in report.modules)
    yaml_keys = sum(len(y.flat) for y in report.yaml_files)
    return (
        f"commit={report.commit} "
        f"modulos={len(report.modules)} classes={classes} metodos={methods} "
        f"funcoes={functions} constantes={constants} "
        f"yaml={len(report.yaml_files)} chaves_yaml={yaml_keys}"
    )


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Raiz do serviço ai-sim-service (padrão: o diretório-pai de scripts/).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help=f"Raiz do código de produção (padrão: {DEFAULT_SOURCE_ROOT}).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Arquivo de saída do JSON (padrão: stdout).",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Imprime apenas as contagens de conferência, sem o JSON.",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root.resolve()
    source_root: Path = (args.root or (repo_root / DEFAULT_SOURCE_ROOT)).resolve()
    if not source_root.is_dir():
        print(f"erro: raiz de código inexistente: {source_root}", file=sys.stderr)
        return 1

    report = build_report(repo_root, source_root, [repo_root / p for p in DEFAULT_YAML_ROOTS])

    if args.summary:
        print(summarize(report))
        return 0

    payload = json.dumps(asdict(report), indent=2, ensure_ascii=False, default=str)
    if args.output is not None:
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(summarize(report), file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
