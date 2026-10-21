"""Lectura de procesos reales del sistema operativo con psutil."""
import time
import psutil

# Usuarios que se consideran "del sistema operativo" -> procesos NO expulsivos
USUARIOS_SO = {
    "system", "root", "local service", "network service",
    "servicio local", "servicio de red", "daemon",
}


def es_del_sistema(usuario):
    """True si el proceso fue generado por el SO (o no se pudo saber el usuario)."""
    if not usuario:
        return True
    u = usuario.lower()
    if u.startswith("nt authority"):
        return True
    return u.split("\\")[-1] in USUARIOS_SO


def obtener_procesos(cantidad, criterio="cpu"):
    """Devuelve los `cantidad` procesos con mayor uso de CPU o memoria.

    Prioridad: 1 = No expulsivo (proceso del SO), 0 = Expulsivo (proceso de usuario).
    """
    procs = list(psutil.process_iter(["pid", "name", "username", "memory_percent"]))

    # psutil necesita dos mediciones para calcular el % de CPU
    for p in procs:
        try:
            p.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(0.5)

    datos = []
    for p in procs:
        try:
            cpu = p.cpu_percent(None)
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            cpu = 0.0
        info = p.info
        if info["pid"] == 0 or not info["name"]:
            continue
        usuario = info["username"] or "SYSTEM"
        nombre = info["name"]
        datos.append({
            "pid": info["pid"],
            "nombre": nombre,
            "usuario": usuario,
            # Descripción por defecto; el usuario la puede editar en la app
            "descripcion": f"{nombre.rsplit('.', 1)[0]} de {usuario.split(chr(92))[-1]}",
            "prioridad": 1 if es_del_sistema(info["username"]) else 0,
            "cpu": round(cpu, 1),
            "memoria": round(info["memory_percent"] or 0, 2),
        })

    clave = "cpu" if criterio == "cpu" else "memoria"
    datos.sort(key=lambda d: d[clave], reverse=True)
    return datos[:cantidad]
