import json

from data_acquisition.exercise_repository import ExerciseRepository
from data_acquisition.models.equipment import Equipment, EquipmentOption
from data_acquisition.models.exercise import Exercise
from data_acquisition.workout_builder import WorkoutBuilder
from data_acquisition.workout_text_parser import ParsedWorkout


def test_repository_omits_leading_resistance_equipment_from_exercise_name(tmp_path):
    repository = ExerciseRepository(tmp_path)

    exercise = repository.get_or_create_exercise("dumbbell rdl")

    assert exercise == Exercise(name="rdl")
    assert repository.prescribed_equipment_from_name("dumbbell rdl") == [
        EquipmentOption(option=Equipment("dumbbell"))
    ]
    assert (tmp_path / "rdl.json").exists()


def test_repository_merges_equipment_variants_into_one_canonical_exercise(tmp_path):
    repository = ExerciseRepository(tmp_path)

    repository.get_or_create_exercise("dumbbell rdl")
    exercise = repository.get_or_create_exercise("barbell rdl")

    assert exercise.name == "rdl"

    exercise_dict = json.loads((tmp_path / "rdl.json").read_text(encoding="utf-8"))
    assert exercise_dict["source_names"] == ["dumbbell rdl", "barbell rdl"]
    assert "required_equipment" not in exercise_dict


def test_repository_omits_workout_qualifiers_from_exercise_name(tmp_path):
    repository = ExerciseRepository(tmp_path)

    exercise = repository.get_or_create_exercise("4x dumbbell devils press ygig (heavy)")

    assert exercise == Exercise(name="devils press")
    assert repository.prescribed_equipment_from_name(
        "4x dumbbell devils press ygig (heavy)"
    ) == [EquipmentOption(option=Equipment("dumbbell"))]


def test_seed_from_raw_text_creates_exercises_from_parsed_workouts(tmp_path):
    repository = ExerciseRepository(tmp_path)

    repository.seed_from_raw_text(
        """
Monday June 8: Sample

Stations: 1

Timing: 45" work 15" rest

1. kettlebell cossack squat
"""
    )

    assert repository.get_exercise_by_name("kettlebell cossack squat") == Exercise(
        name="cossack squat"
    )


def test_builder_gets_or_creates_repository_exercises(tmp_path):
    repository = ExerciseRepository(tmp_path)

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
        EquipmentOption(option=Equipment("barbell"))
    ]
