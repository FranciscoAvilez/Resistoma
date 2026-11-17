"""
Calculadora de Líquidos y Electrolitos Pediátricos (interfaz Tkinter).

Ejecutar:  python app.py
Generar .exe (Windows):  build_exe.bat
"""

import tkinter as tk
from tkinter import ttk

from calculos import Electrolito, Entrada, calcular, goteo

TITULO = "Calculadora de Soluciones Pediátricas"

AVISO = ("Apoyo al cálculo; verifique dosis, no sustituye el juicio clínico. "
         "Holliday-Segar · AAP 2018 · NICE NG29.")

DEFAULTS_ELEC = {
    "Na": (False, "mEq/kg/día", "3"),
    "K": (True, "mEq/L", "20"),
    "Ca": (False, "mg/kg/día", "100"),
    "Mg": (False, "mg/kg/día", "25"),
}
NOMBRES_ELEC = {"Na": "Sodio (NaCl 17.7%)", "K": "Potasio (KCl 14.9%)",
                "Ca": "Calcio (Gluc. Ca 10%)", "Mg": "Magnesio (MgSO4 10%)"}
MODOS_ELEC = {
    "Na": ["mEq/kg/día", "mEq/m²SC/día", "mEq/L"],
    "K": ["mEq/kg/día", "mEq/m²SC/día", "mEq/L"],
    "Ca": ["mg/kg/día", "mEq/kg/día", "mEq/m²SC/día", "mEq/L"],
    "Mg": ["mg/kg/día", "mEq/kg/día", "mEq/m²SC/día", "mEq/L"],
}


