# Directorio de Documentos Corporativos del Cliente

Coloca en este directorio tus propios archivos PDF para que el agente de soporte los indexe y responda sobre ellos.

### Instrucciones de Uso:
1. Copia o sube tus archivos `.pdf` aquí (por ejemplo: manuales internos, políticas corporativas, guías de usuario, preguntas frecuentes).
2. Ejecuta el script de ingesta:
   ```bash
   python3 scripts/ingest_documents.py
   ```
3. El script extraerá el texto, generará los embeddings de 768 dimensiones en CPU y almacenará los vectores directamente en la tabla `KNOWLEDGE_BASE` de tu Oracle Database 26ai.
4. El agente comenzará a responder automáticamente utilizando la información de tus documentos.
