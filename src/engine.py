# -*- coding: utf-8 -*-
# Sistema experto de recomendaciones de rutinas de ejercicio

import collections
try:
    # Compatibilidad para que no reviente
    from collections.abc import Mapping, MutableMapping, Sequence
    for _name, _obj in (("Mapping", Mapping), ("MutableMapping", MutableMapping), ("Sequence", Sequence)):
        if not hasattr(collections, _name):
            setattr(collections, _name, _obj)
except Exception:
    pass
#Codigo por defecto
                    #Motor de reglas #Tipos de hechos
from experta import KnowledgeEngine, Fact, Rule, Field, MATCH, P, AS, W, L
import json
from typing import List, Dict, Any
from pathlib import Path #Manejo de archivos


# Hechos

class Usuario(Fact):
    """Hecho que describe el perfil del usuario"""
    id = Field(str, mandatory=True)
    nivel = Field(str, mandatory=True)  # principiante | intermedio | avanzado
    objetivo = Field(str, mandatory=True)  # perdida_grasa | ganancia_muscular | resistencia | salud_general
    gustos = Field(list, default=[])
    tiempo_minutos = Field(int, mandatory=True)# cuantos minutos quiere entrenar, las recomedaciones 180 min para abajo
    dias_por_semana = Field(int, mandatory=True)# igual maximo 7 dias
    equipo = Field(str, mandatory=True)  # casa_sin_equipo | casa_con_mancuernas | gimnasio
    lesiones = Field(list, default=[])#Puede quedar vacio si no tiene o ha tenido lesiones


class Rutina(Fact):
    """Hecho que representa una rutina recomendada"""
    usuario_id = Field(str, mandatory=True)
    nombre = Field(str, mandatory=True)
    objetivo = Field(str, mandatory=True)
    dias = Field(int, mandatory=True)
    duracion_min = Field(int, mandatory=True)
    ejercicios = Field(list, mandatory=True)  # lista de {nombre, series, repeticiones, tiempo, notas}
    notas = Field(str, default="")
    justificacion = Field(list, default=[])  # razones por las que se va a recomendar


