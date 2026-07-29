"""File-backed repository for equipment options and their substitutes."""

from __future__ import annotations

import argparse
from pathlib import Path
import json
import re

from data_acquisition.models.equipment import Equipment, EquipmentOption
from data_acquisition.workout_text_parser import WorkoutTextParser


class EquipmentRepository:
    """Store equipment options as JSON files keyed by normalized names."""

    EQUIPMENT_ALIASES = {
        "activation band": "band",
        "agility box": "box",
        "barbell": "barbell",
        "balance trainer": "balance trainer",
        "bench": "bench",
        "bike erg": "bike erg",
        "chin up": "bar",
        "deadball": "deadball",
        "deadhang": "bar",
        "double kb": "kettlebell",
        "dumbbell": "dumbbell",
        "dumbbells": "dumbbell",
        "kettlebell": "kettlebell",
        "olympic barbell": "barbell",
        "plate": "plate",
        "plyo box": "box",
        "power band": "band",
        "pull up": "bar",
        "revo": "revo bar",
        "row erg": "row erg",
        "sandbag": "sandbag",
        "single kb": "kettlebell",
        "ski erg": "ski erg",
        "soft box": "box",
        "softbox": "box",
        "step trainer": "box",
        "suspension trainer": "suspension trainer",
        "ybell": "ybell",
    }

    EQUIPMENT_ALIAS_SUBSTITUTIONS = {
        "band": ["dumbell", "ybell"],  # independent, two hand, center grip
        "bar": ["band"],  # coordinated, two hand, center grip, pull
        # coordinated, two hand, center grip
        "barbell": ["dumbbell", "ybell", "sandbag", "revo bar"],
        "balance trainer": ["box", "bench"],  # unstable surface
        "box": ["bench", "balance trainer"],  # stable surface
        "bench": ["box", "balance trainer"],  # stable surface
        # coordinated, two hand, outer grip
        "deadball": ["sandbag", "dumbbell", "ybell", "kettlebell", "plate"],
        # independent/coordinated, single/two hand, center grip
        "dumbbell": ["ybell", "kettlebell", "sandbag", "plate", "barbell", "revo bar"],
        # independent/coordinated, single/two hand, outer grip
        "kettlebell": ["ybell", "dumbbell", "sandbag", "plate"],
        # coordinated, two hand, center grip
        "revo bar": ["barbell", "dumbbell", "ybell", "sandbag"],
        # coordinated, two hand, outer grip
        "sandbag": ["plate", "barbell", "revo bar", "kettlebell", "dumbbell", "ybell"],
        # coordinated, two hand, outer grip
        "plate": ["sandbag", "dumbbell", "ybell", "kettlebell"],
        # independent/coordinated, single/two hand, center/outer grip
        "ybell": ["dumbbell", "kettlebell", "sandbag", "plate"],
    }
    EQUIPMENT_PATTERN = re.compile(
        rf"^({'|'.join(re.escape(alias) for alias in sorted(
            EQUIPMENT_ALIASES, key=len, reverse=True))})\b\s*",
        re.IGNORECASE,
    )
    NUMBERED_EXERCISE_PATTERN = re.compile(r"^\d+\.\s*(.+)$")

    def __init__(self, equipment_dir: str | Path):
        self.equipment_dir = Path(equipment_dir)
        self.equipment_dir.mkdir(parents=True, exist_ok=True)

    def get_equipment_by_name(self, exercise_text: str) -> list[EquipmentOption] | None:
        """Return an existing equipment option matching the raw name from raw exercise text."""
        equipment_names = self.normalize_exercise_text(exercise_text)
        if not equipment_names:
            return None
        equipment = []
        for equipment_name in equipment_names:
            path = self._path_for_name(equipment_name)
            if path.exists():
                equipment.append(self._equipment_from_dict(
                    json.loads(path.read_text(encoding="utf-8"))))
        return equipment if equipment else None

    def get_or_create_equipment(self, exercise_text: str) -> list[EquipmentOption] | None:
        """Return an existing equipment option or create one from the raw exercise text."""
        equipment_names = self.normalize_exercise_text(exercise_text)
        if not equipment_names:
            # An exercise with no leading equipment name is considered to have no equipment.
            return None
        equipment = []
        for equipment_name in equipment_names:
            path = self._path_for_name(equipment_name)
            if path.exists():
                equipment_dict = json.loads(path.read_text(encoding="utf-8"))
                self._merge_source_text(equipment_dict, exercise_text)
            else:
                equipment_dict = self._equipment_dict(
                    canonical_name=equipment_name,
                    source_text=exercise_text,
                )

            path.write_text(
                json.dumps(equipment_dict, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            equipment.append(self._equipment_from_dict(equipment_dict))

        return equipment if equipment else None

    def seed_from_raw_text(self, text: str) -> list[EquipmentOption]:
        """Create repository equipment from every parsed equipment in raw workout text."""
        equipment = []
        parser = WorkoutTextParser()
        for workout in parser.parse(text):
            for numbered_exercise in workout.exercises:
                match = self.NUMBERED_EXERCISE_PATTERN.match(numbered_exercise)
                if match:
                    equipment_from_exercise = self.get_or_create_equipment(
                        match.group(1))
                    if equipment_from_exercise:
                        equipment.extend(equipment_from_exercise)
        return equipment

    def normalize_exercise_text(self, exercise_text: str) -> list[str]:
        """Extract leading equipment names from the raw exercise text."""
        clean_text = self._clean_exercise_text(exercise_text)
        equipment_names = []

        while True:
            match = self.EQUIPMENT_PATTERN.match(clean_text)
            if not match:
                break
            equipment_name = self.EQUIPMENT_ALIASES[match.group(1).lower()]
            if equipment_name not in equipment_names:
                equipment_names.append(equipment_name)
                break  # Only consider the first leading equipment name for now

        return equipment_names

    def _clean_exercise_text(self, exercise_text: str) -> str:
        clean_text = exercise_text.lower()
        clean_text = re.sub(r"\([^)]*\)", "", clean_text)
        clean_text = re.sub(r"\bygig\b", "", clean_text)
        clean_text = re.sub(r"\b\d+x\s\b", "", clean_text)  # e.g., "3x"
        clean_text = re.sub(r"\b\d+x\d\b", "", clean_text)  # e.g., "3x5"
        return self._normalize_spaces(clean_text)

    def _equipment_dict(
        self,
        canonical_name: str,
        source_text: str,
    ) -> dict:
        return {
            "name": canonical_name,
            "source_names": [source_text],
        }

    def _merge_source_text(self, equipment_dict: dict, source_text: str) -> None:
        existing_source_texts = equipment_dict.setdefault("source_names", [])
        if source_text not in existing_source_texts:
            existing_source_texts.append(source_text)

    def _get_equipment_substitutes(self, equipment_name: str) -> list[str]:
        """Return a list of substitute equipment names for the given equipment name."""
        return self.EQUIPMENT_ALIAS_SUBSTITUTIONS.get(equipment_name, [])

    def _equipment_from_dict(self, equipment_dict: dict) -> EquipmentOption:
        return EquipmentOption(
            option=Equipment(name=equipment_dict["name"]),
            substitutes=[
                Equipment(name=substitute_name)
                for substitute_name in self._get_equipment_substitutes(
                    equipment_dict["name"])
            ],
        )

    def _path_for_name(self, equipment_name: str) -> Path:
        return self.equipment_dir / f"{self._slugify(equipment_name)}.json"

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
        return slug or "equipment"

    def _normalize_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


def equipment_option_to_dict(equipment_option: EquipmentOption) -> dict:
    """Convert an EquipmentOption object to a JSON-friendly dictionary."""
    return {
        "name": equipment_option.option.name,
        "substitutes": [substitute.name for substitute in equipment_option.substitutes]
    }


def main() -> None:
    """Seed an equipment repository from a raw workout text file."""
    parser = argparse.ArgumentParser(
        description="Seed canonical equipment from raw workout text."
    )
    parser.add_argument("input_file", help="Path to the raw workout text file")
    parser.add_argument(
        "--equipment-dir",
        default=Path("src") / "data" / "equipment",
        help="Directory where equipment JSON files are stored",
    )
    args = parser.parse_args()

    input_file = Path(args.input_file)
    raw_text = input_file.read_text(encoding="utf-8")
    repository = EquipmentRepository(args.equipment_dir)
    equipment = repository.seed_from_raw_text(raw_text)

    print(
        f"Seeded {len({equipment.option.name for equipment in equipment})} "
        f"equipment(s) into {repository.equipment_dir}."
    )


if __name__ == "__main__":
    main()
