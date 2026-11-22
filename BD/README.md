# Base de datos Panel QR

La base de datos almacena los datos de usuarios, roles, permisos, paneles,
grupos, documentos, historial de versiones y auditoría. Los archivos se guardan
fuera de la base y se relacionan desde `documento_version`.

El motor elegido es **PostgreSQL**. Puedes crear y cargar la base de dos formas:

- **PgAdmin 4**, recomendado para el flujo habitual en Windows.
- **`psql`**, una alternativa desde terminal, útil en Linux y en automatización.

Los scripts de inicialización son para una base vacía. No los ejecutes sobre una
base que ya contenga información: no son migraciones y recrear datos no está
contemplado.

## Qué hace cada script

1. `00_create_database.sql`: crea la base `panel_qr`. Se ejecuta únicamente con
   `psql`, porque contiene la creación de la base.
2. `01_create_tables.sql`: crea las tablas y columnas en la base
   `panel_qr`.
3. `02_foreign_keys.sql`: añade claves foráneas e índices.
4. `03_seed_data.sql`: inserta los roles, permisos, cuentas, paneles y
   documentos de demostración.
5. `panelQR_BD.sql`: archivo maestro para `psql`; ejecuta los pasos anteriores
   en orden.

## Opción A: PgAdmin 4 en Windows

### 1. Instalar y registrar PostgreSQL

Instala PostgreSQL para Windows, que incluye PgAdmin 4, o instala PgAdmin 4
para conectarte a un servidor PostgreSQL existente. Abre PgAdmin y registra o
selecciona el servidor utilizando el host, puerto y credenciales configurados
durante la instalación (el puerto por defecto es `5432`).

### 2. Crear la base con la interfaz gráfica

1. En el árbol del servidor, pulsa con el botón derecho **Databases**.
2. Selecciona **Create → Database…**.
3. Escribe `panel_qr` como nombre y elige el propietario indicado por quien
   administra PostgreSQL. Pulsa **Save**.
4. Abre `panel_qr` en el árbol, selecciónala y abre **Tools → Query Tool**.
5. Ejecuta los scripts **en este orden**:
   - `01_create_tables.sql`
   - `02_foreign_keys.sql`
   - `03_seed_data.sql`

En cada paso, puedes abrir el archivo desde Query Tool o copiar su contenido y
ejecutarlo con **Execute/Refresh (F5)**. Verifica que Query Tool esté conectado
a la base `panel_qr` antes de ejecutar.

> No ejecutes `00_create_database.sql` desde Query Tool: la base ya se creó
> desde la interfaz. El archivo maestro `panelQR_BD.sql` sí está pensado para
> `psql` y usa instrucciones propias de ese cliente, como `\connect` y `\ir`.

### 3. Verificar los datos

En el árbol de PgAdmin, expande **Schemas → public → Tables** y refresca la
lista. Para comprobar los registros, abre Query Tool conectado a `panel_qr` y
ejecuta, por ejemplo:

```sql
SELECT codigo_qr, nombre, estado FROM panel ORDER BY codigo_qr;
SELECT email, activo FROM usuario ORDER BY email;
```

## Opción B: Linux con `psql`

Instala PostgreSQL y el cliente `psql` desde los paquetes de tu distribución y
asegúrate de que el servicio esté en ejecución. Desde la raíz del proyecto:

```sh
psql -U postgres -d postgres -f BD/panelQR_BD.sql
```

El usuario indicado con `-U` debe tener permiso para crear bases. El archivo
maestro crea `panel_qr`, se conecta a ella y luego ejecuta los scripts de
tablas, llaves foráneas y datos iniciales. Según la configuración local,
`psql` podría solicitar una contraseña o requerir conexión por socket.

También se pueden ejecutar por separado desde la raíz, conservando el orden:

```sh
psql -U postgres -d postgres -f BD/00_create_database.sql
psql -U postgres -d panel_qr -f BD/01_create_tables.sql
psql -U postgres -d panel_qr -f BD/02_foreign_keys.sql
psql -U postgres -d panel_qr -f BD/03_seed_data.sql
```

## Cuenta de aplicación

La aplicación debe conectarse con un usuario PostgreSQL de propósito
específico, no con la cuenta superadministradora. Después de crear las tablas,
un administrador puede abrir Query Tool en PgAdmin o `psql` conectado a
`panel_qr` y ejecutar lo siguiente, sustituyendo la contraseña:

```sql
CREATE ROLE panelqr LOGIN PASSWORD 'CAMBIAR_PASSWORD';
GRANT CONNECT ON DATABASE panel_qr TO panelqr;
GRANT USAGE ON SCHEMA public TO panelqr;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO panelqr;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO panelqr;
```

Si el rol ya existe, cambia su contraseña con `ALTER ROLE` en lugar de volver
a ejecutar `CREATE ROLE`. Consulta [APP/README.md](../APP/README.md) para
configurar la conexión de la aplicación.

## Datos de demostración

Cada tabla recibe al menos dos registros para que sea posible probar el flujo.
Las cuentas son:

- `admin@panelqr.local`
- `tecnico1@panelqr.local`
- `tecnico2@panelqr.local`

Las tres usan `PanelQR2026!`. Cámbialas antes de usar información real.

## Normalización

El modelo está diseñado hasta tercera forma normal:

- **1FN:** cada columna almacena un valor por fila; las asignaciones múltiples
  se representan como filas separadas.
- **2FN:** las tablas de relación (`usuario_rol`, `rol_permiso`, `usuario_panel`
  y `usuario_grupo_panel`) usan claves primarias compuestas; sus atributos
  dependen de la clave completa. Las demás tablas usan una clave primaria
  simple.
- **3FN:** nombres de roles, permisos, grupos, tipos documentales y
  repositorios viven en sus catálogos. Las entidades guardan sus claves, no
  copias de esas descripciones. Cada versión se separa de su documento y la
  auditoría se registra como eventos independientes.

Las claves foráneas preservan la integridad referencial y el índice parcial
`uq_documento_version_actual` evita asignar más de una versión vigente a un
documento.