# Utilidades y normalizacion de datos y estructuras por si se devuelve algo inmutable desde frozendict
def normalizar_usuario(u: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza datos de usuario para poder usarlos como hechos"""
    return {
        "id": u["id"],
        "nombre": u["nombre"],
        "apellidos": u["apellidos"],
        "edad": u["edad"],
        "objetivo": u["objetivo"],
        "nivel": u["nivel"],
    }

def limitar_duracion(tiempo_disponible: int, sugerido: int) -> int:
    """Ajusta la duración sugerida a lo disponible"""
    return max(20, min(sugerido, tiempo_disponible))


def ajustar_por_nivel(nivel: str, series_base: int, reps_base: int) -> Dict[str, int]:
    """Devuelve series y repeticiones ajustadas a nivel"""
    if nivel == "principiante":
        return {"series": max(2, series_base - 1), "reps": max(8, reps_base - 4)}
    if nivel == "intermedio":
        return {"series": series_base, "reps": reps_base}
    # avanzado
    return {"series": series_base + 1, "reps": reps_base + 2}


def evitar_por_lesion(nombre_ejercicio: str, lesiones: List[str]) -> bool:
    """True si el ejercicio debe evitarse por lesiones """
    nombre = nombre_ejercicio.lower()
    if "rodilla" in lesiones:
        if any(k in nombre for k in ["salto", "sprint", "saltos", "box jump", "burpee", "zancadas profundas"]):
            return True
    if "hombro" in lesiones:
        if any(k in nombre for k in ["press militar", "press por encima", "handstand", "dominada trasnuca"]):
            return True
    if "espalda" in lesiones:
        if any(k in nombre for k in ["peso muerto pesado", "buenos dias", "hiperextensiones pesadas"]):
            return True
    return False


def filtrar_por_equipo(nombre_ejercicio: str, equipo: str) -> bool:
    """True si el ejercicio es viable con el equipo disponible."""
    nombre = nombre_ejercicio.lower()
    if equipo == "casa_sin_equipo":
        # solo peso corporal / cardio simple
        no_viables = ["barra", "mancuerna", "kettlebell", "maquina", "polea", "press banca", "remo con barra"]
        return not any(p in nombre for p in no_viables)
    if equipo == "casa_con_mancuernas":
        # se permiten mancuernas y peso corporal, no máquinas ni barras
        no_viables = ["barra", "maquina", "polea", "smith"]
        return not any(p in nombre for p in no_viables)
    # gimnasio: todo viable
    return True


def bloque_ejercicios_basico(objetivo: str, nivel: str, equipo: str, lesiones: List[str]) -> List[Dict[str, Any]]:
    """Genera un bloque full-body base ajustado a restricciones."""
    base = [
        {"nombre": "Sentadillas", "series": 3, "reps": 12},
        {"nombre": "Flexiones", "series": 3, "reps": 10},
        {"nombre": "Remo con mancuerna", "series": 3, "reps": 12},
        {"nombre": "Plancha", "series": 3, "tiempo": "30-45s"},
        {"nombre": "Puente de glúteo", "series": 3, "reps": 12}
    ]
    # Ajustes por objetivo (ligeros)
    if objetivo == "ganancia_muscular":
        for e in base:
            if "reps" in e:
                e["reps"] += 2
    elif objetivo == "resistencia":
        for e in base:
            if "reps" in e:
                e["reps"] = max(10, e["reps"] - 2)

    # Ajuste por nivel
    for e in base:
        if "reps" in e and "series" in e:
            adj = ajustar_por_nivel(nivel, e["series"], e["reps"])
            e["series"], e["reps"] = adj["series"], adj["reps"]

    # Filtros por lesión y equipo disponible
    filtrados = []
    for e in base:
        if evitar_por_lesion(e["nombre"], lesiones):
            continue
        if not filtrar_por_equipo(e["nombre"], equipo):
            # Sustituciones simples
            sustituto = {"nombre": "Remo invertido", "series": e.get("series", 3), "reps": e.get("reps", 12)}
            if filtrar_por_equipo(sustituto["nombre"], equipo) and not evitar_por_lesion(sustituto["nombre"], lesiones):
                filtrados.append(sustituto)
            continue
        filtrados.append(e)
    return filtrados


def normalizar_estructura(x: Any) -> Any:
    """Convierte frozendict/tuplas/estructuras inmutables a normales para imprimir."""
    try:
        from collections.abc import Mapping, Sequence
    except Exception:
        from collections import Mapping, Sequence
    if isinstance(x, Mapping):
        return {k: normalizar_estructura(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [normalizar_estructura(v) for v in x]
    return x


class MotorRutinas(KnowledgeEngine):
    """Motor"""

    def __init__(self):
        super().__init__()
        self.resultados: Dict[str, List[Dict[str, Any]]] = {}

    def _agregar_rutina(self, usuario_id: str, rutina: Dict[str, Any]):
        self.resultados.setdefault(usuario_id, []).append(rutina)

    # Regla base, siempre ofrecer una full-body días si el objetivo es salud general o si el usuario es principiante
         #AS.u hace match y captura el hecho completo en u.
    @Rule(AS.u << Usuario(objetivo=L("salud_general") | L("perdida_grasa"),
                          nivel=MATCH.n, equipo=MATCH.eq, lesiones=MATCH.les,
                          dias_por_semana=MATCH.dias, tiempo_minutos=MATCH.tiempo))
    def r_full_body_salud(self, u, n, eq, les, dias, tiempo):
        dias_sugeridos = 3 if dias >= 3 else max(2, dias)
        duracion = limitar_duracion(tiempo, 40)
        ejercicios = bloque_ejercicios_basico("salud_general", n, eq, les)
        self.declare(Rutina(usuario_id=u["id"],
                            nombre="Full-Body Salud",
                            objetivo="salud_general",
                            dias=dias_sugeridos,
                            duracion_min=duracion,
                            ejercicios=ejercicios,
                            notas="Enfoque en técnica y consistencia.",
                            justificacion=["Objetivo salud/perdida de grasa", "Nivel y tiempo disponibles"]))

    # Pérdida de grasa incluir componente HIIT si no hay lesión que lo haga incompatible
    @Rule(AS.u << Usuario(objetivo="perdida_grasa", nivel=MATCH.n, gustos=MATCH.gustos,
                          equipo=MATCH.eq, lesiones=MATCH.les, dias_por_semana=MATCH.dias, tiempo_minutos=MATCH.tiempo))
    def r_hiitt_perdida_grasa(self, u, n, gustos, eq, les, dias, tiempo):
        if "rodilla" in les:
            # Evitar impactos, usar cardio bajo impacto
            cardio = [
                {"nombre": "Caminata rápida o bici estática (intervalos bajos)", "tiempo": "20-25m"}
            ]
            nombre = "Cardio bajo impacto + Core"
            just = ["Pérdida de grasa", "Lesión de rodilla: evitar alto impacto"]
        else:
            cardio = [
                {"nombre": "HIIT (20s ON / 40s OFF) x 10-12 rondas", "tiempo": "20m"},
                {"nombre": "Core: planchas y hollow holds", "tiempo": "10m"}
            ]
            nombre = "HIIT + Core"
            just = ["Pérdida de grasa", "HIIT si no hay lesión que lo impida"]

        # Ajuste por gustoss
        if "correr" in gustos and "rodilla" not in les:
            cardio[0]["nombre"] = "HIIT corriendo (cuestas o pista)"
        elif "ciclismo" in gustos:
            cardio[0]["nombre"] = cardio[0]["nombre"].replace("bici estática", "ciclismo/rodillos")

        dias_sugeridos = min(2, max(1, dias - 1))
        duracion = limitar_duracion(tiempo, 30)
        self.declare(Rutina(usuario_id=u["id"],
                            nombre=nombre,
                            objetivo="perdida_grasa",
                            dias=dias_sugeridos,
                            duracion_min=duracion,
                            ejercicios=cardio,
                            notas="Mantener RPE 7-8 en intervalos.",
                            justificacion=just))

    # Ganancia muscular dividir por empuje/tirón/piernas según días (osea PPl)
    @Rule(AS.u << Usuario(objetivo="ganancia_muscular", nivel=MATCH.n, equipo=MATCH.eq,
                          dias_por_semana=MATCH.dias, tiempo_minutos=MATCH.tiempo, lesiones=MATCH.les, gustos=MATCH.g))
    def r_hipertrofia_split(self, u, n, eq, dias, tiempo, les, g):
        # Elegir split según días
        if dias >= 4:
            split = ["Empuje", "Tirón", "Piernas", "Full-body accesorios"]
            dias_sugeridos = 4
        elif dias == 3:
            split = ["Empuje", "Tirón", "Piernas"]
            dias_sugeridos = 3
        else:
            split = ["Full-body hipertrofia"]
            dias_sugeridos = dias

        ejercicios_por_dia = {
            "Empuje": [
                {"nombre": "Press banca con mancuernas", "series": 3, "reps": 10},
                {"nombre": "Flexiones", "series": 3, "reps": 12},
                {"nombre": "Press militar con mancuernas", "series": 3, "reps": 10},
                {"nombre": "Fondos en paralelas", "series": 3, "reps": 8}
            ],
            "Tirón": [
                {"nombre": "Remo con mancuerna", "series": 3, "reps": 12},
                {"nombre": "Dominadas o jalón", "series": 3, "reps": 8},
                {"nombre": "Curl de bíceps con mancuernas", "series": 3, "reps": 12}
            ],
            "Piernas": [
                {"nombre": "Sentadillas", "series": 4, "reps": 8},
                {"nombre": "Zancadas", "series": 3, "reps": 10},
                {"nombre": "Peso muerto rumano", "series": 3, "reps": 10},
                {"nombre": "Elevación de gemelos", "series": 3, "reps": 15}
            ],
            "Full-body accesorios": [
                {"nombre": "Prensa o sentadilla goblet", "series": 3, "reps": 12},
                {"nombre": "Remo en máquina o mancuerna", "series": 3, "reps": 12},
                {"nombre": "Elevaciones laterales", "series": 3, "reps": 15},
                {"nombre": "Core (rueda/plancha)", "series": 3, "reps": 12}
            ],
            "Full-body hipertrofia": [
                {"nombre": "Sentadilla goblet", "series": 3, "reps": 10},
                {"nombre": "Press banca con mancuernas", "series": 3, "reps": 10},
                {"nombre": "Remo con mancuerna", "series": 3, "reps": 12},
                {"nombre": "Elevaciones laterales", "series": 3, "reps": 15}
            ]
        }

        # Filtros por equipo/lesión y ajustes por nivel
        plan = []
        for dia in split:
            bloque = []
            for e in ejercicios_por_dia[dia]:
                if evitar_por_lesion(e["nombre"], les):
                    continue
                if not filtrar_por_equipo(e["nombre"], eq):
                    continue
                adj = ajustar_por_nivel(n, e["series"], e["reps"])
                bloque.append({"nombre": e["nombre"], "series": adj["series"], "reps": adj["reps"]})
            if bloque:
                plan.append({"dia": dia, "ejercicios": bloque})

        # Preferencias incluir calistenia si gusta y es viable
        if "calistenia" in g:
            for e in [{"nombre": "Dominadas", "series": 3, "reps": 6}, {"nombre": "Flexiones lastradas", "series": 3, "reps": 8}]:
                if filtrar_por_equipo(e["nombre"], eq) and not evitar_por_lesion(e["nombre"], les):
                    if plan:
                        plan[0]["ejercicios"].append(e)

        duracion = limitar_duracion(tiempo, 60)
        self.declare(Rutina(usuario_id=u["id"],
                            nombre="Hipertrofia (split adaptable)",
                            objetivo="ganancia_muscular",
                            dias=dias_sugeridos,
                            duracion_min=duracion,
                            ejercicios=plan,
                            notas="Prioriza sobrecarga progresiva y técnica.",
                            justificacion=["Objetivo ganancia muscular", f"Split según {dias} días disponibles"]))

    # Resistencia cardio progresivo + fuerza ligera
    @Rule(AS.u << Usuario(objetivo="resistencia", nivel=MATCH.n, gustos=MATCH.g,
                          equipo=MATCH.eq, lesiones=MATCH.les, dias_por_semana=MATCH.dias, tiempo_minutos=MATCH.tiempo))
    def r_resistencia(self, u, n, g, eq, les, dias, tiempo):
        cardio_base = "Correr suave" if "correr" in g and "rodilla" not in les else "Ciclismo/Zona 2"
        if "ciclismo" in g:
            cardio_base = "Ciclismo/Zona 2"
        if "rodilla" in les:
            cardio_base = "Ciclismo/Zona 2 o elíptica"

        fuerza = bloque_ejercicios_basico("resistencia", n, eq, les)
        plan = [
            {"nombre": cardio_base, "tiempo": "30-45m", "notas": "Zona 2 (conversacional)"},
            {"nombre": "Fuerza ligera full-body", "detalle": fuerza}
        ]
        dias_sugeridos = min(5, max(3, dias))
        duracion = limitar_duracion(tiempo, 50)
        self.declare(Rutina(usuario_id=u["id"],
                            nombre="Base de resistencia + fuerza ligera",
                            objetivo="resistencia",
                            dias=dias_sugeridos,
                            duracion_min=duracion,
                            ejercicios=plan,
                            notas="Progresión semanal 5-10%.",
                            justificacion=["Objetivo resistencia", "Preferencias de cardio", "Control de lesiones"]))

    # Adaptación por tiempo muy limitado, sesiones rapidas
    @Rule(AS.u << Usuario(tiempo_minutos=P(lambda t: t <= 30)))
    def r_sesiones_express(self, u):
        self.declare(Rutina(usuario_id=u["id"],
                            nombre="Sesiones Express",
                            objetivo="eficiencia_tiempo",
                            dias=u["dias_por_semana"],
                            duracion_min=u["tiempo_minutos"],
                            ejercicios=[{"nombre": "Circuito EMOM 20m: sentadilla aire, flexiones, remo invertido, plancha"}],
                            notas="Mantener transición rápida entre ejercicios.",
                            justificacion=["Tiempo disponible <= 30m"]))

    # Post-procesamiento recolecto las Rutina declaradas
    @Rule(AS.r << Rutina(usuario_id=MATCH.uid,
                         nombre=MATCH.nombre, objetivo=MATCH.obj, dias=MATCH.dias,
                         duracion_min=MATCH.dur, ejercicios=MATCH.ejs, notas=MATCH.notas, justificacion=MATCH.just))
    def r_colectar(self, r, uid, nombre, obj, dias, dur, ejs, notas, just):
        self._agregar_rutina(uid, {
            "nombre": nombre,
            "objetivo": obj,
            "dias": dias,
            "duracion_min": dur,
            "ejercicios": normalizar_estructura(ejs),
            "notas": notas,
            "justificacion": just
        })

    # Helper para ejecutar por un usuario dict
    def recomendar_para_usuario(self, u: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.reset()
        self.resultados = {}
        self.declare(Usuario(**u))
        self.run()
        return self.resultados.get(u["id"], [])

#Hacer la carga de datos desde el archivo JSON
def cargar_usuarios_desde_json(path: str) -> List[Dict[str, Any]]:
    #Codigo por defecto path
    p = Path(path)
    if not p.is_absolute() and not p.exists():
        proyecto_root = Path(__file__).resolve().parent.parent
        candidato = proyecto_root / path
        if candidato.exists():
            p = candidato
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

##Adaptacion en proceso de mejora, pero ya pide al usuario datos y los usa correctamente, despues le agregare la funcion de una base de datos
def _input_opcion(prompt: str, opciones: List[str]) -> str:
    """Pide una opción válida no es sencible a mayusculas siempre lo bajo a minsuculas."""
    opciones_lower = [o.lower() for o in opciones]
    while True:
        valor = input(f"{prompt} {opciones} > ").strip().lower()
        if valor in opciones_lower:
            return valor
        print(f"Valor inválido. Debe ser una de: {opciones}")


def _input_entero(prompt: str, minimo: int = None, maximo: int = None) -> int:
    while True:
        txt = input(f"{prompt} > ").strip()
        try:
            n = int(txt)
            if minimo is not None and n < minimo:
                print(f"Debe ser >= {minimo}")
                continue
            if maximo is not None and n > maximo:
                print(f"Debe ser <= {maximo}")
                continue
            return n
        except ValueError:
            print("Ingresa un número entero válido.")


def _input_lista(prompt: str) -> List[str]:
    """Pide una lista separada por comas"""
    txt = input(f"{prompt} (separa por comas, puede estar vacío) > ").strip()
    if not txt:
        return []
    return [p.strip().lower() for p in txt.split(",") if p.strip()]


def preguntar_usuario_interactivo() -> Dict[str, Any]:
    """Construye un diccionario Usuario pidiendo datos por consola."""
    print("\n== Modo interactivo: genera tu perfil de entrenamiento ==\n")
    uid = input("Identificador (id) del usuario > ").strip() or "u#"
    nivel = _input_opcion("Nivel", ["principiante", "intermedio", "avanzado"])
    objetivo = _input_opcion("Objetivo", ["perdida_grasa", "ganancia_muscular", "resistencia", "salud_general"])
    gustos = _input_lista("Gustos (ej.: correr, ciclismo, yoga, calistenia, pesas, hiit, natacion)")
    tiempo_minutos = _input_entero("Tiempo por sesión (minutos)", minimo=10, maximo=180)
    dias_por_semana = _input_entero("Días por semana", minimo=1, maximo=7)
    equipo = _input_opcion("Equipo", ["casa_sin_equipo", "casa_con_mancuernas", "gimnasio"])
    lesiones = _input_lista("Lesiones (ej.: rodilla, hombro, espalda)")

    return {
        "id": uid,
        "nivel": nivel,
        "objetivo": objetivo,
        "gustos": gustos,
        "tiempo_minutos": tiempo_minutos,
        "dias_por_semana": dias_por_semana,
        "equipo": equipo,
        "lesiones": lesiones
    }

#COMIENZA BLOQUE DE CODIGO GENERADO POR OLLAMA
def _imprimir_recomendaciones(u: Dict[str, Any], recomendaciones: List[Dict[str, Any]]) -> None:
    print(f"\n=== Recomendaciones para {u['id']} ===")
    if not recomendaciones:
        print("No se generaron recomendaciones.")
        return
    for i, r in enumerate(recomendaciones, 1):
        print(f"\n{i}) {r['nombre']} [{r['objetivo']}]")
        print(f"- Días/semana: {r['dias']} | Duración: {r['duracion_min']} min")
        print("- Justificación:", "; ".join(r.get("justificacion", [])))
        print("- Notas:", r.get("notas", ""))
        print("- Plan:")
        # Imprimir flexible según estructura
        if isinstance(r["ejercicios"], list) and r["ejercicios"] and isinstance(r["ejercicios"][0], dict) and "dia" in r["ejercicios"][0]:
            for d in r["ejercicios"]:
                print(f"  * {d['dia']}:")
                for e in d["ejercicios"]:
                    desc = f"{e['nombre']} - {e.get('series','?')}x{e.get('reps','?')}"
                    print(f"    - {desc}")
        elif isinstance(r["ejercicios"], list):
            for e in r["ejercicios"]:
                if "detalle" in e:
                    print(f"  * {e['nombre']}:")
                    for sub in e["detalle"]:
                        if "tiempo" in sub:
                            print(f"    - {sub['nombre']} - {sub['tiempo']}")
                        else:
                            print(f"    - {sub['nombre']} - {sub.get('series','?')}x{sub.get('reps','?')}")
                else:
                    if "tiempo" in e:
                        print(f"  * {e['nombre']} - {e['tiempo']}")
                    else:
                        print(f"  * {e['nombre']} - {e.get('series','?')}x{e.get('reps','?')}")
#TERMINA BLOQUE DE CODIGO GENERADO POR OLLAMA

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sistema experto de rutinas usando experta")
    parser.add_argument("--usuarios", type=str, default="data/usuarios.json", help="Ruta al JSON de usuarios")
    parser.add_argument("--interactivo", action="store_true", help="Modo interactivo = preguntar datos por consola")
    args = parser.parse_args()

    motor = MotorRutinas()

    if args.interactivo:
        u = preguntar_usuario_interactivo()
        recomendaciones = motor.recomendar_para_usuario(u)
        _imprimir_recomendaciones(u, recomendaciones)
        return

    # Modo por archivo JSON como fue el primero fue aun sigue estando por defecto
    usuarios = cargar_usuarios_desde_json(args.usuarios)
    for u in usuarios:
        recomendaciones = motor.recomendar_para_usuario(u)
        _imprimir_recomendaciones(u, recomendaciones)


if __name__ == "__main__":
    main()