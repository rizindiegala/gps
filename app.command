#!/bin/bash
cd "$(dirname "$0")" || exit 1

PYTHON=""
for candidate in "env/bin/python3" "env/bin/python"; do
    if [ -x "$candidate" ]; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Ambiente Python non trovato."
    echo
    echo "Esegui prima l'updater 'Aggiorna GPS' in questa cartella,"
    echo "poi riprova ad avviare GPS."
    echo
    read -n 1 -s -r -p "Premi un tasto per chiudere."
    exit 1
fi

exec "$PYTHON" app.py
