PYTHON ?= python

.PHONY: run dev test lint format bot

run:
	$(PYTHON) start.py

dev:
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest -q

lint:
	$(PYTHON) -m py_compile backend/main.py backend/api/services.py backend/api/chat.py

format:
	@echo "No formatter configured yet"

bot:
	$(PYTHON) telegram_bot/bot.py
