#!/bin/bash

# Скрипт для установки tmux

echo "🔧 Проверяю наличие tmux..."

if command -v tmux &> /dev/null; then
    echo "✅ tmux уже установлен"
    tmux -V
else
    echo "📦 Устанавливаю tmux..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install tmux
        else
            echo "❌ Homebrew не найден. Установите tmux вручную:"
            echo "   brew install tmux"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y tmux
        elif command -v yum &> /dev/null; then
            sudo yum install -y tmux
        elif command -v pacman &> /dev/null; then
            sudo pacman -S tmux
        else
            echo "❌ Менеджер пакетов не найден. Установите tmux вручную"
            exit 1
        fi
    else
        echo "❌ Неподдерживаемая ОС. Установите tmux вручную"
        exit 1
    fi
    
    echo "✅ tmux установлен успешно"
    tmux -V
fi

echo ""
echo "🚀 Теперь можно запускать ботов:"
echo "python3 main.py"
