"""
Motor de cálculo de líquidos y electrolitos de mantenimiento en pediatría.

Sin dependencias de interfaz: se puede importar y probar por separado.

Referencias principales
-----------------------
* Holliday MA, Segar WE. Pediatrics 1957;19:823-832 (regla 100/50/20).
* Feld LG, et al. AAP Clinical Practice Guideline: Maintenance Intravenous
  Fluids in Children. Pediatrics 2018;142(6):e20183083
  (líquidos isotónicos con KCl y dextrosa, 28 días a 18 años).
* NICE NG29 (2015, actualizada 2020): Holliday-Segar; restringir a 50-80 %
  del mantenimiento si hay riesgo de secreción no osmótica de ADH;
  límite habitual en adultos ~2000 mL/día (mujeres) y 2500 mL/día (hombres).

ESTA HERRAMIENTA ES UN APOYO AL CÁLCULO. No sustituye el juicio clínico.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Composición de soluciones (por litro). Valores habituales en México.
# ---------------------------------------------------------------------------
# glucosa en g/L, electrolitos en mEq/L, osm en mOsm/L
SOLUCIONES_BASE = {
    "NaCl 0.9%": {"glucosa": 0.0, "Na": 154.0, "K": 0.0, "Cl": 154.0, "Ca": 0.0, "osm": 308.0},
    "Hartmann": {"glucosa": 0.0, "Na": 130.0, "K": 4.0, "Cl": 109.0, "Ca": 3.0, "osm": 273.0},
}

GLUCOSADAS = {
    5: {"glucosa": 50.0, "osm": 252.0},
    10: {"glucosa": 100.0, "osm": 505.0},
    50: {"glucosa": 500.0, "osm": 2525.0},
}

# Solución mixta = glucosa 5 % en cloruro de sodio 0.9 %
MIXTA = {"glucosa": 50.0, "Na": 154.0, "K": 0.0, "Cl": 154.0, "Ca": 0.0, "osm": 560.0}

# Concentrados para agregar (por mL)
CONCENTRADOS = {
    "Na": {"nombre": "NaCl 17.7%", "meq_ml": 3.0, "osm_ml": 6.0},
    "K": {"nombre": "KCl 14.9%", "meq_ml": 2.0, "osm_ml": 4.0},
    # Gluconato de calcio 10 %: 100 mg/mL = 0.465 mEq/mL de Ca
    "Ca": {"nombre": "Gluconato de calcio 10%", "meq_ml": 0.465, "osm_ml": 0.68, "mg_ml": 100.0},
    # Sulfato de magnesio 10 %: 100 mg/mL = 0.81 mEq/mL de Mg
    "Mg": {"nombre": "Sulfato de magnesio 10%", "meq_ml": 0.81, "osm_ml": 0.81, "mg_ml": 100.0},
}

MODOS = ("mEq/kg/día", "mEq/m²SC/día", "mEq/L", "mg/kg/día")

# Rangos de referencia de mantenimiento (orientativos)
RANGOS = {
    "Na": {"mEq/kg/día": (2, 4), "mEq/m²SC/día": (30, 50), "mEq/L": (77, 154)},
    "K": {"mEq/kg/día": (1, 3), "mEq/m²SC/día": (20, 40), "mEq/L": (20, 40)},
    "Ca": {"mg/kg/día": (100, 200)},
    "Mg": {"mg/kg/día": (25, 50)},
}


# ---------------------------------------------------------------------------
# Volumen
# ---------------------------------------------------------------------------
def holliday_segar(peso_kg: float) -> float:
    """mL/día según Holliday-Segar (100/50/20)."""
    if peso_kg <= 0:
        raise ValueError("El peso debe ser mayor que 0")
    if peso_kg <= 10:
        return 100.0 * peso_kg
    if peso_kg <= 20:
        return 1000.0 + 50.0 * (peso_kg - 10)
    return 1500.0 + 20.0 * (peso_kg - 20)


def superficie_corporal(peso_kg: float, talla_cm: float | None = None) -> tuple[float, str]:
    """SC en m². Mosteller si hay talla; si no, (4P+7)/(P+90)."""
    if talla_cm and talla_cm > 0:
        return math.sqrt(peso_kg * talla_cm / 3600.0), "Mosteller"
    return (4 * peso_kg + 7) / (peso_kg + 90), "(4P+7)/(P+90)"


# ---------------------------------------------------------------------------
# Entradas y resultados
# ---------------------------------------------------------------------------
@dataclass
class Electrolito:
    activo: bool = False
    modo: str = "mEq/kg/día"
    valor: float = 0.0


@dataclass
class Entrada:
    peso_kg: float
    talla_cm: float | None = None
    metodo: str = "Holliday-Segar"          # o "SC"
    ml_m2: float = 1500.0                    # si metodo == "SC"
    limite_adulto: bool = True
    limite_ml: float = 2400.0
    porcentaje: float = 100.0                # % del mantenimiento (restricción)
    solucion: str = "Mixta"                  # "Mixta", "1:1", "2:1"
    base: str = "NaCl 0.9%"                  # o "Hartmann" (para 1:1 y 2:1)
    glucosa_pct: int = 5                     # 5, 10, 50
    descontar_base: bool = True
    electrolitos: dict[str, Electrolito] = field(default_factory=dict)


@dataclass
class Resultado:
    sc: float = 0.0
    sc_formula: str = ""
    vol_calculado: float = 0.0
    vol_limitado: float = 0.0
    limite_aplicado: bool = False
    vol_total: float = 0.0
    ml_h: float = 0.0
    componentes: list[tuple[str, float]] = field(default_factory=list)  # (nombre, mL/día)
    aportes: dict[str, dict] = field(default_factory=dict)
    glucosa_g: float = 0.0
    glucosa_pct_final: float = 0.0
    gkm: float = 0.0
    osm: float = 0.0
    na_meq_l: float = 0.0
    advertencias: list[str] = field(default_factory=list)


def _meq_meta(e: Electrolito, ion: str, peso: float, sc: float, vol_ml: float) -> float:
    if e.modo == "mEq/kg/día":
        return e.valor * peso
    if e.modo == "mEq/m²SC/día":
        return e.valor * sc
    if e.modo == "mEq/L":
        return e.valor * vol_ml / 1000.0
    if e.modo == "mg/kg/día":
        c = CONCENTRADOS[ion]
        if "mg_ml" not in c:
            raise ValueError(f"mg/kg/día no aplica para {ion}")
        ml = e.valor * peso / c["mg_ml"]
        return ml * c["meq_ml"]
    raise ValueError(f"Modo desconocido: {e.modo}")


def _fracciones(ent: Entrada) -> list[tuple[str, dict, float]]:
    """Lista (nombre, composición, fracción del volumen base)."""
    if ent.solucion == "Mixta":
        return [("Solución mixta (Glucosa 5% + NaCl 0.9%)", MIXTA, 1.0)]
    base = SOLUCIONES_BASE[ent.base]
    glu = GLUCOSADAS[ent.glucosa_pct]
    glu_comp = {"glucosa": glu["glucosa"], "Na": 0, "K": 0, "Cl": 0, "Ca": 0, "osm": glu["osm"]}
    nombre_base = "Solución Hartmann" if ent.base == "Hartmann" else "Solución salina 0.9%"
    nombre_glu = f"Solución glucosada {ent.glucosa_pct}%"
    if ent.solucion == "1:1":
        return [(nombre_glu, glu_comp, 0.5), (nombre_base, base, 0.5)]
    if ent.solucion == "2:1":
        return [(nombre_glu, glu_comp, 2 / 3), (nombre_base, base, 1 / 3)]
    raise ValueError(f"Solución desconocida: {ent.solucion}")


def calcular(ent: Entrada) -> Resultado:
    r = Resultado()
    peso = ent.peso_kg
    if peso <= 0:
        raise ValueError("El peso debe ser mayor que 0")
    if not 0 < ent.porcentaje <= 200:
        raise ValueError("El porcentaje debe estar entre 1 y 200")

    r.sc, r.sc_formula = superficie_corporal(peso, ent.talla_cm)

    # 1. Volumen de mantenimiento
    if ent.metodo == "SC":
        r.vol_calculado = r.sc * ent.ml_m2
    else:
        r.vol_calculado = holliday_segar(peso)

    # 2. Límite de adulto
    r.vol_limitado = r.vol_calculado
    if ent.limite_adulto and r.vol_calculado > ent.limite_ml:
        r.vol_limitado = ent.limite_ml
        r.limite_aplicado = True

    # 3. Restricción / ajuste porcentual
    V = r.vol_limitado * ent.porcentaje / 100.0
    r.vol_total = V
    r.ml_h = V / 24.0

    fracs = _fracciones(ent)

    # 4. Electrolitos: el volumen de concentrados se descuenta de la solución
    #    base para que el total sea exactamente el prescrito. Iteración de
    #    punto fijo (converge en pocas vueltas porque los volúmenes son chicos).
    elec = {k: v for k, v in ent.electrolitos.items() if v.activo and v.valor > 0}
    metas = {ion: _meq_meta(e, ion, peso, r.sc, V) for ion, e in elec.items()}
    vol_aditivos = 0.0
    agregar: dict[str, float] = {}
    for _ in range(50):
        vol_base = max(V - vol_aditivos, 0.0)
        agregar = {}
        for ion, meta in metas.items():
            aporte_base = sum(comp.get(ion, 0) * f * vol_base / 1000 for _, comp, f in fracs)
            falta = meta - aporte_base if ent.descontar_base else meta
            agregar[ion] = max(falta, 0.0)
        nuevo = sum(m / CONCENTRADOS[i]["meq_ml"] for i, m in agregar.items())
        if abs(nuevo - vol_aditivos) < 1e-9:
            break
        vol_aditivos = nuevo
    vol_base = max(V - vol_aditivos, 0.0)
    if vol_aditivos > V * 0.5:
        raise ValueError("El volumen de electrolitos excede la mitad del total; revise las dosis")

    # 5. Componentes y composición final
    glucosa_g = 0.0
    osm_total = 0.0
    totales = {"Na": 0.0, "K": 0.0, "Ca": 0.0, "Mg": 0.0}
    base_aporte = {"Na": 0.0, "K": 0.0, "Ca": 0.0, "Mg": 0.0}
    for nombre, comp, f in fracs:
        ml = vol_base * f
        r.componentes.append((nombre, ml))
        glucosa_g += comp["glucosa"] * ml / 1000
        osm_total += comp["osm"] * ml / 1000
        for ion in ("Na", "K", "Ca"):
            base_aporte[ion] += comp.get(ion, 0) * ml / 1000
    for ion in totales:
        totales[ion] = base_aporte[ion]
    for ion, meq in agregar.items():
        c = CONCENTRADOS[ion]
        ml = meq / c["meq_ml"]
        if ml > 0:
            r.componentes.append((c["nombre"], ml))
        osm_total += ml * c["osm_ml"]
        totales[ion] += meq

    r.glucosa_g = glucosa_g
    r.glucosa_pct_final = glucosa_g / V * 100 if V else 0
    r.gkm = glucosa_g * 1000 / (peso * 1440)
    r.osm = osm_total / V * 1000 if V else 0

    for ion, tot in totales.items():
        if tot <= 0 and ion not in elec:
            continue
        d = {
            "total": tot,
            "base": base_aporte[ion],
            "agregado": agregar.get(ion, 0.0),
            "meta": metas.get(ion),
            "por_kg": tot / peso,
            "por_m2": tot / r.sc,
            "por_l": tot / V * 1000 if V else 0,
        }
        if ion in ("Ca", "Mg"):
            d["mg_kg"] = (tot / CONCENTRADOS[ion]["meq_ml"]) * CONCENTRADOS[ion]["mg_ml"] / peso
        r.aportes[ion] = d
    r.na_meq_l = totales["Na"] / V * 1000 if V else 0

    # 6. Advertencias
    adv = r.advertencias
    if peso < 3:
        adv.append("Peso < 3 kg: la guía AAP no aplica a neonatos < 28 días; use protocolo neonatal.")
    if r.limite_aplicado:
        adv.append(f"Se aplicó el límite de adulto ({ent.limite_ml:.0f} mL/día).")
    if ent.porcentaje < 100:
        adv.append(f"Restricción hídrica al {ent.porcentaje:.0f}% (NICE NG29: 50-80% si riesgo de SIADH).")
    if ent.porcentaje > 100:
        adv.append(f"Volumen al {ent.porcentaje:.0f}% del mantenimiento: vigile sobrecarga hídrica.")
    if r.na_meq_l < 130:
        adv.append(f"Solución hipotónica (Na {r.na_meq_l:.0f} mEq/L). AAP 2018 recomienda "
                   "isotónicas (Na 131-154 mEq/L) por riesgo de hiponatremia.")
    if r.osm > 900:
        adv.append(f"Osmolaridad {r.osm:.0f} mOsm/L > 900: requiere acceso venoso central.")
    elif r.osm > 600:
        adv.append(f"Osmolaridad {r.osm:.0f} mOsm/L: riesgo de flebitis por vía periférica.")
    if r.glucosa_pct_final > 12.5:
        adv.append(f"Glucosa final {r.glucosa_pct_final:.1f}%: > 12.5% requiere vía central.")
    if r.gkm > 8:
        adv.append(f"Carga de glucosa {r.gkm:.1f} mg/kg/min elevada para mantenimiento.")
    if "K" in r.aportes:
        k = r.aportes["K"]
        if k["por_l"] > 40:
            adv.append(f"K {k['por_l']:.0f} mEq/L > 40: no recomendado por vía periférica.")
        if k["total"] / 24 / peso > 0.5:
            adv.append("Infusión de K > 0.5 mEq/kg/h: requiere monitoreo cardiaco.")
    for ion, d in r.aportes.items():
        e = elec.get(ion)
        if not e or e.modo not in RANGOS.get(ion, {}):
            continue
        lo, hi = RANGOS[ion][e.modo]
        if not lo <= e.valor <= hi:
            adv.append(f"{ion}: {e.valor:g} {e.modo} fuera del rango habitual ({lo}-{hi}).")
        if ent.descontar_base and d["meta"] is not None and d["base"] > d["meta"] + 1e-6:
            adv.append(f"{ion}: la solución base ya aporta más de la meta "
                       f"({d['base']:.1f} vs {d['meta']:.1f} mEq/día).")
    return r


def goteo(ml_h: float) -> dict[str, float]:
    """Microgotas/min (60 gt/mL) y macrogotas/min (20 gt/mL)."""
    return {"micro": ml_h, "macro": ml_h / 3.0}
