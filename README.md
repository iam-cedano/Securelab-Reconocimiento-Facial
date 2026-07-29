# Securelab: captura facial con ESP32-CAM

Prototipo que consulta una cola de capturas en Supabase. Cuando
`reconocimientos_faciales` recibe una fila con
`resultado = 'captura_requerida'`, un ESP32-CAM reclama el trabajo, toma una
foto JPEG y la sube al bucket privado `capturas-faciales`.

El reconocimiento facial queda fuera de este alcance. Al terminar una carga,
la fila cambia a `captura_completada` y `url_foto` contiene la ruta del objeto.

## Arquitectura y seguridad

El ESP32 no recibe una `service_role`/secret key de Supabase. Se comunica con
la Edge Function `camera-capture` usando un secreto específico del dispositivo.
La función:

1. reclama de forma atómica la captura pendiente más antigua;
2. recibe un JPEG de hasta 1 MiB;
3. lo sube con un nombre UUID;
4. actualiza `reconocimientos_faciales.url_foto`.

El bucket es privado porque las fotografías faciales son datos sensibles. Se
pueden ver desde **Storage > capturas-faciales** en el dashboard de Supabase.
Una aplicación futura debe generar URLs firmadas para mostrarlas fuera del
dashboard.

## Ejecutar en Docker

Docker ejecuta las pruebas de la lógica Python y un simulador de cámara. No
emula el periférico de cámara del ESP32.

```bash
docker compose build
docker compose run --rm test
```

Para probar una captura real contra Supabase:

```bash
cp .env.example .env
# Editar .env con la URL de la función y el mismo DEVICE_API_TOKEN del servidor.
docker compose run --rm simulator
```

El simulador queda en ejecución y consulta la función cada
`POLL_INTERVAL_SECONDS` segundos. Cuando no hay filas pendientes, mantiene la
salida en silencio e imprime `No pendient row were found in the last ten minutes`
solo una vez cada diez minutos. Para ejecutar un único ciclo y salir, definir
`RUN_ONCE=true`.

Si no se define `PHOTO_FILE`, el simulador envía un JPEG válido de 1x1. Para
verificar una fotografía propia, montarla dentro del contenedor:

```bash
docker compose run --rm \
  -v "$PWD/photo.jpg:/photo.jpg:ro" \
  -e PHOTO_FILE=/photo.jpg \
  simulator
```

## Preparar Supabase

Se requiere Supabase CLI autenticado y vinculado al proyecto:

```bash
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
supabase secrets set DEVICE_API_TOKEN="$(openssl rand -hex 32)"
supabase functions deploy camera-capture
```

Copiar el mismo token a `.env` para el simulador y a
`firmware/config.py` para el dispositivo. No usar una publishable key ni una
service-role key como `DEVICE_API_TOKEN`.

`DEVICE_API_TOKEN` es el secreto propio del dispositivo y debe coincidir con el
secreto configurado en la Edge Function. `AUTHORIZATION_TOKEN` es distinto: solo
se usa como `Authorization: Bearer ...` cuando Supabase exige un JWT o una
publishable/anon key antes de ejecutar la función. Si aparece
`UNAUTHORIZED_NO_AUTH_HEADER`, falta `AUTHORIZATION_TOKEN` o la función no fue
desplegada con `verify_jwt = false`. Si aparece `unauthorized device`, la
función sí se ejecutó, pero `DEVICE_API_TOKEN` no coincide con el secreto del
servidor.

La migración:

- agrega estado de reclamación y reintentos a
  `reconocimientos_faciales`;
- crea una función SQL de reclamación con `FOR UPDATE SKIP LOCKED`;
- crea el bucket privado `capturas-faciales`, limitado a JPEG de 1 MiB.

Las reclamaciones que no terminan vuelven a estar disponibles después de dos
minutos.

La función no crea filas en `reconocimientos_faciales`: primero reclama una fila
existente con `resultado = 'captura_requerida'` y `url_foto` vacío, y después
actualiza esa misma fila. La carga de la fotografía sí crea un objeto nuevo en
Storage, visible en el bucket `capturas-faciales`.

## Instalar en el ESP32-CAM

Objetivo probado por diseño: **AI-Thinker ESP32-CAM con OV2640 y PSRAM**. El
MicroPython oficial genérico no incluye el módulo `camera`; se necesita una
compilación de MicroPython para ESP32 que exponga la API `camera.init`,
`camera.capture`, `camera.framesize` y `camera.quality`.

1. Flashear una compilación compatible con cámara y PSRAM.
2. Copiar `firmware/config.example.py` a `firmware/config.py` y completar Wi-Fi,
   URL, token e identificador único del dispositivo.
3. Copiar estos archivos a la raíz del ESP32:

   ```text
   config.py
   capture_client.py
   esp32_camera.py
   micropython_transport.py
   main.py
   ```

4. Reiniciar el dispositivo. `main.py` consulta cada cinco segundos por
   defecto.

La configuración usa QVGA y calidad JPEG 12 para reducir presión de memoria.
Si la compilación de cámara elegida utiliza otro nombre de API o el hardware no
es AI-Thinker, adaptar únicamente `firmware/esp32_camera.py`.

## Estructura

```text
firmware/                 Código compatible con MicroPython
supabase/functions/       Gateway HTTP del ESP32
supabase/migrations/      Cola y bucket de capturas
tools/simulate_device.py  Cámara simulada para CPython
tests/                    Pruebas sin dependencias externas
```
