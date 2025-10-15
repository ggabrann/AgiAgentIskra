.PHONY: setup deps lint test build ci run

setup:
	@echo "[setup] Подготовьте окружение: установите Codex CLI/IDE и включите MFA."

deps:
	@echo "[deps] Зависимости будут добавлены после распаковки архивов."

lint:
	@echo "[lint] Линтер ещё не настроен. Зафиксируйте это в PR и Decision Log."
	@exit 0

test:
	@echo "[test] Автотесты отсутствуют. Добавьте их в будущих задачах."
	@exit 0

build:
	@echo "[build] Нет сборочного процесса. Обновите при появлении сервисов."
	@exit 0

ci:
	@echo "[ci] CI конвейер не настроен. План см. в README."
	@exit 0

run:
	@echo "[run] Код ещё не разложен. Следуйте чек-листам в AGENTS.md."
