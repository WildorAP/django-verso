import os
from dotenv import load_dotenv

print("=== VERIFICACIÓN DE ARCHIVO .env ===")
print()

# Cargar .env con override para forzar la actualización
load_dotenv(override=True)

# Verificar si el archivo .env existe
env_file = '.env'
if os.path.exists(env_file):
    print("✅ Archivo .env encontrado")
    
    # Leer directamente el archivo
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Buscar líneas relevantes
    lines = content.split('\n')
    aws_lines = [line for line in lines if line.startswith('AWS_')]
    
    print("📄 Contenido AWS en .env:")
    for line in aws_lines:
        if 'ACCESS_KEY_ID' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                key = parts[0]
                value = parts[1]
                print(f"  {key}={value[:10]}..." if value else f"  {key}=VACÍO")
        else:
            print(f"  {line}")
    
    print()
    
    # Verificar variables de entorno cargadas
    print("🔍 Variables cargadas en memoria:")
    print(f"  AWS_ACCESS_KEY_ID: {os.getenv('AWS_ACCESS_KEY_ID', 'NO CARGADO')[:10]}..." if os.getenv('AWS_ACCESS_KEY_ID') else "  AWS_ACCESS_KEY_ID: NO CARGADO")
    print(f"  AWS_SECRET_ACCESS_KEY: {'CARGADO' if os.getenv('AWS_SECRET_ACCESS_KEY') else 'NO CARGADO'}")
    print(f"  AWS_STORAGE_BUCKET_NAME: {os.getenv('AWS_STORAGE_BUCKET_NAME', 'NO CARGADO')}")
    print(f"  AWS_S3_REGION_NAME: {os.getenv('AWS_S3_REGION_NAME', 'NO CARGADO')}")
    
else:
    print("❌ Archivo .env NO encontrado")
    print("Debes crear un archivo .env en el directorio raíz del proyecto") 