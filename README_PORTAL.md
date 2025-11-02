# AgiAgentIskra — Portal

## Архитектура
- **core**: грань → активация → фаза → ритуал → ответ
- **observability**: Prometheus (счётчики/гистограмма), подготовка к OpenTelemetry
- **security**: semgrep/trivy в CI

## Карта
- src/iskra_core/: facets, facet_activation_engine, phase_manager, metrics_calculator
- src/iskra_observability/metrics.py
- docs/canon/INDEX.md, docs/ISKRA_CANON_CHECKLIST.md
- tests/unit/*
- .github/workflows/ci.yml, security.yml
- Dockerfile, docker-compose.yml

## Запуск
```bash
pre-commit install && pre-commit run --all-files
pytest -q
docker compose up --build
```
