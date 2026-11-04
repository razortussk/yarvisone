# Cómo poner a funcionar tu reporte de @colombia.core

No necesitas dejar tu computador prendido ni saber programar. Solo sigue estos
pasos una vez y el bot queda corriendo solo, para siempre, gratis (o casi gratis).

## Paso 1 — Crear el bot de Telegram
1. Abre Telegram y busca el usuario **@BotFather**.
2. Escríbele `/newbot` y sigue las instrucciones (te pedirá un nombre y un
   usuario terminado en "bot").
3. Al final te va a dar un **token** — algo como `123456789:ABCdefGhIJKlmNoPQRstuVwXyZ`.
   Guárdalo, lo vas a necesitar.
4. Ahora necesitas tu **Chat ID**: escríbele cualquier mensaje a tu bot recién
   creado, y luego abre en el navegador (reemplazando TU_TOKEN):
   `https://api.telegram.org/botTU_TOKEN/getUpdates`
   Ahí vas a ver un número en `"chat":{"id": ...}` — ese es tu Chat ID.

## Paso 2 — Crear tu cuenta de API de Anthropic
1. Ve a **console.anthropic.com** y crea una cuenta (es distinta a tu cuenta de
   Claude.ai normal).
2. En la sección de Billing, carga crédito prepago — con $5 USD tienes de sobra
   para meses de este bot.
3. Ve a la sección de "API Keys" y crea una clave nueva. Guárdala — solo se
   muestra una vez.

## Paso 3 — Subir este proyecto a GitHub
1. Crea una cuenta gratis en **github.com** si no tienes.
2. Crea un repositorio nuevo (puede ser privado) — por ejemplo
   `colombia-core-bot`.
3. Sube TODOS los archivos que te di (`reporte.py`, `requirements.txt`, y la
   carpeta `.github/workflows/reporte.yml` con esa misma estructura de
   carpetas). Puedes arrastrarlos directamente en la interfaz web de GitHub
   ("Add file" → "Upload files"), no necesitas usar la terminal.

## Paso 4 — Configurar tus claves secretas en GitHub
Estas claves NUNCA van escritas en el código, van guardadas de forma segura
en GitHub:
1. En tu repositorio, ve a **Settings → Secrets and variables → Actions**.
2. Crea 3 "New repository secret":
   - `TELEGRAM_BOT_TOKEN` → el token del Paso 1
   - `TELEGRAM_CHAT_ID` → el número del Paso 1
   - `ANTHROPIC_API_KEY` → la clave del Paso 2

## Paso 5 — Probarlo
1. Ve a la pestaña **Actions** de tu repositorio.
2. Selecciona el workflow "Reporte colombia.core".
3. Dale click a "Run workflow" para probarlo manualmente ahora mismo (no
   tienes que esperar al lunes).
4. En un minuto o dos deberías recibir el mensaje en tu Telegram.

## Después de esto
No vuelves a tocar nada. El robot corre solo lunes, miércoles y viernes a las
7am hora Colombia, y te manda el reporte. Si algún día quieres cambiar los
días/hora, se ajusta en el archivo `.github/workflows/reporte.yml` (línea del
`cron`) — puedo ayudarte a ajustarlo cuando quieras.

## Si algo no funciona
Copia el error que veas en la pestaña "Actions" (ahí queda el log de cada
corrida) y pégamelo — lo resolvemos juntos.
