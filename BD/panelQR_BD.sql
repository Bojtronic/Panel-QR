\set ON_ERROR_STOP on
\ir 00_create_database.sql
\connect panel_qr
\ir 01_create_tables.sql
\ir 02_foreign_keys.sql
\ir 03_seed_data.sql
