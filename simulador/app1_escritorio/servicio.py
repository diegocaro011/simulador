"""Servicio web REST que entrega los catálogos en XML."""
import xml.etree.ElementTree as ET
from flask import Flask, Response

import db

app = Flask(__name__)


def responder_xml(raiz, status=200):
    xml = ET.tostring(raiz, encoding="utf-8", xml_declaration=True)
    resp = Response(xml, status=status, mimetype="application/xml")
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.get("/api/catalogos")
def catalogos():
    raiz = ET.Element("catalogos")
    for c in db.listar_catalogos():
        e = ET.SubElement(raiz, "catalogo")
        for campo in ("numero", "nombre", "criterio", "fecha", "total"):
            ET.SubElement(e, campo).text = str(c[campo])
    return responder_xml(raiz)


@app.get("/api/catalogos/<int:numero>")
def catalogo(numero):
    c = db.obtener_catalogo(numero)
    if not c:
        error = ET.Element("error")
        error.text = f"No existe el catálogo {numero}"
        return responder_xml(error, 404)

    raiz = ET.Element("catalogo")
    for campo in ("numero", "nombre", "criterio", "fecha"):
        ET.SubElement(raiz, campo).text = str(c[campo])
    procesos = ET.SubElement(raiz, "procesos")
    for p in c["procesos"]:
        e = ET.SubElement(procesos, "proceso")
        ET.SubElement(e, "pid").text = str(p["pid"])
        ET.SubElement(e, "nombre").text = p["nombre"]
        ET.SubElement(e, "usuario").text = p["usuario"] or ""
        ET.SubElement(e, "descripcion").text = p["descripcion"]
        ET.SubElement(e, "prioridad").text = str(p["prioridad"])
        # Dato para el algoritmo de planificación: ráfaga = TH * caracteres
        ET.SubElement(e, "caracteres").text = str(len(p["descripcion"]))
    return responder_xml(raiz)


def iniciar(puerto=5001):
    db.crear_tablas()
    app.run(host="0.0.0.0", port=puerto, debug=False, use_reloader=False)


if __name__ == "__main__":
    iniciar()
