# Calculadora de Soluciones Pediátricas

Aplicación de escritorio (Windows `.exe`) para calcular líquidos IV de mantenimiento y electrolitos en pediatría.

> Apoyo al cálculo. Verifique siempre las dosis; no sustituye el juicio clínico ni los protocolos de su unidad.

## Uso

1. **Peso (kg)**: es el único dato obligatorio. La talla es opcional y solo sirve para la SC por Mosteller; sin talla se usa (4P+7)/(P+90).
2. **Volumen**: Holliday-Segar (100/50/20 mL/kg/día) o superficie corporal (mL/m²SC/día, 1500 por defecto). El **límite de adulto** viene en 2400 mL/día y se puede editar.
3. **Restricción hídrica**: deslizador del 30 al 150 %, con botones rápidos de 100, 80, 75, 66 y 50 %. Se aplica después del límite de adulto.
4. **Solución**:
   - **Mixta** = glucosa 5 % + NaCl 0.9 % (Na 154 mEq/L).
   - **1:1** = 1 parte glucosada : 1 parte salina 0.9 % o Hartmann.
   - **2:1** = 2 partes glucosada : 1 parte salina 0.9 % o Hartmann.
   - Glucosada al 5, 10 o 50 %.
5. **Electrolitos** (Na, K, Ca, Mg): cada uno en mEq/kg/día, mEq/m²SC/día o mEq/L. El K viene en 20 mEq/L. Ca y Mg también aceptan mg/kg/día.
   - "Descontar lo que ya aporta la solución base": solo se agrega la diferencia hasta la meta.
   - El volumen de los concentrados se resta de la solución base para que el total sea exactamente el prescrito.

El resultado se recalcula al instante y muestra:
- volumen en 24 h, mL/h, volumen por turno de 8 h, microgotas y macrogotas;
- mL de cada componente en 24 h y por turno;
- mEq totales en mEq/kg, mEq/m² y mEq/L;
- % de glucosa, carga de glucosa (mg/kg/min) y osmolaridad;
- advertencias.

El botón **Copiar indicación** copia un texto listo para pegar en la nota médica.

## Concentrados considerados

| Ion | Concentrado | mEq/mL |
|---|---|---|
| Na | NaCl 17.7 % | 3 |
| K | KCl 14.9 % | 2 |
| Ca | Gluconato de calcio 10 % (100 mg/mL) | 0.465 |
| Mg | Sulfato de magnesio 10 % (100 mg/mL) | 0.81 |

Hartmann: Na 130, K 4, Cl 109, Ca 3 mEq/L, lactato 28.

## Advertencias automáticas

- Solución hipotónica (Na < 130 mEq/L). La AAP 2018 recomienda soluciones isotónicas por riesgo de hiponatremia.
- Osmolaridad > 600 mOsm/L (riesgo de flebitis) o > 900 mOsm/L (requiere vía central). Glucosa > 12.5 %.
- K > 40 mEq/L por vía periférica, o infusión de K > 0.5 mEq/kg/h.
- Dosis fuera de los rangos habituales: Na 2-4 mEq/kg/día o 30-50 mEq/m²/día; K 1-3 mEq/kg/día, 20-40 mEq/m²/día o 20-40 mEq/L.
- Restricción hídrica, límite de adulto aplicado y peso < 3 kg (neonato).

## Bases (revisión 2025-2026)

- **Holliday-Segar** sigue siendo el método estándar de estimación (NICE NG29).
- **AAP 2018** (Feld et al., *Pediatrics* 142:e20183083): de 28 días a 18 años, usar soluciones isotónicas con KCl y dextrosa adecuados. Sigue vigente.
- **NICE NG29**: soluciones isotónicas con Na de 131 a 154 mmol/L. Restringir a 50-80 % del mantenimiento si hay riesgo de secreción no osmótica de ADH (postoperatorio, dolor, neumonía, SNC). En adultos se suelen usar de 2000 a 2500 mL/día como máximo.

## Generar el .exe

- **Automático**: cada push a esta carpeta ejecuta el workflow `.github/workflows/build-exe.yml` en Windows. El `.exe` se descarga desde *Actions → artifacts*.
- **Manual en Windows**: instale Python 3.10 o superior y ejecute `build_exe.bat`.

Para ejecutar sin compilar: `python app.py`. Pruebas: `python -m unittest test_calculos`.
