FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY firmware ./firmware
COPY tools ./tools
COPY tests ./tests

CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
