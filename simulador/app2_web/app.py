"""App 2 - Simulador web de planificación Round Robin.

Consume el servicio REST (XML) de la App 1 para obtener los procesos.
Abrir en el navegador: http://localhost:5002
"""
import urllib.request
import xml.etree.ElementTree as ET

from flask import Flask, jsonify, render_template, request

from simulador import Proceso, Simulador

URL_APP1 = "http://127.0.0.1:5001/api"   # servicio de la App 1
PUERTO = 5002

app = Flask(__name__)
sim = None   # simulación actual


def leer_xml(ruta):
    with urllib.request.urlopen(f"{URL_APP1}{ruta}", timeout=5) as r:
        return ET.fromstring(r.read())


@app.get("/")
def inicio():
    return render_template("index.html")


@app.get("/api/catalogos")
def catalogos():
    try:
        raiz = leer_xml("/catalogos")
    except Exception as e:
        return jsonify(error=f"No se pudo conectar con la App 1 en {URL_APP1} ({e})"), 503
    return jsonify([{
        "numero": int(c.findtext("numero")),
        "nombre": c.findtext("nombre"),
        "total": int(c.findtext("total")),
    } for c in raiz.findall("catalogo")])


@app.post("/api/iniciar")
def iniciar():
    global sim
    datos = request.get_json()
    try:
        numero = int(datos["catalogo"])
        th = int(datos["th"])
        quantum = int(datos["quantum"])
        assert th > 0 and quantum > 0
    except (KeyError, ValueError, AssertionError):
        return jsonify(error="TH y Quantum deben ser números mayores que 0"), 400

    try:
        raiz = leer_xml(f"/catalogos/{numero}")
    except Exception as e:
        return jsonify(error=f"No se pudo obtener el catálogo de la App 1 ({e})"), 503

    procesos = [Proceso(
        pid=int(p.findtext("pid")),
        nombre=p.findtext("nombre"),
        descripcion=p.findtext("descripcion") or "",
        prioridad=int(p.findtext("prioridad")),
    ) for p in raiz.iter("proceso") if p.findtext("descripcion")]

    if sim:
        sim.detener()
    sim = Simulador(procesos, th, quantum)
    sim.iniciar()
    return jsonify(ok=True)


@app.post("/api/pausar")
def pausar():
    if sim:
        sim.pausar()
    return jsonify(ok=True)


@app.post("/api/reanudar")
def reanudar():
    if sim:
        sim.reanudar()
    return jsonify(ok=True)


@app.get("/api/estado")
def estado():
    if not sim:
        return jsonify(estado="sin_iniciar")
    return jsonify(sim.a_dict())


if __name__ == "__main__":
    app.run(port=PUERTO, debug=False, threaded=True)
