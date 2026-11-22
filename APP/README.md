# Panel QR

Aplicación monolítica en Flask para consultar paneles eléctricos por código,
administrar usuarios y permisos, conservar versiones documentales y auditar
acciones. La interfaz usa plantillas HTML de Flask y un único CSS compartido.
El escáner usa `BarcodeDetector` cuando el navegador lo soporta; la búsqueda
manual siempre está disponible.

## Estructura

- `panelqr/`: fábrica de aplicación, vistas, servicios de acceso, conexión SQL,
  plantillas y recursos estáticos.
- `storage/demo/`: archivos de muestra referenciados por los datos iniciales.
- `storage/uploads/`: destino de archivos nuevos. No debe servirse como carpeta
  estática; se entregan por una ruta que comprueba sesión y autorización.
- `tests/`: pruebas unitarias y pruebas de la interfaz HTTP.
- `../BD/`: creación de la base, restricciones foráneas y datos iniciales.

Las responsabilidades están separadas dentro de un solo proceso web. Se puede
agregar una capa de servicio o un blueprint por módulo sin cambiar el esquema
de despliegue. Las consultas SQL son parametrizadas y el acceso a documentos
se valida en el servidor.

## Requisitos

- Python 3.10 o posterior.
- PostgreSQL 13 o posterior.
- HTTPS para el despliegue; los navegadores requieren un contexto seguro para
  habilitar la cámara.

## Instalación local

Desde la raíz del repositorio, crea la base y sus datos de ejemplo. Para
Windows con PgAdmin 4, sigue la guía de [BD/README.md](../BD/README.md):
crea `panel_qr` desde la interfaz y ejecuta los scripts de estructura,
relaciones y datos en orden. Para Linux:

```sh
psql -U postgres -d postgres -f BD/panelQR_BD.sql
```

El usuario que ejecute el script debe poder crear bases de datos. El archivo
maestro crea `panel_qr`, se conecta y ejecuta en orden `01_create_tables.sql`,
`02_foreign_keys.sql` y `03_seed_data.sql`.

Configura un rol de aplicación con permisos sobre la base y el esquema
`public`. No uses el usuario superadministrador de PostgreSQL para ejecutar la
aplicación. Luego:

```sh
psql -U postgres -d panel_qr
```

En Query Tool de PgAdmin, conectado a `panel_qr`, o en una sesión de `psql`,
crea el usuario de aplicación. Sustituye la contraseña y no la guardes en el
repositorio:

```sql
CREATE ROLE panelqr LOGIN PASSWORD 'CAMBIAR_PASSWORD';
GRANT CONNECT ON DATABASE panel_qr TO panelqr;
GRANT USAGE ON SCHEMA public TO panelqr;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO panelqr;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO panelqr;
```

Si usas `psql`, sal de la consola con `\q` después de ejecutar las sentencias.

### Instalar y arrancar en Windows (PowerShell)

Abre PowerShell en la carpeta del proyecto y ejecuta:

```powershell
cd APP
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DATABASE_URL = "postgresql://panelqr:CAMBIAR_PASSWORD@localhost/panel_qr"
$env:SECRET_KEY = (python -c "import secrets; print(secrets.token_hex(32))")
$env:UPLOAD_FOLDER = "$PWD\storage"
flask --app run.py run --debug
```

Si PowerShell bloquea la activación del entorno virtual, permite scripts para
el usuario actual con `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y
vuelve a activar el entorno.

### Instalar y arrancar en Linux

Desde la raíz del repositorio:

```sh
cd APP
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export DATABASE_URL='postgresql://panelqr:CAMBIAR_PASSWORD@localhost/panel_qr'
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export UPLOAD_FOLDER="$PWD/storage"
flask --app run.py run --debug
```

En ambos sistemas, abre `http://127.0.0.1:5000`. El comando anterior inicia el
servidor de desarrollo; no lo uses como servidor de producción. Para probar
el escáner con cámara se requiere HTTPS o `localhost` y un navegador compatible.

### Cuentas de demostración

Las tres cuentas creadas por el script SQL usan la contraseña
`PanelQR2026!`:

- `admin@panelqr.local` — administrador.
- `tecnico1@panelqr.local` — acceso al grupo Edificio principal.
- `tecnico2@panelqr.local` — acceso al grupo Taller.

Cambia estas contraseñas y la clave de sesión antes de cualquier uso real.

## Pruebas

```sh
cd APP
python -m unittest discover -s tests -v
```

Las pruebas unitarias no requieren una base PostgreSQL. Las pruebas de extremo
a extremo con persistencia deben ejecutarse contra una base aislada que haya
recibido los tres scripts SQL:

```sh
TEST_DATABASE_URL='postgresql://panelqr:CAMBIAR_PASSWORD@localhost/panel_qr_test' \
  python -m unittest discover -s tests -v
```

## Seguridad y alcance

- Las contraseñas se guardan como PBKDF2-HMAC-SHA256 con 600 000 iteraciones.
- Las solicitudes que modifican datos requieren token CSRF.
- La sesión usa cookies HttpOnly y SameSite=Lax; configura una clave secreta
  estable y `SESSION_COOKIE_SECURE=true` detrás de HTTPS.
- La autorización se comprueba en el backend para paneles y cada versión de
  documento. El directorio de archivos no es público.
- Se limitan los archivos a PDF, PNG y JPEG y a 20 MB.
- Un navegador no puede impedir capturas de pantalla. El control de acceso y la
  auditoría reducen exposición, pero no sustituyen políticas organizacionales.
- El repositorio local es una implementación inicial; `repositorio` permite
  integrar almacenamiento externo en una fase posterior.

Los archivos de muestra se sirven desde la carpeta empaquetada aunque
`UPLOAD_FOLDER` apunte a otra ubicación. Los archivos reales subidos por la
aplicación reciben un SHA-256 calculado al almacenarse.
