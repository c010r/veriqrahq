# Despliegue en Hostinger VPS sin Docker

Dominio objetivo: `test.veriqrahq.pro`

## 1. Paquetes del servidor

Ubuntu/Debian:

```sh
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip nodejs npm postgresql postgresql-contrib nginx certbot python3-certbot-nginx
```

## 2. DNS

En Hostinger, apunte el registro `A` de `test.veriqrahq.pro` a la IP publica del VPS.

## 3. Base de datos

```sh
sudo -u postgres psql
```

```sql
CREATE USER veriqra WITH PASSWORD 'CAMBIAR_PASSWORD';
CREATE DATABASE veriqra OWNER veriqra;
\q
```

## 4. Codigo

Ubique el proyecto en:

```sh
sudo mkdir -p /var/www/veriqrahq
sudo chown -R $USER:www-data /var/www/veriqrahq
```

Copie o haga `git clone` del proyecto dentro de `/var/www/veriqrahq`.

## 5. Backend FastAPI

```sh
cd /var/www/veriqrahq/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

Edite `DATABASE_URL` con la password real.

```sh
sudo cp /var/www/veriqrahq/deploy/veriqrahq-api.service /etc/systemd/system/veriqrahq-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now veriqrahq-api
sudo systemctl status veriqrahq-api
```

## 6. Frontend React/Vite

```sh
cd /var/www/veriqrahq/frontend
cp .env.production.example .env.production
npm install
npm run build
```

## 6.1 Carga inicial ARCE

La carga historica desde el 01/01/2024 hasta la fecha se ejecuta desde el servidor, no desde la interfaz web:

```sh
cd /var/www/veriqrahq/backend
. .venv/bin/activate
PYTHONPATH=/var/www/veriqrahq/backend nohup python scripts/load_arce_history.py > /var/log/veriqrahq-arce-history.log 2>&1 &
```

El progreso queda visible en `/api/purchases/sync-status` y en la pantalla principal.

`VITE_API_BASE` puede quedar vacio porque Nginx sirve frontend y API bajo el mismo dominio.

## 7. Nginx

```sh
sudo cp /var/www/veriqrahq/deploy/nginx-test.veriqrahq.pro.conf /etc/nginx/sites-available/test.veriqrahq.pro
sudo ln -s /etc/nginx/sites-available/test.veriqrahq.pro /etc/nginx/sites-enabled/test.veriqrahq.pro
sudo nginx -t
sudo systemctl reload nginx
```

## 8. SSL

```sh
sudo certbot --nginx -d test.veriqrahq.pro
```

## 9. Verificacion

```sh
curl -i https://test.veriqrahq.pro/health
curl -i https://test.veriqrahq.pro/api/purchases
```

La aplicacion queda disponible en:

https://test.veriqrahq.pro
