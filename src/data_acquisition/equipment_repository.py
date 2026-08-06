"""File-backed repository for equipment options and their substitutes."""

from __future__ import annotations

import argparse
from enum import Enum
from pathlib import Path
import json
import re
from typing import NamedTuple

from data_acquisition.models.equipment import Equipment, EquipmentOption
from data_acquisition.workout_text_parser import WorkoutTextParser


class CanonicalEquipmentDesc(NamedTuple):
    """A canonical name for a piece of equipment
    @property canonical_name: The canonical name for the equipment
    @property is_structural_equipment: True if the equipment is structural (e.g., a bar)
    @property is_exercise: True if the equipment is also an exercise (e.g., ski erg)
    """

    canonical_name: str
    is_structural_equipment: bool = False
    is_exercise: bool = False


class CanonicalEquipment(Enum):
    """Canonical names for equipment and whether they are structural equipment."""

    BAND = CanonicalEquipmentDesc(
        canonical_name="band", is_structural_equipment=False)
    BALANCE_TRAINER = CanonicalEquipmentDesc(
        canonical_name="balance trainer", is_structural_equipment=False
    )
    BARBELL = CanonicalEquipmentDesc(
        canonical_name="barbell", is_structural_equipment=False
    )
    BAR = CanonicalEquipmentDesc(
        canonical_name="bar", is_structural_equipment=True, is_exercise=True
    )
    BATTLE_ROPES = CanonicalEquipmentDesc(
        canonical_name="battle ropes", is_structural_equipment=True, is_exercise=True
    )
    BIKE_ERG = CanonicalEquipmentDesc(
        canonical_name="bike erg", is_structural_equipment=True
    )
    BOX = CanonicalEquipmentDesc(
        canonical_name="box", is_structural_equipment=True)
    BENCH = CanonicalEquipmentDesc(
        canonical_name="bench", is_structural_equipment=False
    )
    DEADBALL = CanonicalEquipmentDesc(
        canonical_name="deadball", is_structural_equipment=False
    )
    DUMBBELL = CanonicalEquipmentDesc(
        canonical_name="dumbbell", is_structural_equipment=False
    )
    KETTLEBELL = CanonicalEquipmentDesc(
        canonical_name="kettlebell", is_structural_equipment=False
    )
    LANDMINE = CanonicalEquipmentDesc(
        canonical_name="landmine", is_structural_equipment=True
    )
    PLATE = CanonicalEquipmentDesc(
        canonical_name="plate", is_structural_equipment=False
    )
    REVO_BAR = CanonicalEquipmentDesc(
        canonical_name="revo bar", is_structural_equipment=False
    )
    ROW_ERG = CanonicalEquipmentDesc(
        canonical_name="row erg", is_structural_equipment=True
    )
    SANDBAG = CanonicalEquipmentDesc(
        canonical_name="sandbag", is_structural_equipment=False
    )
    SKI_ERG = CanonicalEquipmentDesc(
        canonical_name="ski erg", is_structural_equipment=True
    )
    SLED = CanonicalEquipmentDesc(
        canonical_name="sled", is_structural_equipment=True)
    SLIDES = CanonicalEquipmentDesc(
        canonical_name="slides", is_structural_equipment=True
    )
    SUSPENSION_TRAINER = CanonicalEquipmentDesc(
        canonical_name="TRX straps", is_structural_equipment=True
    )
    YBELL = CanonicalEquipmentDesc(
        canonical_name="ybell", is_structural_equipment=False
    )

    @classmethod
    def to_dict(cls) -> dict:
        """Return a dictionary mapping canonical names to CanonicalEquipmentDesc objects."""
        return {equipment.value.canonical_name: equipment.value for equipment in cls}

    @classmethod
    def equipment_substitutions(cls) -> dict[str, list[str]]:
        """Return a dictionary mapping canonical equipment names to
        a list of substitute canonical equipment names."""
        return {
            # independent, two hand, center grip
            CanonicalEquipment.BAND.name: [
                CanonicalEquipment.DUMBBELL.name,
                CanonicalEquipment.YBELL.name,
            ],
            # coordinated, two hand, center grip, pull
            CanonicalEquipment.BAR.name: [CanonicalEquipment.BAND.name],
            # coordinated, two hand, center grip
            CanonicalEquipment.BARBELL.name: [
                CanonicalEquipment.DUMBBELL.name,
                CanonicalEquipment.YBELL.name,
                CanonicalEquipment.SANDBAG.name,
                CanonicalEquipment.REVO_BAR.name,
            ],
            # unstable surface
            CanonicalEquipment.BALANCE_TRAINER.name: [
                CanonicalEquipment.BOX.name,
                CanonicalEquipment.BENCH.name,
            ],
            # stable surface
            CanonicalEquipment.BOX.name: [
                CanonicalEquipment.BENCH.name,
                CanonicalEquipment.BALANCE_TRAINER.name,
            ],
            # stable surface
            CanonicalEquipment.BENCH.name: [
                CanonicalEquipment.BOX.name,
                CanonicalEquipment.BALANCE_TRAINER.name,
            ],
            # coordinated, two hand, outer grip
            CanonicalEquipment.DEADBALL.name: [
                CanonicalEquipment.SANDBAG.name,
                CanonicalEquipment.DUMBBELL.name,
                CanonicalEquipment.YBELL.name,
                CanonicalEquipment.KETTLEBELL.name,
                CanonicalEquipment.PLATE.name,
            ],
            # independent/coordinated, single/two hand, outer grip
            CanonicalEquipment.KETTLEBELL.name: [
                CanonicalEquipment.YBELL.name,
                CanonicalEquipment.DUMBBELL.name,
                CanonicalEquipment.SANDBAG.name,
                CanonicalEquipment.PLATE.name,
            ],
            # coordinated, single/two hand, outer grip
            CanonicalEquipment.LANDMINE.name: [
                CanonicalEquipment.BARBELL.name,
                CanonicalEquipment.PLATE.name,
            ],
            # coordinated, two hand, center grip
            CanonicalEquipment.REVO_BAR.name: [
                CanonicalEquipment.BARBELL.name,
                CanonicalEquipment.DUMBBELL.name,
                CanonicalEquipment.YBELL.name,
                CanonicalEquipment.SANDBAG.name,
            ],
            # coordinated, two hand, outer grip
            CanonicalEquipment.SANDBAG.name: [
                CanonicalEquipment.PLATE.name,
                CanonicalEquipment.BARBELL.name,
                CanonicalEquipment.REVO_BAR.name,
                CanonicalEquipment.KETTLEBELL.name,
                CanonicalEquipment.DUMBBELL.name,
                CanonicalEquipment.YBELL.name,
            ],
            # coordinated, two hand, outer grip
            CanonicalEquipment.PLATE.name: [
                CanonicalEquipment.SANDBAG.name,
                CanonicalEquipment.DUMBBELL.name,
                CanonicalEquipment.YBELL.name,
                CanonicalEquipment.KETTLEBELL.name,
            ],
            # independent/coordinated, single/two hand, center/outer grip
            CanonicalEquipment.YBELL.name: [
                CanonicalEquipment.DUMBBELL.name,
                CanonicalEquipment.KETTLEBELL.name,
                CanonicalEquipment.SANDBAG.name,
                CanonicalEquipment.PLATE.name,
            ],
        }


