# Iskra 4.0 — Canon Merge

Этот PR вносит в репозиторий объединённую "Искру": канон (фазы, состояния, метрики, ритуалы, голоса, символы),
наблюдаемость, тесты, CI и единый менеджмент зависимостей.

## Что внутри
- docs/canon/ (INDEX + чек-лист покрытия)
- src/iskra_core/ (facets, facet_activation_engine, phase_manager, metrics_calculator)
- src/iskra_observability/metrics.py (Prometheus)
- tests/unit/* (Facets/Phases/Metrics)
- pyproject.toml, .pre-commit-config.yaml, .github/workflows/ci.yml

## Заметки по совместимости
- legacy артефакты оставлены либо перенесены в docs/backups.
- API из hybrid сохранён, core из fullstack приоритезирован, phase_manager из telos.

## Следующие шаги
- Подключить реальные грани (Exploration/Integrity/…);
- Добавить semgrep + trivy в CI;
- Сформировать релизные теги и CHANGELOG.
