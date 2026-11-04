"""
Bot de reporte para @colombia.core
------------------------------------
Recolecta contenido reciente de medios colombianos (RSS), Reddit y Google News,
lo filtra/resume con la API de Claude buscando ángulos "reveladores" útiles
para posts, y manda el resultado por Telegram.

No necesitas correr esto en tu computador: está pensado para ejecutarse
automáticamente vía GitHub Actions (ver .github/workflows/reporte.yml).

Variables de entorno necesarias (se configuran como "Secrets" en GitHub, NUNCA
se escriben directamente en este archivo):
    TELEGRAM_BOT_TOKEN   -> token que te da @BotFather
    TELEGRAM_CHAT_ID     -> el ID de tu chat de Telegram
    ANTHROPIC_API_KEY    -> tu clave de console.anthropic.com
"""

import os
import time
import random
import feedparser
import requests
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE FUENTES
# ---------------------------------------------------------------------------

# Cuántos días hacia atrás mirar (para no repetir noticias viejas en cada corrida)
DIAS_ATRAS = 3

RSS_FEEDS = [
    "https://www.eltiempo.com/rss/cultura.xml",
    "https://www.eltiempo.com/rss/historia.xml",
    "https://www.semana.com/arc/outboundfeeds/rss/category/cultura/",
    "https://www.pulzo.com/rss/curiosidades.xml",
    "https://www.elespectador.com/arc/outboundfeeds/rss/category/cultura/",
]

# Búsquedas en Google News (se arma automáticamente la URL del RSS)
GOOGLE_NEWS_QUERIES = [
    "historia Colombia",
    "cultura colombiana",
    "música colombiana historia",
]

# Subreddits a revisar (usamos el JSON público, no requiere API key de Reddit)
SUBREDDITS = ["Colombia", "askcolombia"]

# Búsquedas adicionales para categorías especiales (iceberg, conspiraciones, historias raras)
BUSQUEDAS_ESPECIALES = [
    "iceberg Colombia",
    "conspiraciones Colombia",
    "historias raras Colombia",
    "misterios sin resolver Colombia",
]


def google_news_rss_url(query: str) -> str:
    q = query.replace(" ", "+")
    return f"https://news.google.com/rss/search?q={q}&hl=es-419&gl=CO&ceid=CO:es"


# ---------------------------------------------------------------------------
# 2. RECOLECCIÓN
# ---------------------------------------------------------------------------

def fecha_reciente(struct_time, dias=DIAS_ATRAS):
    if struct_time is None:
        return True  # si no trae fecha, la dejamos pasar y que el filtro decida
    fecha = datetime(*struct_time[:6], tzinfo=timezone.utc)
    limite = datetime.now(timezone.utc) - timedelta(days=dias)
    return fecha >= limite


def recolectar_rss(url):
    items = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            fecha = entry.get("published_parsed") or entry.get("updated_parsed")
            if fecha_reciente(fecha):
                items.append({
                    "titulo": entry.get("title", "").strip(),
                    "link": entry.get("link", ""),
                    "fuente": feed.feed.get("title", url),
                })
    except Exception as e:
        print(f"[aviso] no se pudo leer {url}: {e}")
    return items