class EquipmentRepository:
    """Store equipment options as JSON files keyed by normalized names."""

    # Aliases for equipment names to canonical equipment descriptions.
    # Names of the canonical equipment themselves are added by the to_dict()
    # method of CanonicalEquipment.
    EQUIPMENT_ALIASES = {
        "activation band": CanonicalEquipment.BAND.value,
        "agility box": CanonicalEquipment.BOX.value,
        "chin up": CanonicalEquipment.BAR.value,
        "deadhang": CanonicalEquipment.BAR.value,
        "double kb": CanonicalEquipment.KETTLEBELL.value,
        "dumbbells": CanonicalEquipment.DUMBBELL.value,
        "flat bench": CanonicalEquipment.BENCH.value,
        "ghr": CanonicalEquipment.SLIDES.value,  # glute-hamstring-roller
        "hyrox cruise": CanonicalEquipment.ROW_ERG.value,
        "medicine ball": CanonicalEquipment.DEADBALL.value,
        "olympic barbell": CanonicalEquipment.BARBELL.value,
        "plyo box": CanonicalEquipment.BOX.value,
        "power band": CanonicalEquipment.BAND.value,
        "pull up": CanonicalEquipment.BAR.value,
        "revo": CanonicalEquipment.REVO_BAR.value,
        "riser": CanonicalEquipment.BOX.value,
        "single kb": CanonicalEquipment.KETTLEBELL.value,
        "soft box": CanonicalEquipment.BOX.value,
        "softbox": CanonicalEquipment.BOX.value,
        "step trainer": CanonicalEquipment.BOX.value,
        "suspension trainer": CanonicalEquipment.SUSPENSION_TRAINER.value,
    } | CanonicalEquipment.to_dict()

    EQUIPMENT_PATTERN = re.compile(
        rf"^({
            '|'.join(
                re.escape(alias)
                for alias in sorted(EQUIPMENT_ALIASES.keys(), key=len, reverse=True)
            )
        })\b\s*",
        re.IGNORECASE,
    )
    NUMBERED_EXERCISE_PATTERN = re.compile(r"^\d+\.\s*(.+)$")

    def __init__(self, equipment_dir: str | Path):
        self.equipment_dir = Path(equipment_dir)
        self.equipment_dir.mkdir(parents=True, exist_ok=True)

    def seed_from_raw_workout_text(self, text: str) -> list[EquipmentOption]:
        """Create repository equipment from every parsed equipment in raw workout text."""
        equipment = []
        parser = WorkoutTextParser()
        for workout in parser.parse(text):
            for numbered_exercise in workout.exercises:
                match = self.NUMBERED_EXERCISE_PATTERN.match(numbered_exercise)
                if match:
                    equipment_options, _ = self.get_or_create_equipment_from_text(
                        match.group(1)
                    )
                    if equipment_options:
                        equipment.extend(equipment_options)
        return equipment

    def get_or_create_equipment_from_text(
        self, exercise_text: str
    ) -> tuple[list[EquipmentOption] | None, str]:
        """Return a list of existing equipment options from raw exercise text creating and storing new ones.
        Also return the remaining exercise text after extracting equipment names."""
        equipment_names, remaining_exercise_text = (
            self.split_equipment_name_and_exercise(exercise_text)
        )
        if not equipment_names:
            # An exercise with no leading equipment name is considered to have no equipment.
            return None, remaining_exercise_text
        equipment = []
        for equipment_name in equipment_names:
            path = self._path_for_name(equipment_name)
            if path.exists():
                equipment_dict = json.loads(path.read_text(encoding="utf-8"))
                self._merge_source_text(equipment_dict, exercise_text)
            else:
                equipment_dict = self._equipment_dict(
                    equipment_name=equipment_name,
                    source_text=exercise_text,
                )

            path.write_text(
                json.dumps(equipment_dict, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            equipment.append(self._equipment_option_from_dict(equipment_dict))

        return (equipment if equipment else None, remaining_exercise_text)

    def split_equipment_name_and_exercise(
        self, exercise_text: str
    ) -> tuple[list[str], str]:
        """Extract leading equipment names from the raw exercise text, and return the remaining equipment and remaining text."""

        clean_exercise_text = self._clean_exercise_text(exercise_text)
        equipment_names = []

        while True:
            match = self.EQUIPMENT_PATTERN.match(clean_exercise_text)
            if not match:
                break
            canonical_equipment = self.EQUIPMENT_ALIASES[match.group(
                1).lower()]
            if canonical_equipment.canonical_name not in equipment_names:
                equipment_names.append(canonical_equipment.canonical_name)
            if canonical_equipment.is_structural_equipment:
                if not canonical_equipment.is_exercise:
                    # replace the structural equipment name with the canonical name in the exercise text first
                    clean_exercise_text = clean_exercise_text.replace(
                        match.group(1), canonical_equipment.canonical_name, 1
                    )
                break  # stop extracting equipment names after the first structural equipment name
            clean_exercise_text = clean_exercise_text[match.end():]

        return (equipment_names, clean_exercise_text)

    def _equipment_dict(
        self,
        equipment_name: str,
        source_text: str,
    ) -> dict:
        return {
            "name": equipment_name,
            "source_texts": [source_text],
        }

    def _merge_source_text(self, equipment_dict: dict, source_text: str) -> None:
        existing_source_texts = equipment_dict.setdefault("source_texts", [])
        if source_text not in existing_source_texts:
            existing_source_texts.append(source_text)

    def _get_equipment_substitutes(self, equipment_name: str) -> list[str]:
        """Return a list of substitute equipment names for the given equipment name."""
        return CanonicalEquipment.equipment_substitutions().get(equipment_name, [])

    def _equipment_option_from_dict(self, equipment_dict: dict) -> EquipmentOption:
        return EquipmentOption(
            option=Equipment(name=equipment_dict["name"]),
            substitutes=[
                Equipment(name=substitute_name)
                for substitute_name in self._get_equipment_substitutes(
                    equipment_dict["name"]
                )
            ],
        )

    def _clean_exercise_text(self, exercise_text: str) -> str:
        clean_text = exercise_text.lower()
        clean_text = re.sub(r"\([^)]*\)", "", clean_text)
        clean_text = re.sub(r"\bygig\b", "", clean_text)
        clean_text = re.sub(r"\b\d+x\s\b", "", clean_text)  # e.g., "3x"
        clean_text = re.sub(r"\b\d+x\d\b", "", clean_text)  # e.g., "3x5"
        return self._normalize_spaces(clean_text)

    def _path_for_name(self, equipment_name: str) -> Path:
        return self.equipment_dir / f"{self._slugify(equipment_name)}.json"

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
        return slug or "equipment"

    def _normalize_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


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
    equipment = repository.seed_from_raw_workout_text(raw_text)

    print(
        f"Seeded {len({equipment.option.name for equipment in equipment})} "
        f"equipment(s) into {repository.equipment_dir}."
    )


if __name__ == "__main__":
    main()
