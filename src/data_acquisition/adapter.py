"""Adapter for converting workout JSON files into model objects."""

from pathlib import Path
import json

from .models.exercise import Exercise
from .models.set_timing import SetTiming, TimingQualifier
from .models.workout import (
    ExerciseSet,
    ExercisePrescription,
    Lap,
    Pod,
    Station,
    Workout,
    WorkoutCategory,
)


class Adapter:
    """Adapter for converting workout JSON files into model objects."""

    def __init__(self, source_dir: str):
        if not Path(source_dir).is_dir():
            raise ValueError(
                "Source directory does not exist or is not a directory.")

        workout_dir = Path(source_dir) / "workouts"
        if not Path(workout_dir).is_dir():
            raise ValueError(
                "Workouts directory does not exist or is not a directory.")

        exercise_dir = Path(source_dir) / "exercises"
        if not Path(exercise_dir).is_dir():
            raise ValueError(
                "Exercises directory does not exist or is not a directory."
            )

        equipment_dir = Path(source_dir) / "equipment"
        if not Path(equipment_dir).is_dir():
            raise ValueError(
                "Equipment directory does not exist or is not a directory."
            )

        self.source_dir = source_dir
        self.workout_dir = workout_dir
        self.exercise_dir = exercise_dir
        self.equipment_dir = equipment_dir

    def workout_dict_from_json(self, workout_file: str | Path) -> dict | None:
        """
        Reads a workout from a JSON file and returns a dictionary or None if an error occurs.
         Args:
            workout_file (str | Path): The path to the JSON file containing the workout data.
         Returns:
            dict | None: The dictionary created from the JSON data or None if an error occurs.
        """
        file_path = self.workout_dir / workout_file
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                workout = json.load(file)
                return workout
        except FileNotFoundError:
            print("Error: The file could not be found.")
            return None
        except json.JSONDecodeError:
            print("Error: The file is not valid JSON format.")
            return None

    def workout_from_dict(self, workout_dict: dict) -> Workout:
        """Convert a workout dictionary into a Workout object."""
        return Workout(
            name=workout_dict["name"],
            categories=[
                WorkoutCategory(category)
                for category in workout_dict.get("categories", [])
            ],
            description=workout_dict.get("description", ""),
            pods=[self._pod_from_dict(pod)
                  for pod in workout_dict.get("pods", [])],
        )

    def _pod_from_dict(self, pod_dict: dict) -> Pod:
        return Pod(laps=[self._lap_from_dict(lap) for lap in pod_dict.get("laps", [])])

    def _lap_from_dict(self, lap_dict: dict) -> Lap:
        return Lap(
            stations=[
                self._station_from_dict(station)
                for station in lap_dict.get("stations", [])
            ],
            repetitions=lap_dict.get("repetitions", 1),
        )

    def _station_from_dict(self, station_dict: dict) -> Station:
        return Station(
            sets=[
                self._exercise_set_from_dict(exercise_set)
                for exercise_set in station_dict.get("sets", [])
            ]
        )

    def _exercise_set_from_dict(self, exercise_set_dict: dict) -> ExerciseSet:
        return ExerciseSet(
            exercises=[
                ExercisePrescription(
                    exercise=Exercise(name=exercise),
                    source_name=exercise,
                )
                for exercise in exercise_set_dict["exercises"]
            ],
            timing=self._timing_from_dict(exercise_set_dict["timing"]),
            repetitions=exercise_set_dict.get("repetitions", 1),
        )

    def _timing_from_dict(self, timing_dict: dict) -> SetTiming:
        if not ("work_seconds" in timing_dict and "rest_seconds" in timing_dict):
            raise ValueError(
                "Timing must include both work_seconds and rest_seconds.")
        qualifier = timing_dict.get("qualifier")
        return SetTiming(
            work_duration_seconds=timing_dict["work_seconds"],
            rest_duration_seconds=timing_dict["rest_seconds"],
            timing_qualifier=TimingQualifier(qualifier) if qualifier else None,
        )