def recolectar_reddit(subreddit):
    items = []
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=20"
    headers = {"User-Agent": "colombia-core-bot/1.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        for post in data["data"]["children"]:
            p = post["data"]
            created = datetime.fromtimestamp(p["created_utc"], tz=timezone.utc)
            if created >= datetime.now(timezone.utc) - timedelta(days=DIAS_ATRAS):
                items.append({
                    "titulo": p.get("title", "").strip(),
                    "link": f"https://reddit.com{p.get('permalink', '')}",
                    "fuente": f"r/{subreddit}",
                })
    except Exception as e:
        print(f"[aviso] no se pudo leer r/{subreddit}: {e}")
    return items


def recolectar_todo():
    items = []
    for url in RSS_FEEDS:
        items += recolectar_rss(url)
    for q in GOOGLE_NEWS_QUERIES + BUSQUEDAS_ESPECIALES:
        items += recolectar_rss(google_news_rss_url(q))
    for sub in SUBREDDITS:
        items += recolectar_reddit(sub)
    return items


# ---------------------------------------------------------------------------
# 3. FILTRADO Y RESUMEN CON CLAUDE
# ---------------------------------------------------------------------------

def curar_con_claude(items):
    if not items:
        return "No encontré nada nuevo relevante en esta corrida."

    api_key = os.environ["ANTHROPIC_API_KEY"]

    lista_texto = "\n".join(
        f"- {it['titulo']} ({it['fuente']}) -> {it['link']}" for it in items
    )

    prompt = f"""Eres un curador de contenido para la cuenta de Instagram @colombia.core,
una página de cultura, historia y música colombiana.

GUÍA DE ESTILO (basada en cuentas de referencia de la creadora):
- Estética tipo @hidden.ny y @artifaxing: archivo curado y ATEMPORAL. No importa si algo
  pasó ayer o hace 40 años — lo que importa es que sea un hallazgo "revelador" o poco conocido,
  no que sea noticia reciente. Evita cualquier cosa que suene a "noticiero".
- Formato/tono tipo @raptv, @bars y @dexerto: directo, con gancho, tipo infográfico corto —
  no explicaciones largas.
- El patrón que mejor ha funcionado hasta ahora: identidad nacional colombiana + ángulo
  "revelador" (ejemplos ya probados: las familias más ricas de Colombia, la historia del
  cigarrillo Pielroja).
- Categorías especiales que también valen mucho para esta cuenta: cosas tipo "iceberg de
  Colombia" (capas de conocimiento poco conocido sobre el país), conspiraciones colombianas,
  e historias raras/curiosas — dales prioridad si aparecen en la lista cruda.
- Los temas NO necesitan ser amplios ni grandes — una anécdota pequeña y documentable
  (ej. un parque que cerró, el apodo curioso de algo) es tan válida como un tema histórico
  grande. Basta con un dato + una descripción breve.
- REGLA OBLIGATORIA: todo lo que elijas tiene que conectar explícitamente con Colombia —
  una región, un pueblo, una persona pública colombiana, o un hecho colombiano específico.
  Descarta cualquier cosa sin ese gancho local, sin importar qué tan interesante sea.
- Temas prioritarios ya identificados por la creadora (dales prioridad si aparece algo
  relacionado, aunque sea indirectamente): 28 de mayo / El Bronx, Boyacá vs. Suiza, nazis en
  Colombia, menciones de Colombia en canciones famosas, Kid Pambele, primer álbum de rap de
  La Etnia, Jaime Garzón, Toma del Palacio de Justicia.

Aquí hay una lista cruda de titulares recolectados de medios, Reddit y Google News:

{lista_texto}

Tu tarea:
1. Elige SOLO los que tengan potencial real de post según la guía de estilo de arriba.
   Descarta política/economía de coyuntura sin ángulo cultural o histórico, y descarta
   cualquier cosa que sea "noticia del día" sin sustancia atemporal detrás.
2. Para cada uno elegido, entrega esta estructura exacta:
   📌 [Título sugerido para el post, corto y con gancho]
   - Qué encontré: resumen de 2-4 líneas del hallazgo/dato/historia
   - Personajes/lugares clave: nombres, regiones, instituciones involucradas
   - Fechas clave: si aplica
   - Para buscar multimedia: 2-3 palabras/frases concretas para buscar en Google/YouTube
     y encontrar fotos o videos de apoyo
   - Fuente: el link original
3. Si nada de la lista cruda encaja bien, dilo honestamente en vez de forzar opciones débiles.
4. Máximo 4 ítems con esta estructura completa (mejor pocos y bien desarrollados que muchos
   superficiales). Incluye como mucho 1 ítem de deportes/fútbol: la cuenta no es de deportes, ordenados por qué tan bueno es el ángulo. Texto plano, sin markdown de
   tablas, listo para Telegram.
"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 2500,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    return "".join(block.get("text", "") for block in data["content"])


def explorar_tema_atemporal():
    """
    Complemento a lo anterior: en vez de solo mirar 'lo nuevo' en RSS/Reddit,
    esto le pide a Claude que investigue (con su propia búsqueda web) un tema
    prioritario de la lista de la creadora, sin importar antigüedad, y saque
    ángulos concretos de post. Rota un tema distinto en cada corrida.
    """
    api_key = os.environ["ANTHROPIC_API_KEY"]

    temas_prioritarios = [
        "mitos y leyendas de Colombia",
        "28 de mayo El Bronx Bogotá",
        "14 cañonazos Colombia",
        "Unidad POLFA F2 Colombia",
        "nazis en Colombia historia",
        "Pisasuave unidad guerrilla",
        "Ciciaquapark Bogotá",
        "tenis exclusivos colombianos historia",
        "Chicas Águila historia",
        "todos los 10 de la selección Colombia historia",
        "techos de la vieja guardia Colombia",
        "colombianos en la Guerra de Corea",
        "álbumes de música colombiana curiosidades",
        "récords colombianos curiosos",
        "Boyacá le declaró la guerra a Suiza",
        "pueblo más borracho de Colombia",
        "SCADA Colombia",
        "Juegos Panamericanos 1971 Colombia",
        "Orozco Colombia historia",
        "hotel Salto del Tequendama historia",
        "Messi en Pereira",
        "19 de abril Palacio de Justicia",
        "relojes de políticos importantes de Colombia",
        "campo de concentración Fusagasugá",
        "Colombia mencionada en canciones famosas",
        "comerciales colombianos encontrados en TikTok",
        "animales curiosos de Colombia",
        "fotógrafos importantes de Colombia",
        "cuadrillas de San Martín 286",
        "Kid Pambele historia",
        "mejores shows de El Show de las Estrellas",
        "videos raros de rap o reggaetón colombiano",
        "tribus Pasé y Yuri Colombia",
        "Octavio Mesa Agosto Colombia",
        "La Etnia primer álbum de rap colombiano",
        "Heiden Ackerman Colombia",
        "relojes de colombianos famosos",
        "Toma del Palacio de Justicia",
        "cumpleaños Valderrama historia",
        "Jaime Garzón",
        "Valle de las Brujas lugares embrujados Colombia",
        "pornomiseria cine colombiano",
        "momias de San Bernardo Colombia",
        "pueblos desaparecidos o abandonados en Colombia",
        "suicidios curiosos en la historia de Colombia",
    ]
    # Elige un tema al azar en cada corrida
    tema = random.choice(temas_prioritarios)

    prompt = f"""Investiga el tema "{tema}" usando tu búsqueda web. Estoy armando contenido
para @colombia.core, cuenta de Instagram de cultura/historia colombiana con estética de
archivo curado y atemporal (como @hidden.ny o @artifaxing), presentado con gancho corto
tipo infográfico (como @raptv o @dexerto) — no importa si el dato es viejo o nuevo.

REGLAS IMPORTANTES:
- El tema NO necesita ser grande ni amplio. Anécdotas pequeñas y documentables son ideales
  (ejemplo: un parque de piscinas en Bogotá que cerró, el apodo de una unidad militar). Basta
  con una foto/dato y una descripción breve — no hace falta una historia extensa.
- TODO ángulo que propongas tiene que conectar explícitamente con Colombia: una región, un
  pueblo, una persona pública colombiana, o un hecho colombiano específico. Nunca algo
  genérico sin ese gancho local.
- Si encuentras registro fotográfico o de video de apoyo, menciónalo — ayuda mucho al post.

Dame 1-2 ángulos concretos y poco conocidos sobre este tema que sirvan como post. Para cada
uno, usa esta estructura exacta:
📌 [Título sugerido para el post, corto y con gancho]
- Qué encontré: el dato/gancho revelador en 2-4 líneas
- Personajes/lugares clave: nombres, regiones, instituciones involucradas
- Fechas clave: si aplica
- Para buscar multimedia: 2-3 palabras/frases concretas para buscar en Google/YouTube y
  encontrar fotos o videos de apoyo
- Fuente: si la tienes

Sé honesto si no encuentras nada con suficiente ángulo revelador."""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 2500,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
        },
        timeout=240,
    )
    response.raise_for_status()
    data = response.json()
    texto = "".join(block.get("text", "") for block in data["content"] if block.get("type") == "text")
    return f"🗂️ Tema del archivo: {tema}\n\n{texto}"


# ---------------------------------------------------------------------------
# 4. ENVÍO A TELEGRAM
# ---------------------------------------------------------------------------

def enviar_telegram(mensaje):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Telegram limita ~4096 caracteres por mensaje; partimos si hace falta
    max_len = 3500
    partes = [mensaje[i:i + max_len] for i in range(0, len(mensaje), max_len)] or [mensaje]

    for parte in partes:
        r = requests.post(url, data={"chat_id": chat_id, "text": parte, "disable_web_page_preview": True})
        r.raise_for_status()
        time.sleep(1)


# ---------------------------------------------------------------------------
# 5. MAIN
# ---------------------------------------------------------------------------

def main():
    print("Recolectando contenido reciente...")
    items = recolectar_todo()
    print(f"{len(items)} items recolectados. Curando con Claude...")
    reporte_reciente = curar_con_claude(items)

    print("Explorando tema atemporal...")
    reporte_atemporal = explorar_tema_atemporal()

    encabezado = f"📰 Reporte @colombia.core — {datetime.now().strftime('%d/%m/%Y')}\n\n"
    mensaje_final = (
        encabezado
        + "— LO RECIENTE —\n" + reporte_reciente
        + "\n\n— DEL ARCHIVO —\n" + reporte_atemporal
    )
    enviar_telegram(mensaje_final)
    print("Reporte enviado.")


if __name__ == "__main__":
    main()
