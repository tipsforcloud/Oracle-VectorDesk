# Carpeta de Documentos de Demostración (PDFs)

Este directorio almacena los 10 documentos PDF corporativos utilizados para la ingesta y vectorización en **Oracle Database 26ai**.

Para generarlos automáticamente con formato profesional:
```bash
python3 generate_sample_pdfs.py
```

Esto creará los siguientes 10 archivos PDF:
1. `POL-TI-01_Acceso_Red_Wifi_Visitantes.pdf`
2. `PROC-TI-02_Solicitud_Renovacion_Equipos_Hardware.pdf`
3. `GUIA-TI-03_Configuracion_MFA_Microsoft_Authenticator.pdf`
4. `PROC-TI-04_Solicitud_Accesos_Roles_SAP_ERP.pdf`
5. `POL-TI-05_Politica_Uso_Dispositivos_Moviles_BYOD.pdf`
6. `PROC-TI-06_Protocolo_Respaldo_OneDrive_Migracion_Equipos.pdf`
7. `PROC-TI-07_Gestion_Bajas_Revocacion_Accesos_Offboarding.pdf`
8. `PROTO-TI-08_Atencion_Incidentes_Seguridad_Phishing.pdf`
9. `GUIA-TI-09_Impresion_Segura_PaperCut_Tarjetas_RFID.pdf`
10. `POL-TI-10_Horarios_Guardias_Escalamiento_Soporte_Critico.pdf`

Posteriormente, ejecuta `python3 ingest_pdfs.py` para vectorizarlos e indexarlos en la base de datos.
