
Модуль публикаций (VK, Telegram, Telegraph)
===========================================

0) ОБЩИЙ ОБЗОР
-------------------------------------------
Модуль делает два типа задач:

A. RSS-флоу
1) Берёт строки из вкладки RSS, где Status = "Revised".
2) Публикует большую версию (GPT Post) с картинкой (Image URL) в Telegraph, записывает ссылку в Telegraph Link.
3) Берёт маленькую версию (Short Post), добавляет в конец "\n\nЧитать подробнее: {Telegraph Link}".
4) Публикует короткую версию + картинку (Image URL) в VK и Telegram.
5) Сохраняет ссылки публикаций в VK Post Link и TG Post Link.
6) Проставляет Status = "Published".

B. Точечные флоу
- Вкладка VK: обрабатывает строки со Status = "Revised", публикует Title + Content + Image URL в VK, сохраняет ссылку в Post Link, ставит Status = "Published".
- Вкладка Setka: обрабатывает строки со Status = "Revised", публикует Title + Content + Image URL в Telegram, сохраняет ссылку в Post Link, ставит Status = "Published".

1) GOOGLE SHEETS
-------------------------------------------
Sheet ID: 1bjJiP24WnkierEFqZy00Hw9kSR4ESmXgVetrBeTULnU
Вкладки: RSS, VK, Setka

RSS:
  Date — дата материала
  Source — источник
  Title — заголовок
  Link — оригинальная ссылка
  Summary — краткое описание
  Short Post — короткая версия для VK/TG
  GPT Post Title — заголовок для Telegraph
  GPT Post — длинная версия для Telegraph
  Image URL — картинка
  Image Source — источник картинки
  Score — приоритет
  Status — строки со значением "Revised" подлежат обработке, после публикации меняется на "Published"
  Notes — текст ошибки (заполняется при неудаче)
  Telegraph Link — ссылка на страницу Telegraph
  VK Post Link — ссылка на пост VK
  TG Post Link — ссылка на пост Telegram

VK:
  Title, Content, Image URL, Status, Status Dzen, Iteration, Publish Note, Lock, Post Link
  Обработка только для Status = "Revised", после успешной публикации Status = "Published", Post Link заполняется ссылкой на стену, Publish Note очищается.

Setka:
  Title, Content, Image URL, Status, Status Dzen, Iteration, Publish Note, Lock, Post Link
  Обработка только для Status = "Revised", после успешной публикации Status = "Published", Post Link заполняется ссылкой на Telegram, Publish Note очищается.

VK:
  Title, Content, Image URL, VK Post Link, Status

Setka:
  Title, Content, Image URL, Post Link, Status

2) TELEGRAPH (Telegra.ph API)
-------------------------------------------
Если TELEGRAPH_ACCESS_TOKEN нет — создать через createAccount:
  short_name="Mark"
  author_name="Марк Аборчи / AI и Автоматизация"
  author_url="https://t.me/aborchi_m"

createPage параметры:
  title — Title или первые 100 символов GPT Post
  author_name, author_url — как выше
  content — массив JSON-нодов, включая картинку и текст параграфами.

На выходе: url → Telegraph Link.

3) VK (сообщество)
-------------------------------------------
Нужен VK_USER_ACCESS_TOKEN с правами wall,photos,offline и доступом к нужной группе.

Загрузка фото:
1) photos.getWallUploadServer(group_id)
2) POST на upload_url (multipart, поле photo)
3) photos.saveWallPhoto(group_id) → owner_id, id

Публикация:
wall.post(owner_id=-group_id, from_group=1, message, attachments=photo{owner_id}_{id})
Ссылка: https://vk.com/wall-{group_id}_{post_id} → VK Post Link

4) TELEGRAM (канал, bot → admin)
-------------------------------------------
Нужен TELEGRAM_BOT_TOKEN.
Канал должен иметь username (@channel).

sendPhoto:
  chat_id=@channel
  photo=Image URL
  caption=текст поста + "\n\nЧитать подробнее: {Telegraph Link}"
  parse_mode="HTML"
caption ≤ 1024 символов.

Ссылка: https://t.me/<channel>/<message_id> → Post Link

5) РАСПИСАНИЕ ПУБЛИКАЦИЙ
-------------------------------------------
RSS: публикации выполняются ежедневно в 08:00 и 20:00 (мск).
VK/Setka: публикации выполняются в 18:00 (мск) только в дни, перечисленные в переменных окружения `VK_PUBLISH_DAYS`, `SETKA_PUBLISH_DAYS` (формат — `mon,tue,...`).

6) СБОРКА ТЕКСТА RSS
-------------------------------------------
Short Post + "\n\nЧитать подробнее >". Перед публикацией сервис удаляет из исходного текста хвостовой фрагмент "Читать подробнее > ..." (если редактор добавил его вручную), чтобы избежать дублирования. В VK используется сокращённая ссылка (`utils.getShortLink` → `vk.cc/...`) с форматом `Читать подробнее > vk.cc/...`. В Telegram — HTML ссылка `<a href="...">Читать подробнее &gt;</a>`. Поле `Short Post` в таблице не изменяется.

7) ОБРАБОТКА VK/SETKA
-------------------------------------------
VK (Status = "Revised"): Title + Content → wall.post (owner_id=-group_id) с Image URL → Post Link, Status=Published
Setka (Status = "Revised"): Title + Content → sendPhoto(Image URL + caption) → Post Link, Status=Published

8) ОШИБКИ, ЛОГИ, РЕТРАИ
-------------------------------------------
2 повтора (всего 3 попытки), экспоненциальная пауза.
Логирование в stdout (JSON), писать id строки, вкладку, результат.
Ошибки в Notes (RSS) и Publish Note (VK/Setka), статус не меняется.

9) ENV
-------------------------------------------
GOOGLE_SHEET_ID=1bjJiP24WnkierEFqZy00Hw9kSR4ESmXgVetrBeTULnU
GOOGLE_SERVICE_ACCOUNT_JSON=/app/sa.json
TELEGRAPH_ACCESS_TOKEN=
TELEGRAPH_AUTHOR_NAME=Марк Аборчи / AI и Автоматизация
TELEGRAPH_AUTHOR_URL=https://t.me/aborchi_m
VK_USER_ACCESS_TOKEN=
VK_GROUP_ID=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHANNEL_USERNAME=aborchi_m
VK_PUBLISH_DAYS=
SETKA_PUBLISH_DAYS=
LOG_LEVEL=INFO

10) DOCKER
-------------------------------------------
Dockerfile:
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y ca-certificates curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY sa.json /app/sa.json
COPY . /app
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "publisher.run"]

requirements.txt:
gspread
google-auth
requests
python-dotenv
pytz
tenacity

docker-compose.yml:
version: "3.9"
services:
  publisher:
    build: .
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs

10) СТРУКТУРА КОДА
-------------------------------------------
/publisher
  /gs/sheets.py
  /vk/client.py
  /tg/client.py
  /telegraph/client.py
  /core/logger.py
  /core/retry.py
  run.py

11) ПСЕВДОКОД
-------------------------------------------
RSS:
  read RSS rows → create telegraph → append short + link → post VK + TG → write URLs → set Published

VK:
  read VK rows → wall.post → write link → Published

Setka:
  read Setka rows → sendPhoto → write link → Published

12) ПОДГОТОВКА
-------------------------------------------
1) Сервис-аккаунт Google с правами редактирования.
2) VK Access Token (wall, photos, offline).
3) Telegram Bot (admin в канале).
4) Telegraph access_token (или авто-создание).
