import requests

resp = requests.get("https://httpbin.org/get")
print("Código de respuesta:", resp.status_code)
print("Contenido:", resp.text)
