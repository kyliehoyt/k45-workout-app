# k45-workout-app

A personal workout companion app that helps you follow F45-style workouts outside of the studio, including apartment-gym-friendly modifications.

This project includes:
- A Python data pipeline to ingest and parse weekly F45 workouts
- A structured workout database
- (Planned) Android application for guided workout execution with timers and tracking


## Purpose

I got the chance to try a few F45 workouts while on vacation and fell in love with the class style, but there are no F45 studios close to where I live. :(

This app aims to:
- Import weekly F45 workouts from community sources
- Let users browse workouts by category
- Provide a guided workout experience (timers, pods, exercises)
- Track completed workouts and history
- Remove any exercises I don't like and add my favorites that are missing (hence k45, for Kylie)
- Suggest equipment substitutions for apartment or home gyms


## Developer Setup
This project uses uv for Python dependency management.

Install uv (docs: https://docs.astral.sh/uv/)
```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```
Install dependencies
```bash
uv sync
```

## Formatting/Linting
Format code and run fast lint checks using Ruff:
```bash
uv run ruff format
uv run ruff check
```

Run Pylint (on a directory) for idiomatic naming and stricter style checks:
```bash
uv run pylint data_acquisition/
```

## Unit Testing
Write and run unit tests with pytest:
```bash
uv run pytest path_to_tests/
uv run pytest path_to_test_file.py
uv run pytest path_to_test_file.py::test_function
```

## Project Structure
```text
k45-workout-app/
│
├── src/                        # Python source and related data
    ├── data/                   # Raw + processed workout data
    ├── data_acquisition/       # Python data ingestion (from online sources)
    └── tests/                  # pytest unit tests
├── android/                    # Future android app
├── pyproject.toml
├── uv.lock
└── README.md
```
