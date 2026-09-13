#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
for candidate in ./Tools/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [ -x "$candidate" ] && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
        "$candidate" music_library.py
        result=$?
        if [ "$result" -ne 0 ]; then
            read -r -p 'Pulsa Enter para cerrar…' unused
        fi
        exit "$result"
    fi
done
printf 'No se encuentra Python 3.9 o posterior en este Mac. Instala Python desde python.org.\n'
read -r -p 'Pulsa Enter para cerrar…' unused
