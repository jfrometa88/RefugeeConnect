import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))

project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.utils import tools


def test_get_services_by_category():
    """Prueba que la búsqueda de servicios devuelva los campos correctos"""
    results = tools.get_services_by_category('Comida', 'Valencia')
    
    print(results)  # Para depuración, muestra los resultados obtenidos
    assert len(results) > 0 

def test_get_branch_coordinates():
    """Prueba que la geolocalización devuelva latitud y longitud"""
    coords = tools.get_branch_coordinates('CEAR', 'Valencia')
    
    assert coords['lat'] == 39.467521
    assert coords['lon'] == -0.395812
    assert coords['name'] == 'CEAR'

def test_service_not_found():
    """Prueba el comportamiento cuando no hay resultados"""
    results = tools.get_services_by_category('Comida', 'Madrid')
    assert len(results) == 0