# Akyl Cheshmesi Docker Deploy Package

## Что внутри
- `Dockerfile.django` — контейнер Django/Gunicorn/Celery/workers
- `Dockerfile.go` — контейнер Go realtime
- `docker-compose.prod.yml` — production stack
- `deploy/nginx/conf.d/default.conf` — Nginx reverse proxy + `/` + `/privacy`
- `deploy/django-entrypoint.sh` — entrypoint с migrate/collectstatic
- `env/.env.prod.example` — шаблон production env
- `web/index.html`, `web/privacy.html` — заглушки, замени своими файлами
- `.github/workflows/deploy.yml` — пример GitHub Actions deploy по SSH

## Как это работает
- `/` -> статический `web/index.html`
- `/privacy` -> статический `web/privacy.html`
- `/api/*` -> Django
- `/admin/*` -> Django admin
- `/ws` -> Go websocket
- `/static/*` и `/media/*` -> Nginx из volumes

## Что заменить перед запуском
1. Скопируй `env/.env.prod.example` в `env/.env.prod`
2. Заполни секреты
3. Замени `web/index.html` и `web/privacy.html` своими файлами
4. Если реальный домен `akyl-cheshmesi.ru`, а не `aky-cheshmesi.ru`, замени его в:
   - `deploy/nginx/conf.d/default.conf`
   - `env/.env.prod`

## Первый запуск на Ubuntu
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable docker
sudo systemctl start docker

sudo mkdir -p /srv/akyl-cheshmesi
sudo chown -R $USER:$USER /srv/akyl-cheshmesi
cd /srv/akyl-cheshmesi
# сюда скопируй репозиторий

docker compose --env-file env/.env.prod -f docker-compose.prod.yml up -d --build
```

## Обновление
```bash
git pull
docker compose --env-file env/.env.prod -f docker-compose.prod.yml up -d --build
```

## Проверка
```bash
docker compose --env-file env/.env.prod -f docker-compose.prod.yml ps
docker compose --env-file env/.env.prod -f docker-compose.prod.yml logs -f django
docker compose --env-file env/.env.prod -f docker-compose.prod.yml logs -f go-realtime
```
