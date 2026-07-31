import json
from typing import Any
from zipfile import Path

from data_acquisition.equipment_repository import EquipmentRepository
from data_acquisition.exercise_repository import ExerciseRepository
from data_acquisition.models.equipment import Equipment, EquipmentOption
from data_acquisition.models.exercise import Exercise
from data_acquisition.workout_builder import WorkoutBuilder
from data_acquisition.workout_text_parser import ParsedWorkout


def test_repository_omits_leading_resistance_equipment_from_exercise_name(tmp_path):
    exercise_path, repository = _create_exercise_repository(tmp_path)

    equipment, exercise = repository.get_or_create_exercise_from_text(
        "dumbbell rdl")

    assert exercise == Exercise(name="rdl")
    assert equipment == [EquipmentOption(option=Equipment("dumbbell"))]
    assert (exercise_path / "rdl.json").exists()


def test_repository_merges_equipment_variants_into_one_canonical_exercise(tmp_path):
    exercise_path, repository = _create_exercise_repository(tmp_path)
    repository.get_or_create_exercise_from_text("dumbbell rdl")
    _, exercise = repository.get_or_create_exercise_from_text("barbell rdl")

    assert exercise.name == "rdl"

    exercise_dict = json.loads(
        (exercise_path / "rdl.json").read_text(encoding="utf-8"))
    assert exercise_dict["source_texts"] == ["dumbbell rdl", "barbell rdl"]
    assert "required_equipment" not in exercise_dict


def test_repository_omits_workout_qualifiers_from_exercise_name(tmp_path):
    _, repository = _create_exercise_repository(tmp_path)

    equipment, exercise = repository.get_or_create_exercise_from_text(
        "4x dumbbell devils press ygig (heavy)"
    )

    assert exercise == Exercise(name="devils press")
    assert equipment == [EquipmentOption(option=Equipment("dumbbell"))]


def test_seed_from_raw_text_creates_exercises_from_parsed_workouts(tmp_path):
    _, repository = _create_exercise_repository(tmp_path)

    repository.seed_from_raw_text(
        """
Monday June 8: Sample

Stations: 1

Timing: 45" work 15" rest

1. kettlebell cossack squat
"""
    )

    _, exercise = repository.get_or_create_exercise_from_text(
        "kettlebell cossack squat"
    )
    assert exercise == Exercise(name="cossack squat")


def test_builder_gets_or_creates_repository_exercises(tmp_path):
    _, repository = _create_exercise_repository(tmp_path)

    workout = WorkoutBuilder(repository).build_workout(
        ParsedWorkout(
            name="Sample",
            pods=1,
            stations="1",
            sets="1",
            laps="1",
            timing=[],
            exercises=["1. barbell front squat"],
        )
    )

    prescription = workout.pods[0].laps[0].stations[0].sets[0].exercises[0]
    assert prescription.exercise == Exercise(name="front squat")
    assert prescription.source_name == "barbell front squat"
    assert prescription.prescribed_equipment == [
        EquipmentOption(
            option=Equipment("barbell"),
        ),
    ]


def _create_exercise_repository(tmp_path) -> tuple[Any, ExerciseRepository]:
    equipment_repository = EquipmentRepository(tmp_path / "equipment")
    exercise_path = tmp_path / "exercises"
    return exercise_path, ExerciseRepository(
        exercise_path, equipment_repository=equipment_repository
    )