def _num(s: str):
    s = s.strip().replace(",", ".")
    return float(s) if s else None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TITULO)
        self.geometry("1100x740")
        self.minsize(900, 600)
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("H.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))

        self.v = {
            "peso": tk.StringVar(value=""),
            "talla": tk.StringVar(value=""),
            "metodo": tk.StringVar(value="Holliday-Segar"),
            "ml_m2": tk.StringVar(value="1500"),
            "limite_on": tk.BooleanVar(value=True),
            "limite": tk.StringVar(value="2400"),
            "pct": tk.DoubleVar(value=100),
            "solucion": tk.StringVar(value="Mixta"),
            "base": tk.StringVar(value="NaCl 0.9%"),
            "glucosa": tk.StringVar(value="5"),
            "descontar": tk.BooleanVar(value=True),
        }
        self.elec_vars = {}
        self._construir()
        for var in self.v.values():
            var.trace_add("write", lambda *_: self.recalcular())
        self.recalcular()

    # ------------------------------------------------------------------ UI
    def _construir(self):
        cont = ttk.Frame(self, padding=8)
        cont.pack(fill="both", expand=True)
        cont.columnconfigure(1, weight=1)
        cont.rowconfigure(0, weight=1)

        izq = ttk.Frame(cont)
        izq.grid(row=0, column=0, sticky="ns", padx=(0, 8))

        # 1. Paciente
        f = ttk.LabelFrame(izq, text="1. Paciente", padding=6)
        f.pack(fill="x", pady=3)
        ttk.Label(f, text="Peso (kg) *").grid(row=0, column=0, sticky="w")
        e = ttk.Entry(f, textvariable=self.v["peso"], width=10, font=("Segoe UI", 12))
        e.grid(row=0, column=1, sticky="w", padx=4)
        e.focus_set()
        ttk.Label(f, text="Talla (cm)").grid(row=1, column=0, sticky="w")
        ttk.Entry(f, textvariable=self.v["talla"], width=10).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(f, text="(opcional, para SC Mosteller)", foreground="gray").grid(row=1, column=2, sticky="w")

        # 2. Volumen
        f = ttk.LabelFrame(izq, text="2. Volumen de mantenimiento", padding=6)
        f.pack(fill="x", pady=3)
        ttk.Radiobutton(f, text="Holliday-Segar (100/50/20)", value="Holliday-Segar",
                        variable=self.v["metodo"]).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Radiobutton(f, text="Superficie corporal", value="SC",
                        variable=self.v["metodo"]).grid(row=1, column=0, sticky="w")
        ttk.Entry(f, textvariable=self.v["ml_m2"], width=7).grid(row=1, column=1, sticky="w")
        ttk.Label(f, text="mL/m²SC/día").grid(row=1, column=2, sticky="w")
        ttk.Checkbutton(f, text="Límite de adulto", variable=self.v["limite_on"]).grid(row=2, column=0, sticky="w")
        ttk.Entry(f, textvariable=self.v["limite"], width=7).grid(row=2, column=1, sticky="w")
        ttk.Label(f, text="mL/día máx.").grid(row=2, column=2, sticky="w")

        # 3. Restricción
        f = ttk.LabelFrame(izq, text="3. Restricción hídrica (% del mantenimiento)", padding=6)
        f.pack(fill="x", pady=3)
        self.lbl_pct = ttk.Label(f, text="100 %", style="H.TLabel", width=6)
        self.lbl_pct.grid(row=0, column=0)
        ttk.Scale(f, from_=30, to=150, variable=self.v["pct"], length=230,
                  command=lambda val: self.v["pct"].set(round(float(val)))).grid(row=0, column=1, columnspan=4)
        for i, p in enumerate((100, 80, 75, 66, 50)):
            ttk.Button(f, text=f"{p}%", width=5,
                       command=lambda p=p: self.v["pct"].set(p)).grid(row=1, column=i, padx=1, pady=2)

        # 4. Solución
        f = ttk.LabelFrame(izq, text="4. Tipo de solución", padding=6)
        f.pack(fill="x", pady=3)
        for i, (val, txt) in enumerate((("Mixta", "Mixta (Glucosa 5% + NaCl 0.9%)"),
                                         ("1:1", "1:1  (1 glucosada : 1 salina/Hartmann)"),
                                         ("2:1", "2:1  (2 glucosada : 1 salina/Hartmann)"))):
            ttk.Radiobutton(f, text=txt, value=val, variable=self.v["solucion"]).grid(
                row=i, column=0, columnspan=4, sticky="w")
        ttk.Label(f, text="Salina:").grid(row=3, column=0, sticky="w", pady=(4, 0))
        self.rb_base = [ttk.Radiobutton(f, text=t, value=t, variable=self.v["base"])
                        for t in ("NaCl 0.9%", "Hartmann")]
        for i, rb in enumerate(self.rb_base):
            rb.grid(row=3, column=1 + i, sticky="w", pady=(4, 0))
        ttk.Label(f, text="Glucosa:").grid(row=4, column=0, sticky="w")
        self.rb_glu = [ttk.Radiobutton(f, text=f"{g}%", value=str(g), variable=self.v["glucosa"])
                       for g in (5, 10, 50)]
        for i, rb in enumerate(self.rb_glu):
            rb.grid(row=4, column=1 + i, sticky="w")

        # 5. Electrolitos
        f = ttk.LabelFrame(izq, text="5. Electrolitos", padding=6)
        f.pack(fill="x", pady=3)
        for i, ion in enumerate(("Na", "K", "Ca", "Mg")):
            act, modo, val = DEFAULTS_ELEC[ion]
            va = tk.BooleanVar(value=act)
            vm = tk.StringVar(value=modo)
            vv = tk.StringVar(value=val)
            ttk.Checkbutton(f, text=NOMBRES_ELEC[ion], variable=va).grid(row=i, column=0, sticky="w")
            ttk.Entry(f, textvariable=vv, width=6).grid(row=i, column=1, padx=3)
            ttk.Combobox(f, textvariable=vm, values=MODOS_ELEC[ion], state="readonly",
                         width=13).grid(row=i, column=2)
            for var in (va, vm, vv):
                var.trace_add("write", lambda *_: self.recalcular())
            self.elec_vars[ion] = (va, vm, vv)
        ttk.Checkbutton(f, text="Descontar lo que ya aporta la solución base",
                        variable=self.v["descontar"]).grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))

        ttk.Label(izq, text=AVISO, foreground="#7a4b00", wraplength=380,
                  font=("Segoe UI", 8)).pack(fill="x", pady=(6, 0))

        # Resultados
        der = ttk.LabelFrame(cont, text="Resultado", padding=6)
        der.grid(row=0, column=1, sticky="nsew")
        der.rowconfigure(0, weight=1)
        der.columnconfigure(0, weight=1)
        self.txt = tk.Text(der, wrap="word", font=("Consolas", 10), relief="flat",
                           background="#fbfbfb", padx=8, pady=6)
        self.txt.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(der, command=self.txt.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.txt.configure(yscrollcommand=sb.set)
        self.txt.tag_configure("h", font=("Segoe UI", 11, "bold"), foreground="#0b4f8a", spacing1=6)
        self.txt.tag_configure("big", font=("Segoe UI", 14, "bold"))
        self.txt.tag_configure("warn", foreground="#b00020")
        self.txt.tag_configure("err", foreground="#b00020", font=("Segoe UI", 11, "bold"))
        self.txt.tag_configure("gris", foreground="gray")
        ttk.Button(der, text="Copiar indicación", command=self.copiar).grid(row=1, column=0, sticky="e", pady=(6, 0))

    # --------------------------------------------------------------- lógica
    def _entrada(self) -> Entrada:
        peso = _num(self.v["peso"].get())
        if peso is None:
            raise ValueError("Capture el peso en kg para comenzar.")
        elec = {}
        for ion, (va, vm, vv) in self.elec_vars.items():
            try:
                valor = _num(vv.get()) or 0.0
            except ValueError:
                raise ValueError(f"Valor inválido para {ion}")
            elec[ion] = Electrolito(va.get(), vm.get(), valor)
        return Entrada(
            peso_kg=peso,
            talla_cm=_num(self.v["talla"].get()),
            metodo=self.v["metodo"].get(),
            ml_m2=_num(self.v["ml_m2"].get()) or 1500,
            limite_adulto=self.v["limite_on"].get(),
            limite_ml=_num(self.v["limite"].get()) or 2400,
            porcentaje=float(self.v["pct"].get()),
            solucion=self.v["solucion"].get(),
            base=self.v["base"].get(),
            glucosa_pct=int(self.v["glucosa"].get()),
            descontar_base=self.v["descontar"].get(),
            electrolitos=elec,
        )

    def recalcular(self):
        if not hasattr(self, "txt"):
            return
        self.lbl_pct.configure(text=f"{self.v['pct'].get():.0f} %")
        estado = "disabled" if self.v["solucion"].get() == "Mixta" else "normal"
        for rb in self.rb_base + self.rb_glu:
            rb.configure(state=estado)

        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        try:
            ent = self._entrada()
            r = calcular(ent)
        except (ValueError, tk.TclError) as exc:
            self.txt.insert("end", str(exc) if str(exc) else "Revise los datos.", "err")
            self.txt.configure(state="disabled")
            self.indicacion = ""
            return
        self._mostrar(ent, r)
        self.txt.configure(state="disabled")

    def _mostrar(self, ent: Entrada, r):
        w = self.txt.insert
        w("end", "Volumen\n", "h")
        metodo = (f"Holliday-Segar" if ent.metodo != "SC" else f"SC × {ent.ml_m2:g} mL/m²")
        w("end", f"SC: {r.sc:.2f} m²  ({r.sc_formula})\n")
        w("end", f"Mantenimiento ({metodo}): {r.vol_calculado:.0f} mL/día\n")
        if r.limite_aplicado:
            w("end", f"Limitado a adulto: {r.vol_limitado:.0f} mL/día\n")
        w("end", f"Ajuste: {ent.porcentaje:.0f}%\n")
        w("end", f"TOTAL: {r.vol_total:.0f} mL/día   =   {r.ml_h:.1f} mL/h\n", "big")
        g = goteo(r.ml_h)
        w("end", f"{r.vol_total/3:.0f} mL por turno de 8 h  |  {g['micro']:.0f} microgotas/min"
                 f"  |  {g['macro']:.0f} gotas/min (macro)\n")
        w("end", f"{r.vol_total/ent.peso_kg:.0f} mL/kg/día   |   {r.vol_total/r.sc:.0f} mL/m²SC/día\n", "gris")

        w("end", "Preparación\n", "h")
        w("end", f"{'Componente':<42}{'24 h':>9}{'Turno 8 h':>12}\n", "gris")
        lineas = []
        for nombre, ml in r.componentes:
            w("end", f"{nombre:<42}{ml:>7.1f} mL{ml/3:>9.1f} mL\n")
            lineas.append(f"{nombre} {ml:.1f} mL")

        w("end", "Aporte de electrolitos\n", "h")
        w("end", f"{'Ion':<4}{'mEq/día':>9}{'mEq/kg':>9}{'mEq/m²':>9}{'mEq/L':>8}{'agregado':>11}\n", "gris")
        for ion, d in r.aportes.items():
            extra = f"   ({d['mg_kg']:.0f} mg/kg/día)" if "mg_kg" in d else ""
            w("end", f"{ion:<4}{d['total']:>9.1f}{d['por_kg']:>9.2f}{d['por_m2']:>9.1f}"
                     f"{d['por_l']:>8.0f}{d['agregado']:>8.1f} mEq{extra}\n")

        w("end", "Composición final\n", "h")
        w("end", f"Glucosa: {r.glucosa_g:.1f} g/día  ({r.glucosa_pct_final:.1f}%)  |  "
                 f"Carga de glucosa: {r.gkm:.2f} mg/kg/min\n")
        w("end", f"Na: {r.na_meq_l:.0f} mEq/L   |   Osmolaridad aprox.: {r.osm:.0f} mOsm/L\n")

        if r.advertencias:
            w("end", "Advertencias\n", "h")
            for a in r.advertencias:
                w("end", f"• {a}\n", "warn")

        sol = "Solución mixta" if ent.solucion == "Mixta" else f"Solución {ent.solucion}"
        self.indicacion = (
            f"{sol}: {r.vol_total:.0f} mL para 24 h ({ent.porcentaje:.0f}% de mantenimiento), "
            f"{r.ml_h:.1f} mL/h. Preparar: " + ", ".join(lineas) +
            f". Peso {ent.peso_kg:g} kg, SC {r.sc:.2f} m²."
        )

    def copiar(self):
        if getattr(self, "indicacion", ""):
            self.clipboard_clear()
            self.clipboard_append(self.indicacion)


if __name__ == "__main__":
    App().mainloop()
