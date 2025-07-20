from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import json, os
from datetime import datetime, timedelta
from collections import defaultdict

load_dotenv()
app = Flask(__name__)

ARQUIVO = "registos.json"
API_KEY = os.getenv("API_KEY", "chave_padrao")

# Garante que o arquivo exista
if not os.path.exists(ARQUIVO):
    with open(ARQUIVO, "w") as f:
        json.dump([], f)

@app.route("/registrar_servico", methods=["POST"])
def registrar_servico():
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {API_KEY}":
        return jsonify({"erro": "Não autorizado"}), 403

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"erro": "Formato inválido"}), 400

    with open(ARQUIVO, "r") as f:
        try:
            registos = json.load(f)
            if not isinstance(registos, list):
                raise ValueError
        except Exception:
            registos = []

    registos.append(data)

    with open(ARQUIVO, "w") as f:
        json.dump(registos, f, indent=4)

    return jsonify({"status": "sucesso"}), 200

@app.route("/ranking/semana")
def ranking_semana():
    with open(ARQUIVO, "r") as f:
        registos = json.load(f)

    hoje = datetime.now()
    segunda = hoje - timedelta(days=hoje.weekday())
    total_por_usuario = defaultdict(timedelta)

    for item in registos:
        try:
            entrada = datetime.strptime(item["entrada"], "%Y-%m-%d %H:%M:%S")
            saida = datetime.strptime(item["saida"], "%Y-%m-%d %H:%M:%S")
            if entrada >= segunda:
                duracao = saida - entrada
                total_por_usuario[item["usuario"]] += duracao
        except Exception:
            continue

    ranking_ordenado = sorted(total_por_usuario.items(), key=lambda x: x[1], reverse=True)

    return render_template("ranking.html", ranking=ranking_ordenado, current_year=datetime.now().year)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
