"""
Generador de Documentos PDF Corporativos de Demostración
Genera 10 PDFs realistas de soporte de TI y políticas corporativas
para el Agente de Soporte RAG con Oracle Database 26ai.
"""

import os
import sys

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
except ImportError:
    print("ReportLab no está instalado. Instálalo ejecutando: pip install reportlab")
    sys.exit(1)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs_demo")
os.makedirs(OUTPUT_DIR, exist_ok=True)

DOCUMENTS_DATA = [
    {
        "filename": "POL-TI-01_Acceso_Red_Wifi_Visitantes.pdf",
        "code": "POL-TI-01",
        "title": "Política de Acceso a Red Wi-Fi Corporativa y de Visitantes",
        "category": "Redes y Conectividad",
        "version": "2.4",
        "date": "2026-02-15",
        "sections": [
            ("1. Propósito y Alcance", 
             "Esta política establece los lineamientos de seguridad para la conexión a las redes inalámbricas de InnovaCorp Technologies en todas sus sedes y sucursales."),
            ("2. Redes Wi-Fi Disponibles",
             "<b>InnovaCorp-Corp:</b> Red exclusiva para portátiles corporativos enrolados en el dominio. Autenticación mediante certificados digitales 802.1X (WPA3-Enterprise).<br/>"
             "<b>InnovaCorp-Guest:</b> Red destinada a proveedores, clientes y visitantes externos. Requiere registro mediante portal cautivo."),
            ("3. Solicitud de Vouchers para Visitantes",
             "Para otorgar acceso a un visitante externo, la recepcionista o el anfitrión del empleado debe ingresar al portal interno <u>https://wifi-guest.innovacorp.local</u> o llamar a la recepción en la <b>ext. 1001</b>. Se generará un código PIN de 6 dígitos que tiene una vigencia máxima de <b>8 horas continuas</b>."),
            ("4. Restricciones Técnicas",
             "La red de visitantes tiene activo el aislamiento de clientes (Client Isolation). Se bloquea automáticamente el tráfico P2P (BitTorrent, Tor) y servicios de streaming recreativo (Netflix, Twitch) están limitados a 1.5 Mbps por usuario. Queda prohibido conectar servidores o equipos sin antivirus activo.")
        ]
    },
    {
        "filename": "PROC-TI-02_Solicitud_Renovacion_Equipos_Hardware.pdf",
        "code": "PROC-TI-02",
        "title": "Procedimiento para Solicitud y Renovación de Equipos de Cómputo",
        "category": "Gestión de Activos TI",
        "version": "3.1",
        "date": "2026-01-20",
        "sections": [
            ("1. Ciclo de Vida del Hardware",
             "Los equipos portátiles estándar (Lenovo ThinkPad T14 / Dell Latitude 5440) tienen un ciclo de renovación obligatorio de <b>36 meses (3 años)</b>. Las estaciones de desarrollo y alto rendimiento (MacBook Pro M3 / Dell Precision) se renuevan cada <b>48 meses (4 años)</b>."),
            ("2. Proceso de Solicitud de Renovación",
             "Para iniciar el reemplazo, el colaborador debe registrar un ticket en Jira Service Desk bajo la categoría <b>'HW-RENOVACION'</b> indicando el número de serie de su equipo actual. El ticket requiere aprobación obligatoria del Gerente de Área y del Director de Finanzas si el costo del nuevo equipo supera los USD $1,500."),
            ("3. Entrega y Devolución del Equipo Anterior",
             "El colaborador recibirá su nuevo equipo configurado en el almacén de TI (Piso 3, Torre A). Dispone de un plazo perentorio de <b>5 días hábiles</b> para transferir sus archivos a OneDrive y entregar el equipo anterior limpio. Si no se devuelve en este plazo, se suspenderán los permisos de acceso temporalmente.")
        ]
    },
    {
        "filename": "GUIA-TI-03_Configuracion_MFA_Microsoft_Authenticator.pdf",
        "code": "GUIA-TI-03",
        "title": "Guía de Enrolamiento y Uso de Autenticación Multifactor (MFA)",
        "category": "Seguridad e Identidad",
        "version": "1.8",
        "date": "2026-03-01",
        "sections": [
            ("1. Obligatoriedad del MFA",
             "De acuerdo con la norma de ciberseguridad corporativa, todos los colaboradores y contratistas deben contar con MFA activo para acceder al correo, VPN, CRM y portales web de InnovaCorp."),
            ("2. Proceso de Registro Inicial",
             "1. Acceder desde una computadora conectada a la red a <u>https://aka.ms/mfasetup</u>.<br/>"
             "2. Instalar la aplicación <b>Microsoft Authenticator</b> en el teléfono móvil corporativo o personal.<br/>"
             "3. Seleccionar 'Agregar cuenta de trabajo o escuela' y escanear el código QR en pantalla.<br/>"
             "4. Confirmar el inicio de sesión aprobando la notificación con coincidencia de número de 2 dígitos."),
            ("3. Métodos Secundarios y Restricciones",
             "Queda terminantemente prohibido el uso de SMS o llamadas como método de autenticación primario. En caso de pérdida de teléfono, el colaborador debe solicitar un <b>Pase de Acceso Temporal (TAP)</b> con vigencia de 4 horas escribiendo a <u>seguridad.identidad@innovacorp.internal</u>."),
            ("4. Solución al Error 'MFA Loop'",
             "Si el navegador entra en un bucle continuo pidiendo confirmación de MFA, borrar cookies y caché en Google Chrome o Microsoft Edge, o abrir una ventana de incógnito.")
        ]
    },
    {
        "filename": "PROC-TI-04_Solicitud_Accesos_Roles_SAP_ERP.pdf",
        "code": "PROC-TI-04",
        "title": "Procedimiento de Solicitud de Roles y Accesos en ERP SAP S/4HANA",
        "category": "Aplicaciones Corporativas",
        "version": "4.0",
        "date": "2026-02-10",
        "sections": [
            ("1. Catálogo de Roles Estándar",
             "Los accesos a SAP S/4HANA se rigen por el principio de mínimo privilegio. Los roles base son:<br/>"
             "• <b>Z_FI_CONTABILIDAD_GENERAL:</b> Registro de pólizas, consultas de balances contables.<br/>"
             "• <b>Z_MM_COMPRAS_APROBADOR:</b> Creación y liberación de órdenes de compra.<br/>"
             "• <b>Z_SD_FACTURACION_CONSULTA:</b> Consulta de pedidos de venta y facturas."),
            ("2. Formulario y Flujo de Aprobación",
             "El usuario debe descargar el formulario <b>FORM-SAP-SEC-04</b> desde la intranet, completarlo con los módulos solicitados y justificación de negocio. Requiere 3 firmas secuenciales: 1) Jefe Inmediato, 2) Business Process Owner (BPO) del módulo, 3) Oficial de Seguridad de la Información (CISO)."),
            ("3. Tiempos de Atención y Bloqueo por Inactividad",
             "El SLA estándar de asignación de roles es de <b>72 horas hábiles</b> tras recibir todas las aprobaciones. Las cuentas que permanezcan sin iniciar sesión durante <b>60 días consecutivos</b> son bloqueadas automáticamente por el job nocturno <code>Z_AUTO_LOCK_USERS</code>.")
        ]
    },
    {
        "filename": "POL-TI-05_Politica_Uso_Dispositivos_Moviles_BYOD.pdf",
        "code": "POL-TI-05",
        "title": "Política de Uso de Dispositivos Móviles Personales en el Trabajo (BYOD)",
        "category": "Seguridad de la Información",
        "version": "2.2",
        "date": "2026-01-15",
        "sections": [
            ("1. Requisitos Técnicos Obligatorios",
             "Cualquier smartphone o tablet personal que sincronice correo o Teams corporativo debe contar con sistema operativo <b>iOS 16.0 o Android 13 en adelante</b>, no poseer modificaciones root o jailbreak, y tener activo un PIN de seguridad de mínimo 6 dígitos o biometría."),
            ("2. Gestión de Dispositivos Móviles (MDM)",
             "El dispositivo debe ser registrado a través de la aplicación <b>Portal de Empresa de Microsoft Intune</b>. Esto crea un contenedor de trabajo cifrado y aislado de las aplicaciones personales del usuario."),
            ("3. Protocolo en Caso de Pérdida o Robo",
             "En caso de extravío o hurto del teléfono móvil, el empleado debe comunicarse de inmediato con la línea de emergencia del SOC al <b>+1-800-555-0199</b> o escribir a <u>soc-alert@innovacorp.internal</u>. TI ejecutará un <b>Borrado Selectivo Remoto (Selective Wipe)</b> que eliminará exclusivamente los datos corporativos, preservando fotografías y datos personales.")
        ]
    },
    {
        "filename": "PROC-TI-06_Protocolo_Respaldo_OneDrive_Migracion_Equipos.pdf",
        "code": "PROC-TI-06",
        "title": "Protocolo de Respaldo en OneDrive y Migración de Datos de Usuario",
        "category": "Almacenamiento y Backup",
        "version": "2.0",
        "date": "2026-03-10",
        "sections": [
            ("1. Almacenamiento Oficial en la Nube",
             "InnovaCorp asigna a cada colaborador una cuota de <b>1 Terabyte (1 TB)</b> en OneDrive for Business. Todas las computadoras de la compañía tienen activada la sincronización automática de carpetas conocidas (KFM) para 'Escritorio', 'Documentos' e 'Imágenes'."),
            ("2. Políticas de Retención y Recuperación de Archivos",
             "Los archivos eliminados por el usuario permanecen en la papelera de reciclaje durante <b>30 días</b>. Si el archivo fue purgado de la papelera, el administrador de TI puede recuperarlo de la papelera de segundo nivel hasta por <b>93 días adicionales</b>."),
            ("3. Restricciones de Medios Externos",
             "Queda terminantemente prohibido realizar respaldos de archivos corporativos en discos duros externos personales o memorias USB no cifradas. Los puertos USB de los portátiles cuentan con política de bloqueo DLP para transferencias masivas no autorizadas.")
        ]
    },
    {
        "filename": "PROC-TI-07_Gestion_Bajas_Revocacion_Accesos_Offboarding.pdf",
        "code": "PROC-TI-07",
        "title": "Procedimiento de Desvinculación de Personal y Revocación de Accesos TI",
        "category": "Seguridad e Identidad",
        "version": "3.3",
        "date": "2026-02-28",
        "sections": [
            ("1. Notificación Previa de Talento Humano",
             "El área de People & Culture / RRHH debe crear un ticket en ServiceNow bajo la categoría <b>'OFF-TALENTO'</b> con al menos <b>24 horas de anticipación</b> a la fecha y hora pactada para la salida del colaborador."),
            ("2. Ejecución Técnica de la Baja",
             "A las 18:00 horas del último día laboral (o de forma inmediata en despidos con causa):<br/>"
             "1. Deshabilitación de la cuenta en Microsoft Entra ID y Active Directory local.<br/>"
             "2. Cierre forzoso de todas las sesiones web activas (Revoke All Sessions en O365).<br/>"
             "3. Revocación de certificados VPN y desactivación de tarjetas de acceso físicas RFID."),
            ("3. Gestión del Buzón de Correo y Archivos",
             "El buzón de correo se convierte en 'Buzón Compartido' y se delega acceso de solo lectura al supervisor directo por un periodo máximo de <b>30 días calendario</b>. Cumplido este tiempo, el buzón y la cuenta OneDrive se archivan en frío.")
        ]
    },
    {
        "filename": "PROTO-TI-08_Atencion_Incidentes_Seguridad_Phishing.pdf",
        "code": "PROTO-TI-08",
        "title": "Protocolo de Atención ante Incidentes de Seguridad y Correos de Phishing",
        "category": "Ciberseguridad",
        "version": "2.5",
        "date": "2026-03-05",
        "sections": [
            ("1. Identificación y Reporte de Correos Sospechosos",
             "Si un colaborador recibe un mensaje con enlaces sospechosos, solicitud urgente de transferencias o solicitudes de cambio de clave no solicitadas, debe presionar el botón <b>'Reportar Phishing'</b> en Outlook o reenviar el correo como archivo adjunto a <u>phishing-alert@innovacorp.internal</u>."),
            ("2. Acciones Inmediatas si se Hizo Clic o se Descargó un Archivo",
             "Si el usuario ingresó sus credenciales o ejecutó un archivo adjunto malicioso:<br/>"
             "<b>Paso 1:</b> Desconectar de inmediato el cable de red Ethernet y apagar el interruptor de Wi-Fi de la laptop (aislamiento de red).<br/>"
             "<b>Paso 2:</b> <u>NO APAGAR NI REINICIAR LA COMPUTADORA</u>. El reinicio destruye evidencia crítica en la memoria RAM volátil.<br/>"
             "<b>Paso 3:</b> Llamar urgentemente a la <b>Línea Roja del SOC en la ext. 9111</b> desde un teléfono corporativo.")
        ]
    },
    {
        "filename": "GUIA-TI-09_Impresion_Segura_PaperCut_Tarjetas_RFID.pdf",
        "code": "GUIA-TI-09",
        "title": "Guía de Impresión Segura FollowMe con PaperCut y Carnet RFID",
        "category": "Servicios de Impresión",
        "version": "1.5",
        "date": "2026-01-30",
        "sections": [
            ("1. Colas de Impresión Universales",
             "No se instalan impresoras individuales en las laptops. Todos los documentos deben enviarse a las colas compartidas del servidor de impresión:<br/>"
             "• <code>\\\\printserver01.innovacorp.local\\FollowMe-Color</code> (impresión a color)<br/>"
             "• <code>\\\\printserver01.innovacorp.local\\FollowMe-BW</code> (impresión monocromática)"),
            ("2. Liberación de Trabajos en la Impresora",
             "El usuario puede acercarse a cualquier equipo multifuncional de la empresa y liberar sus documentos acercando su carnet corporativo RFID al lector contactless. Si no tiene el carnet físico, puede ingresar su PIN personal de 4 dígitos generado en el portal <u>https://print.innovacorp.local</u>."),
            ("3. Cancelación Automática por Timeout",
             "Los documentos enviados que no sean liberados en un lapso de <b>4 horas</b> se eliminarán automáticamente de la cola del servidor para garantizar confidencialidad y ahorro ecológico de papel.")
        ]
    },
    {
        "filename": "POL-TI-10_Horarios_Guardias_Escalamiento_Soporte_Critico.pdf",
        "code": "POL-TI-10",
        "title": "Política de Horarios de Mesa de Ayuda, Guardias y Escalamiento Crítico",
        "category": "Operaciones TI y Soporte",
        "version": "3.0",
        "date": "2026-03-12",
        "sections": [
            ("1. Horarios de Atención Ordinaria Nivel 1",
             "La Mesa de Ayuda de TI brinda atención de lunes a viernes en jornada continua de <b>07:00 a 19:00 horas (GMT-5)</b> a través del portal de autoservicio Jira o mediante la línea interna <b>ext. 4357</b>."),
            ("2. Soporte Crítico Fuera de Horario (On-Call 24/7)",
             "Las guardias fuera de horario y fines de semana atienden EXCLUSIVAMENTE incidentes de Severidad 1 (P1 / Sev-1), definidos como caída total del ERP SAP, core transaccional o corte general de VPN. Para activar la guardia, marcar a la línea internacional <b>+1-800-555-0199</b> e ingresar el PIN de emergencia <b>9911</b>."),
            ("3. Tiempos de Respuesta y Matriz de Escalamiento",
             "• <b>0 a 15 minutos:</b> Atención y triage inicial por el Ingeniero de Guardia Nivel 1.<br/>"
             "• <b>15 a 30 minutos:</b> Escalamiento automático al Especialista de Infraestructura Nivel 2 si no se ha restablecido el servicio.<br/>"
             "• <b>> 30 minutos:</b> Notificación al Gerente de Operaciones de TI y apertura de Sala de Guerra (War Room) virtual en Microsoft Teams.")
        ]
    }
]


