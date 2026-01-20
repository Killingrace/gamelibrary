# Universal Game Library

A Kivy/KivyMD app for tracking a universal game catalog and your personal play progress.

## Requirements

- Python 3.11
- Kivy 3.2.1
- KivyMD 1.2.0

## Installation

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install kivy==3.2.1 kivymd==1.2.0
```

## Run

```sh
python lastProject/main.py
```

## Notes

- The local SQLite database is stored at `lastProject/games.db`.
- Screenshots are read from paths in the `screenshots` field (e.g. `pics/minecraft1.png|pics/minecraft2.png`).
