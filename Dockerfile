FROM python:3.13-alpine AS builder

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev

RUN python3 -m venv $VIRTUAL_ENV
RUN pip install --upgrade pip

COPY ./requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.13-alpine AS runner

LABEL authors="Pashok11"

RUN apk add --no-cache libpq

COPY --from=builder /opt/venv /opt/venv

ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV APP=/app

RUN mkdir $APP
WORKDIR $APP

# Копируем код
COPY ./static/ ./static/
COPY ./start_app.py ./
COPY ./src/ ./src/
# Копируем .env внутрь контейнера
COPY ./.env ./

ENTRYPOINT ["python", "start_app.py"]