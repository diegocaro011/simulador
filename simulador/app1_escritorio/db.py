"""Base de datos SQLite para los catálogos de procesos."""
import os
import sqlite3

RUTA_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalogos.db")


def conectar():
    con = sqlite3.connect(RUTA_DB)
    con.row_factory = sqlite3.Row
    return con


def crear_tablas():
    with conectar() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS catalogo (
            numero   INTEGER PRIMARY KEY,
            nombre   TEXT NOT NULL,
            criterio TEXT NOT NULL,
            fecha    TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS proceso (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            catalogo    INTEGER NOT NULL REFERENCES catalogo(numero),
            pid         INTEGER NOT NULL,
            nombre      TEXT NOT NULL,
            usuario     TEXT,
            descripcion TEXT NOT NULL,
            prioridad   INTEGER NOT NULL
        );
        """)


def siguiente_numero():
    with conectar() as con:
        fila = con.execute("SELECT COALESCE(MAX(numero), 0) + 1 FROM catalogo").fetchone()
        return fila[0]


def existe_catalogo(numero):
    with conectar() as con:
        return con.execute("SELECT 1 FROM catalogo WHERE numero=?", (numero,)).fetchone() is not None


def guardar_catalogo(numero, nombre, criterio, procesos):
    with conectar() as con:
        con.execute("INSERT INTO catalogo(numero, nombre, criterio) VALUES (?,?,?)",
                    (numero, nombre, criterio))
        con.executemany(
            "INSERT INTO proceso(catalogo, pid, nombre, usuario, descripcion, prioridad) "
            "VALUES (?,?,?,?,?,?)",
            [(numero, p["pid"], p["nombre"], p["usuario"], p["descripcion"], p["prioridad"])
             for p in procesos])


def listar_catalogos():
    with conectar() as con:
        return [dict(f) for f in con.execute(
            "SELECT c.*, COUNT(p.id) AS total FROM catalogo c "
            "LEFT JOIN proceso p ON p.catalogo = c.numero "
            "GROUP BY c.numero ORDER BY c.numero")]


def obtener_catalogo(numero):
    with conectar() as con:
        cat = con.execute("SELECT * FROM catalogo WHERE numero=?", (numero,)).fetchone()
        if not cat:
            return None
        procs = con.execute("SELECT * FROM proceso WHERE catalogo=? ORDER BY id", (numero,))
        return {**dict(cat), "procesos": [dict(p) for p in procs]}
