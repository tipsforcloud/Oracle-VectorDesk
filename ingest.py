"""
Script de Ingesta y Vectorización de Documentos
Motor: Oracle Database 23ai / 26ai (Base DB o Autonomous Database)
Calcula embeddings locales en CPU y los almacena en columnas VECTOR de Oracle.
"""

import os
import array
import oracledb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Configuración de conexión Oracle Database 26ai
DB_USER = os.getenv("DB_USER", "app_support")
DB_PASSWORD = os.getenv("DB_PASSWORD", "CambiarPorTuPassword123!")
DB_DSN = os.getenv("DB_DSN", "localhost:1521/PDBLAB1")
WALLET_DIR = os.getenv("WALLET_DIR", None)
WALLET_PASSWORD = os.getenv("WALLET_PASSWORD", None)

SAMPLE_ARTICLES = [
    {
        "title": "Procedimiento de Restablecimiento de Contraseña Corporativa",
        "category": "Seguridad e Identidad",
        "content": (
            "Para restablecer la contraseña corporativa, el colaborador debe acceder al portal "
            "https://idm.empresa.com y seleccionar 'Olvidé mi contraseña'. Se enviará un código OTP "
            "de 6 dígitos al teléfono móvil corporativo registrado. El código tiene una validez de 5 minutos. "
            "La nueva contraseña debe tener mínimo 12 caracteres, incluir una mayúscula, un número y un símbolo."
        )
    },
    {
        "title": "Configuración de la VPN Corporativa en Windows y Mac",
        "category": "Redes y Conectividad",
        "content": (
            "Para conectar a la VPN corporativa desde equipos portátiles: 1. Abrir la aplicación Cisco AnyConnect o FortiClient. "
            "2. En la dirección del servidor ingresar 'vpn.empresa.com'. 3. Ingresar usuario corporativo y clave. "
            "4. Aprobar la notificación Push en la app de autenticación multifactor (MFA). "
            "Si se presenta el error 'Gateway not reachable', verificar que el DNS primario esté configurado en 1.1.1.1 o reiniciar el router doméstico."
        )
    },
    {
        "title": "Desbloqueo de Cuenta por Intentos Fallidos",
        "category": "Seguridad e Identidad",
        "content": (
            "Si un usuario ingresa su contraseña erróneamente más de 5 veces consecutivas, el directorio activo "
            "bloqueará la cuenta automáticamente por 30 minutos. Para un desbloqueo inmediato, el usuario debe comunicarse "
            "con la línea interna de soporte ext. 4357 o solicitar a su supervisor directo que envíe un correo autorizando "
            "el desbloqueo al buzón soporte.seguridad@empresa.com."
        )
    },
    {
        "title": "Solicitud de Licencias de Software Especializado",
        "category": "Gestión de Activos TI",
        "content": (
            "Las solicitudes de software (Adobe, AutoCAD, JetBrains, PowerBI Pro) deben canalizarse mediante el ticket tipo "
            "'Aprovisionamiento de Software' en el portal Jira Service Desk, adjuntando la aprobación por correo del gerente de área "
            "y el centro de costos respectivo. El tiempo estimado de entrega de la licencia es de 48 horas hábiles."
        )
    }
]


def get_connection():
    if WALLET_DIR:
        return oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN,
            wallet_location=WALLET_DIR,
            wallet_password=WALLET_PASSWORD
        )
    else:
        return oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN
        )


def ingest_data():
    print("Cargando modelo de embeddings de alta precisión (768 dimensiones) en CPU...")
    model = SentenceTransformer("intfloat/multilingual-e5-base")
    
    print(f"Conectando a Oracle Database 23ai en {DB_DSN}...")
    conn = get_connection()
    cur = conn.cursor()

    print("Insertando artículos y vectores nativos en Oracle...")
    insert_sql = """
        INSERT INTO knowledge_base (title, category, content, embedding)
        VALUES (:title, :category, :content, :embedding)
    """

    for article in SAMPLE_ARTICLES:
        # Los modelos E5 utilizan el prefijo 'passage: ' para documentos a indexar
        passage_text = f"passage: {article['title']}. {article['content']}"
        # Generar embedding vectorial (768 floats normalizados)
        embedding_list = model.encode(passage_text, normalize_embeddings=True).tolist()
        vector_data = array.array("f", embedding_list)
        
        cur.execute(insert_sql, {
            "title": article["title"],
            "category": article["category"],
            "content": article["content"],
            "embedding": vector_data
        })

    conn.commit()
    cur.close()
    conn.close()
    print("¡Ingesta en Oracle 23ai completada exitosamente!")


if __name__ == "__main__":
    ingest_data()
