import unittest

from calculos import Electrolito, Entrada, calcular, hoja_rol, holliday_segar, superficie_corporal


class TestVolumen(unittest.TestCase):
    def test_holliday_segar(self):
        self.assertEqual(holliday_segar(8), 800)
        self.assertEqual(holliday_segar(10), 1000)
        self.assertEqual(holliday_segar(15), 1250)
        self.assertEqual(holliday_segar(20), 1500)
        self.assertEqual(holliday_segar(35), 1800)

    def test_limite_adulto(self):
        r = calcular(Entrada(peso_kg=70))  # HS = 2500
        self.assertTrue(r.limite_aplicado)
        self.assertAlmostEqual(r.vol_total, 2400)

    def test_restriccion(self):
        r = calcular(Entrada(peso_kg=12, porcentaje=70))  # 1100 * 0.7
        self.assertAlmostEqual(r.vol_total, 770)
        r = calcular(Entrada(peso_kg=70, porcentaje=50))  # min(2500,2400)*0.5
        self.assertAlmostEqual(r.vol_total, 1200)

    def test_sc(self):
        sc, f = superficie_corporal(20, 110)
        self.assertAlmostEqual(sc, 0.7817, places=3)
        self.assertEqual(f, "Mosteller")
        r = calcular(Entrada(peso_kg=20, talla_cm=110, metodo="SC", ml_m2=1500))
        self.assertAlmostEqual(r.vol_total, 0.7817 * 1500, delta=1)


class TestSoluciones(unittest.TestCase):
    def test_mixta(self):
        r = calcular(Entrada(peso_kg=10))
        self.assertAlmostEqual(r.na_meq_l, 154)
        self.assertAlmostEqual(r.glucosa_pct_final, 5)
        self.assertAlmostEqual(r.gkm, 50 * 1000 / (10 * 1440), places=3)

    def test_1_1(self):
        r = calcular(Entrada(peso_kg=10, solucion="1:1"))
        vols = dict(r.componentes)
        self.assertAlmostEqual(vols["Solución glucosada 5%"], 500)
        self.assertAlmostEqual(vols["Cloruro de sodio 0.9%"], 500)
        self.assertAlmostEqual(r.na_meq_l, 77)

    def test_2_1_hartmann_d10(self):
        r = calcular(Entrada(peso_kg=10, solucion="2:1", base="Hartmann", glucosa_pct=10))
        vols = dict(r.componentes)
        self.assertAlmostEqual(vols["Solución glucosada 10%"], 666.67, places=1)
        self.assertAlmostEqual(vols["Solución Hartmann"], 333.33, places=1)
        self.assertAlmostEqual(r.glucosa_pct_final, 6.667, places=2)


class TestElectrolitos(unittest.TestCase):
    def test_k_20_meq_l_exacto(self):
        ent = Entrada(peso_kg=10, electrolitos={"K": Electrolito(True, "mEq/L", 20)})
        r = calcular(ent)
        self.assertAlmostEqual(r.vol_total, 1000)
        self.assertAlmostEqual(sum(v for _, v in r.componentes), 1000)
        self.assertAlmostEqual(r.aportes["K"]["total"], 20, places=6)
        self.assertAlmostEqual(dict(r.componentes)["Cloruro de potasio 20 mEq/5 ml"], 5, places=6)
        ent.fuentes = {"K": "Cloruro de potasio 14.9% (20 mEq/10 ml)"}
        r = calcular(ent)
        self.assertAlmostEqual(dict(r.componentes)["Cloruro de potasio 14.9% (20 mEq/10 ml)"], 10, places=6)

    def test_na_descuenta_base(self):
        # 1:1 salina aporta 77 mEq/L; meta 3 mEq/kg en 10 kg = 30 mEq < 77 => nada que agregar
        ent = Entrada(peso_kg=10, solucion="1:1", electrolitos={"Na": Electrolito(True, "mEq/kg/día", 3)})
        r = calcular(ent)
        self.assertEqual(r.aportes["Na"]["agregado"], 0)
        self.assertTrue(any("ya aporta" in a for a in r.advertencias))

    def test_na_sin_descontar_glucosada_m2(self):
        ent = Entrada(peso_kg=20, talla_cm=110, solucion="2:1", descontar_base=False,
                      electrolitos={"Na": Electrolito(True, "mEq/m²SC/día", 40)})
        r = calcular(ent)
        self.assertAlmostEqual(r.aportes["Na"]["agregado"], 40 * r.sc, places=6)
        self.assertAlmostEqual(sum(v for _, v in r.componentes), r.vol_total, places=6)

    def test_ca_mg_kg(self):
        ent = Entrada(peso_kg=10, electrolitos={"Ca": Electrolito(True, "mg/kg/día", 100)})
        r = calcular(ent)
        self.assertAlmostEqual(dict(r.componentes)["Gluconato de calcio 10%"], 10, places=6)
        self.assertAlmostEqual(r.aportes["Ca"]["mg_kg"], 100, places=6)

    def test_advertencia_osm_d50(self):
        r = calcular(Entrada(peso_kg=10, solucion="1:1", glucosa_pct=50))
        self.assertTrue(any("central" in a for a in r.advertencias))


class TestFuentesYRol(unittest.TestCase):
    def test_na_con_salina_09(self):
        # Glucosada 5 % sola (2:1 sin descontar no aplica); usar 2:1 y meta alta de Na
        ent = Entrada(peso_kg=10, solucion="2:1", fuentes={"Na": "Cloruro de sodio 0.9%"},
                      electrolitos={"Na": Electrolito(True, "mEq/kg/día", 8)})
        r = calcular(ent)
        self.assertAlmostEqual(sum(v for _, v in r.componentes), 1000, places=6)
        self.assertAlmostEqual(r.aportes["Na"]["total"], 80, places=4)

    def test_hoja_rol_8h(self):
        ent = Entrada(peso_kg=12, talla_cm=85, metodo="SC", ml_m2=1100, rol_h=8,
                      electrolitos={"K": Electrolito(True, "mEq/m²SC/día", 45)})
        r = calcular(ent)
        txt = hoja_rol(ent, r, "2.-")
        self.assertIn("1100 ml/m2sc/día para rol de 8 horas", txt)
        self.assertIn(f"Volumen total: {r.vol_total / 3:.0f} ml", txt)
        self.assertIn("(45 mEq/m²SC/d)", txt)
        self.assertIn("(GKM", txt)

    def test_rol_24_neonato(self):
        ent = Entrada(peso_kg=3.2, rol_h=24)
        txt = hoja_rol(ent, calcular(ent))
        self.assertIn("para 24 horas", txt)


if __name__ == "__main__":
    unittest.main()
