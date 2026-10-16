#!/usr/bin/env python3
"""
Script de Mantenimiento y Reinicio de Base de Datos (Reset DB)
Oracle-VectorDesk: Enterprise Support & Helpdesk RAG on Oracle Database 26ai

Permite purgar o reinstalar de forma limpia las tablas KNOWLEDGE_BASE y AGENT_TICKETS_LOG
en caso de pruebas, reindexación completa o reinstalación del agente.
"""

import os
import sys
from pathlib import Path

# Localizar la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.database import get_connection, test_db_connection


def reset_database():
    print("=" * 80)
    print(" Oracle-VectorDesk: Reinicio y Purga de Tablas en Oracle Database 26ai")
    print("=" * 80)

    # 1. Probar conectividad
    print("\n[1/3] Verificando conectividad con la Base de Datos...")
    test_res = test_db_connection()
    if not test_res.get("ok"):
        print(f"  [!] Error conectando a la base de datos: {test_res.get('error')}")
        print("      Verifica las credenciales y DSN en el archivo '.env'.")
        sys.exit(1)
    print(f"  [✓] Conectado exitosamente: {test_res.get('banner')}")

    # 2. Consultar tablas existentes
    print("\n[2/3] Inspeccionando estructuras en el esquema del usuario...")
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT table_name 
        FROM user_tables 
        WHERE table_name IN ('KNOWLEDGE_BASE', 'AGENT_TICKETS_LOG')
    """)
    existing_tables = [row[0] for row in cur.fetchall()]

    if not existing_tables:
        print("  [i] No se encontraron tablas de Oracle-VectorDesk en este esquema. Está completamente limpio.")
    else:
        print(f"  [!] Tablas detectadas para purgar: {', '.join(existing_tables)}")
        confirm = input("\n  ¿Estás SEGURO de eliminar estas tablas y todos sus datos vectoriales? [s/N]: ").strip().lower()
        if confirm != 's':
            print("  Operación cancelada. No se realizaron cambios.")
            conn.close()
            sys.exit(0)

        print("\n  Eliminando tablas...")
        for table in existing_tables:
            try:
                cur.execute(f"DROP TABLE {table} PURGE")
                print(f"  [✓] Tabla '{table}' eliminada (PURGE).")
            except Exception as e:
                print(f"  [!] Error al eliminar '{table}': {e}")
        conn.commit()

    # 3. Preguntar si desea recrearlas limpias
    print("\n[3/3] Recreación de estructuras...")
    recreate = input("  ¿Deseas recrear las tablas vacías ahora utilizando 'sql/init_db.sql'? [S/n]: ").strip().lower()
    if recreate != 'n':
        sql_file = BASE_DIR / "sql" / "init_db.sql"
        if not sql_file.exists():
            print(f"  [!] No se encontró el archivo: {sql_file}")
            conn.close()
            sys.exit(1)

        with open(str(sql_file), "r", encoding="utf-8") as f:
            content = f.read()

        # Filtrar líneas de comentarios para no perder sentencias que inicien con comentario
        clean_lines = [l for l in content.splitlines() if not l.strip().startswith("--")]
        statements = [stmt.strip() for stmt in "\n".join(clean_lines).split(";") if stmt.strip()]

        for stmt in statements:
            try:
                cur.execute(stmt)
            except Exception as err:
                err_str = str(err)
                if "ORA-00955" in err_str or "already exists" in err_str:
                    pass
                elif "ORA-51962" in err_str:
                    print("    [i] Nota Informativa: 'vector_memory_size' no está asignado en esta instancia (Oracle SE2 o default).")
                    print("        Oracle AI Vector Search operará en modo 'Exact Vector Search' (búsqueda vectorial exacta SIMD),")
                    print("        que no requiere memoria SGA adicional y ofrece 100% de precisión y latencia < 20 ms.")
                else:
                    first_line = stmt.splitlines()[0] if stmt.splitlines() else stmt
                    print(f"    [!] Error en sentencia [{first_line[:40]}...]: {err}")
        conn.commit()

        # Validar existencia de las tablas
        cur.execute("""
            SELECT table_name 
            FROM user_tables 
            WHERE table_name IN ('KNOWLEDGE_BASE', 'AGENT_TICKETS_LOG')
        """)
        created = [row[0] for row in cur.fetchall()]
        if "KNOWLEDGE_BASE" in created and "AGENT_TICKETS_LOG" in created:
            print(f"  [✓] Estructuras recreadas y verificadas exitosamente: {', '.join(created)}")
        else:
            print(f"  [!] Advertencia: No se pudieron verificar todas las tablas creadas. Encontradas: {created}")
    else:
        print("  Tablas purgadas. La base de datos queda limpia sin estructuras de Oracle-VectorDesk.")

    conn.close()
    print("\n" + "=" * 80)
    print(" Operación de mantenimiento completada exitosamente.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    reset_database()