def create_pdf(doc_info):
    pdf_path = os.path.join(OUTPUT_DIR, doc_info["filename"])
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    header_style = ParagraphStyle(
        'DocHeader',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f2b48')
    )
    
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#555555')
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1b5e20')
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#222222')
    )
    
    story = []

    # Encabezado corporativo
    story.append(Paragraph("INNOVACORP TECHNOLOGIES - DIRECCIÓN DE TECNOLOGÍA", meta_style))
    story.append(Paragraph(doc_info["title"], header_style))
    story.append(Spacer(1, 8))
    
    # Tabla de Metadatos
    meta_table_data = [
        [
            Paragraph(f"<b>Código:</b> {doc_info['code']}", meta_style),
            Paragraph(f"<b>Versión:</b> {doc_info['version']}", meta_style),
            Paragraph(f"<b>Fecha:</b> {doc_info['date']}", meta_style),
            Paragraph(f"<b>Categoría:</b> {doc_info['category']}", meta_style)
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[120, 90, 110, 200])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f4f8')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#c0d0e0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0f2b48'), spaceAfter=14))

    # Secciones
    for sec_title, sec_content in doc_info["sections"]:
        story.append(Paragraph(sec_title, section_title_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(sec_content, body_style))
        story.append(Spacer(1, 10))

    # Pie de documento
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#aaaaaa'), spaceAfter=8))
    story.append(Paragraph("Documento de Uso Interno Confidencial - Prohibida su reproducción sin autorización de TI InnovaCorp", meta_style))

    doc.build(story)
    print(f"Generado exitosamente: {doc_info['filename']}")


def main():
    print(f"Generando 10 documentos PDF corporativos de demostración en:\n{OUTPUT_DIR}\n")
    for doc in DOCUMENTS_DATA:
        create_pdf(doc)
    print("\n¡Todos los 10 PDFs fueron generados con éxito!")


if __name__ == "__main__":
    main()
