import base64

with open("semilla_firmada.p7s", "rb") as f:
    print(base64.b64encode(f.read()).decode("utf-8"))
