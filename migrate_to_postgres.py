"""Migra dados de SQLite (instance/valor_futuro.db) para PostgreSQL.

Uso:
    python migrate_to_postgres.py "<postgres-url>"

A URL pode estar no formato `postgres://user:pass@host:port/db` (Render/Heroku)
ou `postgresql://...`. O script reescreve automaticamente.

O que faz:
  1. Lê o esquema da BD SQLite via reflexão (não depende dos modelos).
  2. Recria as tabelas no Postgres caso não existam.
  3. Copia todas as linhas preservando os IDs originais (truncate + insert).
  4. Reposiciona as sequences serial do Postgres para o próximo MAX(id)+1.

Idempotente: pode correr várias vezes — substitui o conteúdo no destino.
"""
from __future__ import annotations

import os
import sys
from sqlalchemy import MetaData, create_engine, inspect, text


def _normalise_url(url: str) -> str:
    if url.startswith('postgres://'):
        return 'postgresql://' + url[len('postgres://'):]
    return url


def _redact(url: str) -> str:
    """Esconde a password na URL para imprimir nos logs."""
    if '@' not in url:
        return url
    head, tail = url.rsplit('@', 1)
    if '//' in head and ':' in head.split('//', 1)[1]:
        scheme, rest = head.split('//', 1)
        user = rest.split(':', 1)[0]
        return f'{scheme}//{user}:***@{tail}'
    return url


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__)
        return 0 if len(sys.argv) >= 2 else 1

    target_url = _normalise_url(sys.argv[1])
    sqlite_path = os.path.abspath(os.path.join('instance', 'valor_futuro.db'))

    if not os.path.exists(sqlite_path):
        print(f'[ERRO] BD SQLite não encontrada em: {sqlite_path}')
        return 1

    src_url = f'sqlite:///{sqlite_path}'

    print(f'Origem:  {src_url}')
    print(f'Destino: {_redact(target_url)}')
    print()

    src = create_engine(src_url)
    dst = create_engine(target_url, pool_pre_ping=True)

    # 1) Refletir o schema da origem
    metadata = MetaData()
    metadata.reflect(bind=src)

    if not metadata.tables:
        print('[ERRO] BD SQLite vazia (sem tabelas).')
        return 1

    print(f'Tabelas detectadas: {", ".join(metadata.tables.keys())}')
    print()

    # 2) Criar schema no destino
    print('A criar schema no Postgres (se necessário)…')
    metadata.create_all(bind=dst)

    # 3) Copiar dados (preservando IDs) — limpa primeiro, em ordem inversa de FK
    table_order = list(metadata.sorted_tables)
    total_rows = 0

    # Apagar conteúdo no destino na ordem inversa para respeitar FKs
    print('A limpar conteúdo existente no destino…')
    with dst.begin() as conn:
        for table in reversed(table_order):
            try:
                conn.execute(table.delete())
            except Exception as e:
                print(f'  [warn] {table.name}: {e}')

    print('\nA copiar linhas:')
    for table in table_order:
        with src.connect() as sc:
            rows = sc.execute(table.select()).fetchall()
        if not rows:
            print(f'  {table.name:<20} 0 linhas')
            continue
        with dst.begin() as dc:
            dc.execute(table.insert(), [dict(r._mapping) for r in rows])
        total_rows += len(rows)
        print(f'  {table.name:<20} {len(rows)} linhas copiadas')

    # 4) Resetar sequences do Postgres para evitar colisões em INSERTs futuros
    print('\nA actualizar sequences:')
    inspector = inspect(dst)
    with dst.begin() as conn:
        for table in table_order:
            try:
                # Procura a coluna PK serial (geralmente "id")
                pk_cols = [c.name for c in table.primary_key.columns]
                if not pk_cols:
                    continue
                pk = pk_cols[0]
                # pg_get_serial_sequence devolve null se a coluna não tiver sequence
                stmt = text(
                    f"SELECT setval(pg_get_serial_sequence(:t, :c), "
                    f"COALESCE((SELECT MAX(\"{pk}\") FROM \"{table.name}\"), 1), "
                    f"(SELECT COUNT(*) FROM \"{table.name}\") > 0)"
                )
                result = conn.execute(stmt, {'t': table.name, 'c': pk}).scalar()
                if result is not None:
                    print(f'  {table.name}.{pk} sequence -> {result}')
                else:
                    print(f'  {table.name}.{pk} (sem sequence — ignorado)')
            except Exception as e:
                print(f'  [warn] {table.name}: {e}')

    print(f'\n[OK] Migração concluída: {total_rows} linhas no total.')
    print('\nPróximo passo:')
    print('  1. Adiciona DATABASE_URL ao teu .env (mesma URL do destino)')
    print('  2. Reinicia a app: python app.py')
    print('  3. Confirma os imóveis em http://127.0.0.1:5000/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
