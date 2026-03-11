#!/bin/bash
# ════════════════════════════════════════════════════════════════
#  setup.sh — первоначальная настройка проекта
# ════════════════════════════════════════════════════════════════
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Discord–Telegram Bridge  Setup Script   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# Проверяем .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠  Файл .env не найден. Копирую .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}❗ ВАЖНО: Откройте .env и заполните все значения перед запуском!${NC}"
    echo ""
fi

# Создаём папку для логов
mkdir -p logs

echo -e "${GREEN}✓ Структура директорий готова${NC}"

# Проверяем Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker не установлен!${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose не установлен!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker и Docker Compose найдены${NC}"
echo ""
echo -e "${YELLOW}Следующие шаги:${NC}"
echo -e "  1. Отредактируйте ${BLUE}.env${NC} — заполните все токены и ID"
echo -e "  2. Запустите: ${GREEN}docker compose up -d${NC}"
echo -e "  3. Проверьте логи: ${GREEN}docker compose logs -f app${NC}"