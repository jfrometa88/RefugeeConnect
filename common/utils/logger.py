import logging
from pathlib import Path

def setup_logger(name:str) -> logging.Logger:
    """Configurar el sistema de logging"""
    
    # 1. Definir la ruta usando Path (independiente del SO)
    log_dir = Path("common") / "data" / "logs"
    
    # 2. Crear el directorio y sus padres si no existen (exist_ok evita errores)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. Definir el archivo final
    log_filename = log_dir / "logs.log"
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()  # También muestra en consola
        ]
    )    
    return logging.getLogger(name)

