"""Valida a restauração em banco separado, usando somente o cluster fictício local."""
import os
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import manage

manage.prepare_development_environment()
server = manage._PGSERVER
backup = max((manage.BASE_DIR / "backups").glob("tudun-*.dump"), key=lambda item: item.stat().st_mtime)
database_name = "tudun_restore_validation"
main_uri = server.get_uri()

with psycopg.connect(main_uri, autocommit=True) as connection:
    connection.execute(f'DROP DATABASE IF EXISTS {database_name} WITH (FORCE)')
    connection.execute(f'CREATE DATABASE {database_name}')

try:
    os.environ["DATABASE_URL"] = server.get_uri(database_name)
    import django
    from django.core.management import call_command

    django.setup()
    call_command("restore_database", str(backup), confirm="RESTAURAR")
    count_queries = (
        "SELECT count(*) FROM auth_user",
        "SELECT count(*) FROM communities_community",
        "SELECT count(*) FROM identity_identityprofile",
        "SELECT count(*) FROM audit_auditevent",
        "SELECT count(*) FROM pg_indexes WHERE tablename = 'auth_user' AND indexname = 'auth_user_email_lower_unique'",
    )
    with psycopg.connect(server.get_uri(database_name)) as restored:
        restored_counts = tuple(restored.execute(query).fetchone()[0] for query in count_queries)
    with psycopg.connect(main_uri) as source:
        source_counts = tuple(source.execute(query).fetchone()[0] for query in count_queries)
    if restored_counts != source_counts or restored_counts[0] < 1 or restored_counts[-1] != 1:
        raise RuntimeError(f"Contagens divergentes: origem={source_counts}, restauração={restored_counts}")
    print(
        "RESTAURAÇÃO VALIDADA: "
        f"usuários={restored_counts[0]}, comunidades={restored_counts[1]}, "
        f"perfis={restored_counts[2]}, auditoria={restored_counts[3]}, índice_de_email={restored_counts[4]}"
    )
finally:
    with psycopg.connect(main_uri, autocommit=True) as connection:
        connection.execute(f'DROP DATABASE IF EXISTS {database_name} WITH (FORCE)')
    print("Banco temporário de validação removido.")
