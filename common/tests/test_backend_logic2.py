import requests
import time

BASE_URL = "http://localhost:8000"

def test_hot_swap_flow():
# 2. Cambiar a modo LOCAL (Ollama)
    print("\n--- Cambiando a modo Local (Gemma 4 vía Ollama) ---")
    config_res = requests.post(f"{BASE_URL}/config/toggle", json={
    "use_local_agent": True,
    "use_local": True,
    "model_name_cloud": "gemma2:2b",
    "model_name_local": "gemma2:2b"
    })
    print(f"Resultado cambio: {config_res.status_code}")

    # 3. Segunda pregunta: ¿Mantiene el contexto?
    print("\n--- Probando pregunta de seguimiento en modo Local ---")
    q2 = requests.post(f"{BASE_URL}/query", json={
        "user_id": "test_user_1",
        "query": "¿Cuál es la dirección de la primera que mencionaste?"
    })
    # Si responde correctamente, la persistencia de InMemorySessionService funciona
    print(f"Respuesta Local (con contexto): {q2.json()['response'][:100]}...")

if __name__ == "__main__":
    test_hot_swap_flow()