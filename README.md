# VeriqraHQ - Compras estatales Uruguay

Sistema full stack para consultar compras estatales vigentes y anteriores con precios de adjudicacion.

Stack:

- Backend: FastAPI + SQLAlchemy
- Frontend: React/Vite + Tailwind
- Base de datos: PostgreSQL
- Deploy VPS: Nginx + systemd + Certbot

## Fuente oficial

La primera version trabaja con el dataset de ARCE en el Catalogo de Datos Abiertos:

https://catalogodatos.gub.uy/dataset/acce-compras-estatales

Ese conjunto publica las publicaciones realizadas en el sitio web de Compras Estatales, documenta la interfaz XML, incluye codigueras como estados de compra, monedas, incisos, tipos/subtipos de compra, unidades ejecutoras, y documenta RSS para automatizar busquedas.

## Desarrollo local

Backend:

```sh
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8020
```

Frontend:

```sh
cd frontend
npm install
npm run dev
```

URLs locales:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

## Despliegue Hostinger VPS

Dominio objetivo: `test.veriqrahq.pro`.

La guia paso a paso esta en:

```sh
deploy/INSTALL_HOSTINGER.md
```

Archivos de despliegue incluidos:

- `deploy/veriqrahq-api.service`: servicio systemd para FastAPI en `127.0.0.1:8020`
- `deploy/nginx-test.veriqrahq.pro.conf`: Nginx sirviendo `frontend/dist` y proxy `/api`
- `backend/.env.example`: variables de produccion del backend
- `frontend/.env.production.example`: variables de build del frontend
- `scripts/build_frontend.sh`: build del frontend

## Importar datos ARCE

Desde el frontend:

1. Descargue XML/RSS/CSV desde el dataset o desde una busqueda guardada del sitio de Compras Estatales.
2. Use `Importar archivo`, o pegue una URL XML/RSS y pulse `Sincronizar`.
3. Filtre por estado, organismo, procedimiento, proveedor, expediente u objeto.

Desde API:

```sh
curl -F "file=@compras.xml" http://localhost:8000/api/purchases/import
curl -F "url=https://..." http://localhost:8000/api/purchases/sync-url
```

## Endpoints principales

- `GET /health`
- `GET /api/purchases`
- `GET /api/purchases/catalogs`
- `POST /api/purchases/import`
- `POST /api/purchases/sync-url`

## Nota de implementacion

El parser acepta nombres de campos frecuentes en XML/RSS/CSV de compras: expediente/id/guid, objeto/titulo, organismo/inciso/unidad ejecutora, proveedor/adjudicatario, estado, procedimiento/tipo de compra, moneda, monto/precio adjudicado y fechas. La normalizacion es tolerante para permitir trabajar con las codigueras oficiales y con RSS del buscador.
