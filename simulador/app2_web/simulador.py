"""Simulador Round Robin con modelo de estados (Listo -> Ejecución -> Terminado).

- Cada proceso tiene su propio hilo (Thread).
- La actividad de un proceso es escribir su descripción, carácter por carácter,
  en un archivo con su nombre. Cada carácter tarda TH milisegundos.
- Ráfaga (R) = TH * cantidad de caracteres de la descripción.
- Expulsivo (prioridad 0): usa la CPU un quantum (N caracteres) y vuelve a Listo.
- No expulsivo (prioridad 1): usa la CPU hasta terminar toda su actividad.
"""
import os
import re
import threading
import time
from collections import deque

CARPETA_SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salida")


class Proceso:
    def __init__(self, pid, nombre, descripcion, prioridad):
        self.pid = pid
        self.nombre = nombre
        self.descripcion = descripcion
        self.prioridad = prioridad          # 0 = Expulsivo, 1 = No expulsivo
        self.tl = 0                         # tiempo de llegada
        self.rafaga = 0                     # ms
        self.indice = 0                     # caracteres ya escritos
        self.ejecuciones = 0                # veces que usó la CPU
        self.tf = None                      # tiempo de finalización
        self.estado = "Listo"
        self.turno = threading.Event()      # el planificador le da la CPU

    @property
    def tr(self):                           # TurnAround = TF - TL
        return None if self.tf is None else self.tf - self.tl

    def archivo(self):
        limpio = re.sub(r'[\\/:*?"<>|]', "_", self.nombre)
        return os.path.join(CARPETA_SALIDA, f"{limpio}_{self.pid}.txt")

    def a_dict(self, quantum):
        return {
            "pid": self.pid, "nombre": self.nombre, "descripcion": self.descripcion,
            "prioridad": self.prioridad, "estado": self.estado,
            "tl": self.tl, "rafaga": self.rafaga, "quantum": quantum,
            "ejecuciones": self.ejecuciones, "escritos": self.indice,
            "total": len(self.descripcion), "tf": self.tf, "tr": self.tr,
        }


class Simulador:
    def __init__(self, procesos, th, quantum):
        self.th = th                        # ms por carácter
        self.quantum = quantum              # caracteres por turno (expulsivos)
        self.reloj = 0                      # tiempo simulado en ms
        self.lock = threading.Lock()
        self.corriendo = threading.Event()  # set = corre, clear = pausado
        self.liberada = threading.Event()   # la CPU quedó libre
        self.detenido = False

        # Estructuras dinámicas por estado
        self.listo = deque()
        self.ejecucion = None
        self.terminado = []
        self.todos = []

        os.makedirs(CARPETA_SALIDA, exist_ok=True)
        for p in procesos:
            # Tiempo de llegada: 0 si LISTO está vacío, si no el del último + 1
            p.tl = 0 if not self.listo else self.listo[-1].tl + 1
            p.rafaga = th * len(p.descripcion)
            open(p.archivo(), "w", encoding="utf-8").close()
            self.listo.append(p)
            self.todos.append(p)

    # ---------- Control ----------
    def iniciar(self):
        self.corriendo.set()
        for p in self.todos:
            threading.Thread(target=self._hilo_proceso, args=(p,), daemon=True).start()
        threading.Thread(target=self._planificador, daemon=True).start()

    def pausar(self):
        self.corriendo.clear()

    def reanudar(self):
        self.corriendo.set()

    def detener(self):
        self.detenido = True
        self.corriendo.set()
        self.liberada.set()
        for p in self.todos:
            p.turno.set()

    @property
    def estado_general(self):
        if len(self.terminado) == len(self.todos):
            return "finalizada"
        return "corriendo" if self.corriendo.is_set() else "pausada"

    # ---------- Planificador Round Robin ----------
    def _planificador(self):
        while not self.detenido and len(self.terminado) < len(self.todos):
            self.corriendo.wait()
            with self.lock:
                # Listo -> Ejecución, solo si no hay proceso usando la CPU
                if self.ejecucion is not None or not self.listo:
                    continue
                p = self.listo.popleft()
                p.estado = "Ejecución"
                self.ejecucion = p
                self.liberada.clear()
            p.turno.set()                    # le da la CPU al hilo del proceso
            self.liberada.wait()             # espera a que la libere

    # ---------- Hilo de cada proceso ----------
    def _hilo_proceso(self, p):
        while True:
            p.turno.wait()
            p.turno.clear()
            if self.detenido:
                return
            p.ejecuciones += 1
            usados = 0
            with open(p.archivo(), "a", encoding="utf-8") as f:
                while p.indice < len(p.descripcion):
                    self.corriendo.wait()    # si está pausado, el hilo espera
                    if self.detenido:
                        return
                    f.write(p.descripcion[p.indice])
                    f.flush()
                    time.sleep(self.th / 1000)
                    with self.lock:
                        self.reloj += self.th
                        p.indice += 1
                    usados += 1
                    # Liberación b: el proceso expulsivo suelta la CPU al agotar su quantum
                    if p.prioridad == 0 and usados >= self.quantum:
                        break

            with self.lock:
                if p.indice >= len(p.descripcion):
                    # Liberación a: terminó su actividad -> Ejecución a Terminado
                    p.estado = "Terminado"
                    p.tf = self.reloj
                    self.terminado.append(p)
                else:
                    # Ejecución a Listo (solo expulsivos)
                    p.estado = "Listo"
                    self.listo.append(p)
                self.ejecucion = None
            self.liberada.set()
            if p.estado == "Terminado":
                return

    # ---------- Estado para la interfaz ----------
    def a_dict(self):
        with self.lock:
            q = self.quantum
            return {
                "estado": self.estado_general,
                "reloj": self.reloj, "th": self.th, "quantum": q,
                "listo": [p.a_dict(q) for p in self.listo],
                "ejecucion": [self.ejecucion.a_dict(q)] if self.ejecucion else [],
                "terminado": [p.a_dict(q) for p in self.terminado],
                "todos": [p.a_dict(q) for p in self.todos],
            }
