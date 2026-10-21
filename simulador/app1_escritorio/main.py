"""App 1 - Generador de procesos (escritorio).

Obtiene procesos reales del SO, permite catalogarlos, los guarda en la BD
y levanta el servicio REST (XML) en http://localhost:5001/api/catalogos
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import db
import servicio
from procesos import obtener_procesos

PUERTO = 5001


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Generador de procesos")
        self.geometry("900x560")
        self.procesos = []

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=8, pady=8)
        tabs.add(self._tab_obtener(tabs), text="Obtener procesos")
        tabs.add(self._tab_catalogos(tabs), text="Catálogos guardados")
        tabs.bind("<<NotebookTabChanged>>", lambda e: self.cargar_catalogos())

        ttk.Label(self, text=f"Servicio REST activo: http://localhost:{PUERTO}/api/catalogos",
                  foreground="gray").pack(pady=(0, 6))

    # ---------- Pestaña 1 ----------
    def _tab_obtener(self, padre):
        f = ttk.Frame(padre, padding=8)
        form = ttk.Frame(f)
        form.pack(fill="x")

        self.v_numero = tk.StringVar(value=str(db.siguiente_numero()))
        self.v_nombre = tk.StringVar()
        self.v_cantidad = tk.StringVar(value="5")
        self.v_criterio = tk.StringVar(value="CPU")

        ttk.Label(form, text="N° catálogo").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.v_numero, width=8).grid(row=1, column=0, padx=(0, 8))
        ttk.Label(form, text="Nombre catálogo").grid(row=0, column=1, sticky="w")
        ttk.Entry(form, textvariable=self.v_nombre, width=30).grid(row=1, column=1, padx=(0, 8))
        ttk.Label(form, text="Cantidad").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(form, from_=1, to=50, textvariable=self.v_cantidad, width=6).grid(row=1, column=2, padx=(0, 8))
        ttk.Label(form, text="Criterio").grid(row=0, column=3, sticky="w")
        ttk.Combobox(form, textvariable=self.v_criterio, values=["CPU", "Memoria"],
                     state="readonly", width=10).grid(row=1, column=3, padx=(0, 8))
        ttk.Button(form, text="Obtener procesos", command=self.obtener).grid(row=1, column=4)

        cols = ("pid", "nombre", "usuario", "descripcion", "prioridad", "cpu", "memoria")
        self.tabla = ttk.Treeview(f, columns=cols, show="headings", height=14)
        for c, ancho in zip(cols, (60, 140, 140, 240, 110, 60, 70)):
            self.tabla.heading(c, text=c.capitalize())
            self.tabla.column(c, width=ancho)
        self.tabla.pack(fill="both", expand=True, pady=8)
        self.tabla.bind("<Double-1>", self.editar_descripcion)

        abajo = ttk.Frame(f)
        abajo.pack(fill="x")
        ttk.Label(abajo, text="Doble clic sobre un proceso para editar su descripción. "
                              "Prioridad: 1 = No expulsivo (SO), 0 = Expulsivo",
                  foreground="gray").pack(side="left")
        ttk.Button(abajo, text="Guardar catálogo", command=self.guardar).pack(side="right")
        return f

    def obtener(self):
        try:
            n = int(self.v_cantidad.get())
            assert n > 0
        except (ValueError, AssertionError):
            return messagebox.showwarning("Dato inválido", "La cantidad debe ser un número mayor que 0")
        criterio = "cpu" if self.v_criterio.get() == "CPU" else "memoria"
        self.procesos = obtener_procesos(n, criterio)
        self.pintar_tabla()

    def pintar_tabla(self):
        self.tabla.delete(*self.tabla.get_children())
        for i, p in enumerate(self.procesos):
            prioridad = "1 (No expulsivo)" if p["prioridad"] else "0 (Expulsivo)"
            self.tabla.insert("", "end", iid=str(i), values=(
                p["pid"], p["nombre"], p["usuario"], p["descripcion"],
                prioridad, p["cpu"], p["memoria"]))

    def editar_descripcion(self, _evento):
        sel = self.tabla.focus()
        if not sel:
            return
        p = self.procesos[int(sel)]
        nueva = simpledialog.askstring("Descripción", f"Descripción de {p['nombre']}:",
                                       initialvalue=p["descripcion"], parent=self)
        if nueva and nueva.strip():
            p["descripcion"] = nueva.strip()
            self.pintar_tabla()

    def guardar(self):
        if not self.procesos:
            return messagebox.showwarning("Sin procesos", "Primero obtén los procesos")
        nombre = self.v_nombre.get().strip()
        if not nombre:
            return messagebox.showwarning("Falta el nombre", "Escribe el nombre del catálogo")
        try:
            numero = int(self.v_numero.get())
        except ValueError:
            return messagebox.showwarning("Dato inválido", "El número de catálogo debe ser numérico")
        if db.existe_catalogo(numero):
            return messagebox.showwarning("Repetido", f"Ya existe el catálogo {numero}")

        criterio = "cpu" if self.v_criterio.get() == "CPU" else "memoria"
        db.guardar_catalogo(numero, nombre, criterio, self.procesos)
        messagebox.showinfo("Guardado", f"Catálogo {numero} guardado con {len(self.procesos)} procesos")
        self.procesos = []
        self.pintar_tabla()
        self.v_nombre.set("")
        self.v_numero.set(str(db.siguiente_numero()))

    # ---------- Pestaña 2 ----------
    def _tab_catalogos(self, padre):
        f = ttk.Frame(padre, padding=8)
        self.t_cat = ttk.Treeview(f, columns=("numero", "nombre", "criterio", "total", "fecha"),
                                  show="headings", height=6)
        for c in ("numero", "nombre", "criterio", "total", "fecha"):
            self.t_cat.heading(c, text=c.capitalize())
        self.t_cat.pack(fill="x")
        self.t_cat.bind("<<TreeviewSelect>>", self.ver_catalogo)

        ttk.Label(f, text="Procesos del catálogo seleccionado").pack(anchor="w", pady=(10, 2))
        cols = ("pid", "nombre", "usuario", "descripcion", "prioridad")
        self.t_procs = ttk.Treeview(f, columns=cols, show="headings")
        for c in cols:
            self.t_procs.heading(c, text=c.capitalize())
        self.t_procs.pack(fill="both", expand=True)
        return f

    def cargar_catalogos(self):
        self.t_cat.delete(*self.t_cat.get_children())
        for c in db.listar_catalogos():
            self.t_cat.insert("", "end", iid=str(c["numero"]), values=(
                c["numero"], c["nombre"], c["criterio"], c["total"], c["fecha"]))

    def ver_catalogo(self, _evento):
        sel = self.t_cat.focus()
        self.t_procs.delete(*self.t_procs.get_children())
        if not sel:
            return
        for p in db.obtener_catalogo(int(sel))["procesos"]:
            self.t_procs.insert("", "end", values=(
                p["pid"], p["nombre"], p["usuario"], p["descripcion"], p["prioridad"]))


if __name__ == "__main__":
    db.crear_tablas()
    threading.Thread(target=servicio.iniciar, args=(PUERTO,), daemon=True).start()
    App().mainloop()
