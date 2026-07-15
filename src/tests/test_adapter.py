from data_acquisition.adapter import (
    SetTiming,
    TimingQualifier,
)
import json
from data_acquisition.adapter import Adapter


# Sample workout JSON file
workout_data = {
    "name": "Sample Workout",
    "createdDate": "2026-06-07",
    "pods": [
        {
            "laps": [
                {
                    "stations": [
                        {
                            "sets": [
                                {
                                    "repetitions": 4,
                                    "exercises": [
                                        "tricep kickbacks"
                                    ],
                                    "timing": {
                                        "work_seconds": 35,
                                        "rest_seconds": 25
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "laps": [
                {
                    "repetitions": 2,
                    "stations": [
                        {
                            "sets": [
                                {
                                    "exercises": [
                                        "dumbbell bench incline pull",
                                        "olympic barbell front squat"
                                    ],
                                    "timing": {
                                        "work_seconds": 705,
                                        "rest_seconds": 0,
                                        "qualifier": "11:45"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}

workout_dict = {
    "name": "Sample Workout",
    "pods": [
        {
            "laps": [
                {
                    "stations": [
                        {
                            "sets": [
                                {
                                    "repetitions": 4,
                                    "exercises": [
                                        "tricep kickbacks"
                                    ],
                                    "timing": {
                                        "work_seconds": 35,
                                        "rest_seconds": 25
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "laps": [
                {
                    "repetitions": 2,
                    "stations": [
                        {
                            "sets": [
                                {
                                    "exercises": [
                                        "dumbbell bench incline pull",
                                        "olympic barbell front squat"
                                    ],
                                    "timing": {
                                        "work_seconds": 705,
                                        "rest_seconds": 0,
                                        "qualifier": "11:45"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}


def test_source_dir_not_found():
    """Test that the Adapter raises a ValueError when the source directory does not exist."""
    try:
        Adapter("non_existent_directory")
        assert False, "Expected ValueError was not raised."
    except ValueError as e:
        assert str(
            e) == "Source directory does not exist or is not a directory."


def test_workout_dir_not_found(tmp_path):
    """Test that the Adapter raises a ValueError when the workouts directory does not exist."""
    try:
        Adapter(tmp_path)
        assert False, "Expected ValueError was not raised."
    except ValueError as e:
        assert str(
            e) == "Workouts directory does not exist or is not a directory."


def test_exercise_dir_not_found(tmp_path):
    """Test that the Adapter raises a ValueError when the exercises directory does not exist."""
    (tmp_path / "workouts").mkdir()  # Pass the workouts directory check
    try:
        Adapter(tmp_path)
        assert False, "Expected ValueError was not raised."
    except ValueError as e:
        assert str(
            e) == "Exercises directory does not exist or is not a directory."


def test_equipment_dir_not_found(tmp_path):
    """Test that the Adapter raises a ValueError when the equipment directory does not exist."""
    (tmp_path / "workouts").mkdir()  # Pass the workouts directory check
    (tmp_path / "exercises").mkdir()  # Pass the exercises directory check
    try:
        Adapter(tmp_path)
        assert False, "Expected ValueError was not raised."
    except ValueError as e:
        assert str(
            e) == "Equipment directory does not exist or is not a directory."


def test_workout_data_source_initialized(tmp_path):
    """Test that the Adapter initializes correctly when all required directories exist."""
    (tmp_path / "workouts").mkdir()
    (tmp_path / "exercises").mkdir()
    (tmp_path / "equipment").mkdir()
    try:
        adapter = Adapter(tmp_path)
        assert adapter.source_dir == tmp_path
        assert adapter.workout_dir == tmp_path / "workouts"
        assert adapter.exercise_dir == tmp_path / "exercises"
        assert adapter.equipment_dir == tmp_path / "equipment"
    except ValueError:
        assert False, "Unexpected ValueError was raised."


def test_workout_dict_from_json(tmp_path):
    """Test that the workout_dict_from_json method correctly reads a workout from a JSON file."""
    adapter = initialize_adapter_with_valid_directories(tmp_path)

    workout_file = tmp_path / "workouts" / "sample_workout.json"
    with open(workout_file, "w", encoding="utf-8") as f:
        json.dump(workout_data, f)

    # Read the workout data using the adapter
    workout_dict = adapter.workout_dict_from_json("sample_workout.json")

    # Assert that the workout data was read correctly
    assert workout_dict is not None
    assert workout_dict["name"] == "Sample Workout"
    assert len(workout_dict["pods"]) == 2
    assert len(workout_dict["pods"][0]["laps"]) == 1
    assert len(workout_dict["pods"][0]["laps"][0]["stations"]) == 1
    assert len(workout_dict["pods"][0]["laps"][0]["stations"][0]["sets"]) == 1
    assert workout_dict["pods"][0]["laps"][0]["stations"][0]["sets"][0]["repetitions"] == 4
    assert workout_dict["pods"][0]["laps"][0]["stations"][0]["sets"][0]["exercises"] == [
        "tricep kickbacks"]
    assert workout_dict["pods"][0]["laps"][0]["stations"][0]["sets"][0]["timing"]["work_seconds"] == 35
    assert workout_dict["pods"][0]["laps"][0]["stations"][0]["sets"][0]["timing"]["rest_seconds"] == 25
    assert len(workout_dict["pods"][1]["laps"]) == 1
    assert len(workout_dict["pods"][1]["laps"][0]["stations"]) == 1
    assert workout_dict["pods"][1]["laps"][0]["repetitions"] == 2
    assert len(workout_dict["pods"][1]["laps"][0]["stations"][0]["sets"]) == 1
    assert workout_dict["pods"][1]["laps"][0]["stations"][0]["sets"][0]["exercises"] == [
        "dumbbell bench incline pull", "olympic barbell front squat"]
    assert workout_dict["pods"][1]["laps"][0]["stations"][0]["sets"][0]["timing"]["work_seconds"] == 705
    assert workout_dict["pods"][1]["laps"][0]["stations"][0]["sets"][0]["timing"]["rest_seconds"] == 0
    assert workout_dict["pods"][1]["laps"][0]["stations"][0]["sets"][0]["timing"]["qualifier"] == "11:45"


def test_workout_dict_from_json_file_not_found(tmp_path):
    """Test that the workout_dict_from_json method returns None when the file is not found."""
    adapter = initialize_adapter_with_valid_directories(tmp_path)

    workout_dict = adapter.workout_dict_from_json("non_existent_file.json")
    assert workout_dict is None


def test_workout_dict_from_json_invalid_json(tmp_path):
    """Test that the workout_dict_from_json method returns None when the file is not valid JSON."""
    adapter = initialize_adapter_with_valid_directories(tmp_path)

    # Create an invalid JSON file
    workout_file = tmp_path / "workouts" / "invalid_workout.json"
    with open(workout_file, "w", encoding="utf-8") as f:
        f.write("This is not valid JSON")

    workout_dict = adapter.workout_dict_from_json("invalid_workout.json")
    assert workout_dict is None


def initialize_adapter_with_valid_directories(tmp_path):
    """Helper function to initialize the Adapter with valid directories."""
    (tmp_path / "workouts").mkdir()
    (tmp_path / "exercises").mkdir()
    (tmp_path / "equipment").mkdir()
    return Adapter(tmp_path)


def exercise_names(exercise_set):
    """Return canonical exercise names for an ExerciseSet."""
    return [
        prescription.exercise.name
        for prescription in exercise_set.exercises
    ]


def test_workout_from_dict(tmp_path):
    """Test that the workout_from_dict method correctly converts a workout dictionary into a Workout object."""
    adapter = initialize_adapter_with_valid_directories(tmp_path)
    workout = adapter.workout_from_dict(workout_dict)

    assert workout.name == "Sample Workout"
    assert len(workout.pods) == 2
    assert len(workout.pods[0].laps) == 1
    assert len(workout.pods[0].laps[0].stations) == 1
    assert len(workout.pods[0].laps[0].stations[0].sets) == 1
    assert workout.pods[0].laps[0].stations[0].sets[0].repetitions == 4
    assert exercise_names(workout.pods[0].laps[0].stations[0].sets[0]) == [
        "tricep kickbacks"]
    assert workout.pods[0].laps[0].stations[0].sets[0].timing == SetTiming(
        work_duration_seconds=35, rest_duration_seconds=25)
    assert len(workout.pods[1].laps) == 1
    assert len(workout.pods[1].laps[0].stations) == 1
    assert workout.pods[1].laps[0].repetitions == 2
    assert len(workout.pods[1].laps[0].stations[0].sets) == 1
    assert exercise_names(workout.pods[1].laps[0].stations[0].sets[0]) == [
        "dumbbell bench incline pull", "olympic barbell front squat"]
    assert workout.pods[1].laps[0].stations[0].sets[0].timing == SetTiming(
        work_duration_seconds=705, rest_duration_seconds=0, timing_qualifier=TimingQualifier("11:45"))
