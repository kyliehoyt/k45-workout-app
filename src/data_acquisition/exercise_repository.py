"""File-backed repository for canonical Exercise records."""

from __future__ import annotations

import argparse
from pathlib import Path
import json
import re

from data_acquisition.equipment_repository import EquipmentRepository
from data_acquisition.models.equipment import EquipmentOption
from data_acquisition.models.exercise import Exercise
from data_acquisition.workout_text_parser import WorkoutTextParser


class ExerciseRepository:
    """Store exercises as JSON files keyed by normalized, equipment-free names."""

    NUMBERED_EXERCISE_PATTERN = re.compile(r"^\d+\.\s*(.+)$")

    def __init__(
        self, exercise_dir: str | Path, equipment_repository: EquipmentRepository = None
    ):
        self.exercise_dir = Path(exercise_dir)
        self.exercise_dir.mkdir(parents=True, exist_ok=True)
        self.equipment_repository = equipment_repository

    def get_or_create_exercise_from_text(
        self, exercise_text: str
    ) -> tuple[list[EquipmentOption], Exercise] | None:
        """Return an existing exercise or create one from a raw exercise text."""
        equipment_options, exercise_only_text = (
            self.equipment_repository.get_or_create_equipment_from_text(exercise_text)
        )
        clean_name = self._clean_exercise_text(exercise_only_text)

        if not clean_name:
            # exercise text was only equipment, so use the first equipment name as the exercise name
            if equipment_options:
                clean_name = equipment_options[0].option.name
            else:
                return None  # no exercise name or equipment found

        path = self._path_for_name(clean_name)
        if path.exists():
            exercise_dict = json.loads(path.read_text(encoding="utf-8"))
            self._merge_source_text(exercise_dict, exercise_text)
        else:
            exercise_dict = self._exercise_dict(
                exercise_name=clean_name,
                source_text=exercise_text,
            )

        path.write_text(
            json.dumps(exercise_dict, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return (equipment_options, self._exercise_from_dict(exercise_dict))

    def seed_from_raw_text(self, text: str) -> list[Exercise]:
        """Create repository exercises from every parsed exercise in raw workout text."""
        exercises = []
        parser = WorkoutTextParser()
        for workout in parser.parse(text):
            for numbered_exercise in workout.exercises:
                match = self.NUMBERED_EXERCISE_PATTERN.match(numbered_exercise)
                if match:
                    _, exercise = self.get_or_create_exercise_from_text(match.group(1))
                    if exercise:
                        exercises.append(exercise)
                    else:
                        print(
                            f"Warning: Could not create exercise from text: '{match.group(1)}'"
                        )
        return exercises

    def _clean_exercise_text(self, exercise_text: str) -> str:
        clean_text = exercise_text.lower()
        clean_text = re.sub(r"\([^)]*\)", "", clean_text)
        clean_text = re.sub(r"\bygig\b", "", clean_text)
        clean_text = re.sub(r"\b\d+x\s\b", "", clean_text)  # e.g., "3x"
        clean_text = re.sub(r"\b\d+x\d\b", "", clean_text)  # e.g., "3x5"
        return self._normalize_spaces(clean_text)

    def _exercise_dict(
        self,
        exercise_name: str,
        source_text: str,
    ) -> dict:
        return {
            "name": exercise_name,
            "source_texts": [source_text],
        }

    def _merge_source_text(self, exercise_dict: dict, source_text: str) -> None:
        source_texts = exercise_dict.setdefault("source_texts", [])
        if source_text not in source_texts:
            source_texts.append(source_text)

    def _exercise_from_dict(self, exercise_dict: dict) -> Exercise:
        return Exercise(
            name=exercise_dict["name"],
        )

    def _path_for_name(self, exercise_name: str) -> Path:
        return self.exercise_dir / f"{self._slugify(exercise_name)}.json"

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
        return slug or "exercise"

    def _normalize_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


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
    parser.add_argument(
        "--equipment-dir",
        default=Path("src") / "data" / "equipment",
        help="Directory where equipment JSON files are stored",
    )
    args = parser.parse_args()

    input_file = Path(args.input_file)
    raw_text = input_file.read_text(encoding="utf-8")
    repository = ExerciseRepository(
        args.exercise_dir, equipment_repository=EquipmentRepository(args.equipment_dir)
    )
    exercises = repository.seed_from_raw_text(raw_text)

    print(
        f"Seeded {len({exercise.name for exercise in exercises})} "
        f"exercise(s) into {repository.exercise_dir}."
    )


if __name__ == "__main__":
    main()
