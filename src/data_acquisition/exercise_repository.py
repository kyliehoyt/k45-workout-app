"""File-backed repository for canonical Exercise records."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import json
import re

from data_acquisition.models.equipment import Equipment, EquipmentOption
from data_acquisition.models.exercise import Exercise, MuscleGroup
from data_acquisition.workout_text_parser import WorkoutTextParser


class ExerciseRepository:
    """Store exercises as JSON files keyed by normalized, equipment-free names."""

    EQUIPMENT_ALIASES = {
        "activation band": "activation band",
        "barbell": "barbell",
        "balance trainer": "balance trainer",
        "deadball": "deadball",
        "double kb": "kettlebell",
        "dumbbell": "dumbbell",
        "dumbbells": "dumbbell",
        "kettlebell": "kettlebell",
        "olympic barbell": "barbell",
        "plate": "plate",
        "plyo box": "box",
        "power band": "power band",
        "revo": "revo bar",
        "sandbag": "sandbag",
        "single kb": "kettlebell",
        "soft box": "box",
        "softbox": "box",
        "suspension trainer": "suspension trainer",
        "ybell": "ybell",
    }
    EQUIPMENT_PATTERN = re.compile(
        rf"^({'|'.join(re.escape(alias) for alias in sorted(EQUIPMENT_ALIASES, key=len, reverse=True))})\b\s*",
        re.IGNORECASE,
    )
    NUMBERED_EXERCISE_PATTERN = re.compile(r"^\d+\.\s*(.+)$")

    def __init__(self, exercise_dir: str | Path):
        self.exercise_dir = Path(exercise_dir)
        self.exercise_dir.mkdir(parents=True, exist_ok=True)

    def get_exercise_by_name(self, exercise_name: str) -> Exercise | None:
        """Return an existing exercise matching the raw or canonical name."""
        canonical_name, _ = self.normalize_exercise_name(
            exercise_name)
        path = self._path_for_name(canonical_name)
        if not path.exists():
            return None
        return self._exercise_from_dict(json.loads(path.read_text(encoding="utf-8")))

    def get_or_create_exercise(self, exercise_name: str) -> Exercise:
        """Return an existing exercise or create one from a raw source name."""
        canonical_name, _ = self.normalize_exercise_name(
            exercise_name)
        path = self._path_for_name(canonical_name)
        if path.exists():
            exercise_dict = json.loads(path.read_text(encoding="utf-8"))
            self._merge_source_name(exercise_dict, exercise_name)
        else:
            exercise_dict = self._exercise_dict(
                canonical_name=canonical_name,
                source_name=exercise_name,
            )

        path.write_text(
            json.dumps(exercise_dict, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return self._exercise_from_dict(exercise_dict)

    def prescribed_equipment_from_name(self, exercise_name: str) -> list[EquipmentOption]:
        """Return equipment prescribed by a raw exercise name."""
        _, equipment_names = self.normalize_exercise_name(
            exercise_name)
        return [
            EquipmentOption(option=Equipment(equipment_name))
            for equipment_name in equipment_names
        ]

    def seed_from_raw_text(self, text: str) -> list[Exercise]:
        """Create repository exercises from every parsed exercise in raw workout text."""
        exercises = []
        parser = WorkoutTextParser()
        for workout in parser.parse(text):
            for numbered_exercise in workout.exercises:
                match = self.NUMBERED_EXERCISE_PATTERN.match(numbered_exercise)
                if match:
                    exercises.append(
                        self.get_or_create_exercise(match.group(1)))
        return exercises

    def normalize_exercise_name(self, exercise_name: str) -> tuple[str, list[str]]:
        """Split leading equipment words from the canonical exercise movement name."""
        clean_name = self._clean_source_name(exercise_name)
        equipment_names = []

        while True:
            match = self.EQUIPMENT_PATTERN.match(clean_name)
            if not match:
                break
            equipment_name = self.EQUIPMENT_ALIASES[match.group(1).lower()]
            if equipment_name not in equipment_names:
                equipment_names.append(equipment_name)
            clean_name = self._normalize_spaces(clean_name[match.end():])

        return clean_name, equipment_names

    def _clean_source_name(self, exercise_name: str) -> str:
        clean_name = exercise_name.lower()
        clean_name = re.sub(r"\([^)]*\)", "", clean_name)
        clean_name = re.sub(r"\bygig\b", "", clean_name)
        clean_name = re.sub(r"\b\d+x\s\b", "", clean_name)  # e.g., "3x"
        clean_name = re.sub(r"\b\d+x\d\b", "", clean_name)  # e.g., "3x5"
        return self._normalize_spaces(clean_name)

    def _exercise_dict(
        self,
        canonical_name: str,
        source_name: str,
    ) -> dict:
        return {
            "name": canonical_name,
            "description": "",
            "visual_url": "",
            "target_muscle_groups": [],
            "source_names": [source_name],
        }

    def _merge_source_name(self, exercise_dict: dict, source_name: str) -> None:
        source_names = exercise_dict.setdefault("source_names", [])
        if source_name not in source_names:
            source_names.append(source_name)

    def _exercise_from_dict(self, exercise_dict: dict) -> Exercise:
        return Exercise(
            name=exercise_dict["name"],
            description=exercise_dict.get("description", ""),
            visual_url=exercise_dict.get("visual_url", ""),
            target_muscle_groups=[
                MuscleGroup(muscle_group)
                for muscle_group in exercise_dict.get("target_muscle_groups", [])
            ],
        )

    def _path_for_name(self, exercise_name: str) -> Path:
        return self.exercise_dir / f"{self._slugify(exercise_name)}.json"

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
        return slug or "exercise"

    def _normalize_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


def exercise_to_dict(exercise: Exercise) -> dict:
    """Convert an Exercise object to a JSON-friendly dictionary."""
    exercise_dict = asdict(exercise)
    exercise_dict["target_muscle_groups"] = [
        muscle_group.value for muscle_group in exercise.target_muscle_groups
    ]
    return exercise_dict


def main() -> None:
    """Seed an exercise repository from a raw workout text file."""
    parser = argparse.ArgumentParser(
        description="Seed canonical exercises from raw workout text."
    )
    parser.add_argument("input_file", help="Path to the raw workout text file")
    parser.add_argument(
        "--exercise-dir",
        default=Path("src") / "data" / "exercises",
        help="Directory where exercise JSON files are stored",
    )
    args = parser.parse_args()

    input_file = Path(args.input_file)
    raw_text = input_file.read_text(encoding="utf-8")
    repository = ExerciseRepository(args.exercise_dir)
    exercises = repository.seed_from_raw_text(raw_text)

    print(
        f"Seeded {len({exercise.name for exercise in exercises})} "
        f"exercise(s) into {repository.exercise_dir}."
    )


if __name__ == "__main__":
    main()
