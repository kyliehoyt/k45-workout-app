"""
This module provides a parser for workout text files. It extracts structured information 
from the text, including workout names, metadata, timing, and exercises.
The parser is designed to handle the specific format of K45 workout text files, which 
include headers, metadata, timing sections, and exercise listings.
"""
import argparse
from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass
class ParsedWorkout:
    """
    Represents a parsed workout with its associated metadata, timing, and exercises.
    Attributes:
        name (str): The name of the workout.
        pods (int | None): The number of pods in the workout, if specified.
        stations (str): A description of the stations in the workout.
        sets (str): A description of the sets in the workout.
        laps (str): A description of the laps in the workout.
        timing (list[str]): A list of timing information for the workout.
        exercises (list[str]): A list of exercises included in the workout.
    """
    name: str = ""
    pods: int | None = None
    stations: str = ""
    sets: str = ""
    laps: str = ""
    timing: list[str] = field(default_factory=list)
    exercises: list[str] = field(default_factory=list)


class WorkoutTextParser:
    """
    A parser for workout text files. It extracts structured information from the text, 
    including workout names, metadata, timing, and exercises.
    The parser is designed to handle the specific format of K45 workout text files, 
    which include headers, metadata, timing sections, and exercise listings.
    """
    HEADER_PATTERN = re.compile(
        # DayOfWeek Month Day: (name) to capture the name
        r"^[A-Za-z]+\s+[A-Za-z]+\s+\d+:\s+(.+)$"
    )

    EXERCISE_PATTERN = re.compile(
        # (number). (exerciseName) to capture the number and name
        re.compile(r"^(\d+)+\.\s+(.+)$")
    )

    def parse(self, text: str) -> list[ParsedWorkout]:
        """
        Parses the given workout text and returns a list of ParsedWorkout objects.
        Args:
            text (str): The workout text to parse.
        Returns:
            list[ParsedWorkout]: A list of parsed workout objects.
        """
        workouts = []

        current_workout = None
        reading_timing = False
        reading_exercises = False

        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            # Header
            header_match = self.HEADER_PATTERN.match(line)

            if header_match:
                if current_workout:
                    workouts.append(current_workout)

                current_workout = ParsedWorkout(
                    # .group(1) gives the captured name
                    name=header_match.group(1)
                )

                reading_timing = False
                reading_exercises = False
                continue

            if current_workout is None:
                continue

            lower = line.lower()

            # Metadata
            if lower.startswith("stations:"):
                current_workout.stations = line.split(":", 1)[1].strip()
                continue

            if lower.startswith("pods:"):
                current_workout.pods = self._parse_int(line)
                continue

            if lower.startswith("sets:"):
                current_workout.sets = line.split(":", 1)[1].strip()
                continue

            if lower.startswith("laps:") or lower.startswith("lap:"):
                # take what's after the semicolon
                current_workout.laps = line.split(":", 1)[1].strip()
                continue

            # Timing
            if lower.startswith("timing:"):
                reading_timing = True
                reading_exercises = False

                timing = line.split(":", 1)[1].strip()

                if timing:
                    current_workout.timing.append(timing)

                continue

            # timing continues until another section begins
            if reading_timing:

                # exercise section markers
                if lower.startswith((
                    "upper body",
                    "lower body",
                    "cardio",
                    "resistance",)
                ):
                    reading_timing = False
                    reading_exercises = True
                    continue
                if lower.startswith("1."):
                    reading_timing = False
                    reading_exercises = True
                    # do not continue to next line
                else:
                    current_workout.timing.append(line)
                    continue

            # Ignore section headers after timing section
            if lower.startswith(("upper body",
                                 "lower body",
                                 "cardio",
                                 "resistance",)
                                ):
                reading_exercises = True
                continue

            # Everything else is an exercise
            reading_exercises = True

            if reading_exercises:
                match = self.EXERCISE_PATTERN.match(line)
                if match:
                    exercise_number_and_name = match.group(0)
                    current_workout.exercises.append(exercise_number_and_name)

        if current_workout:
            workouts.append(current_workout)

        return workouts

    @staticmethod
    def _parse_int(text: str) -> int:
        match = re.search(r"\d+", text)
        return int(match.group()) if match else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse workout text files.")
    parser.add_argument("input_file", help="Path to the input text file")
    args = parser.parse_args()

    input_file = Path(args.input_file)

    with input_file.open("r", encoding="utf-8") as f:
        file_text = f.read()

    parser = WorkoutTextParser()
    parsed_workouts = parser.parse(file_text)

    print(f"Parsed {len(parsed_workouts)} workouts.\n")

    for workout in parsed_workouts:
        print(f"{workout.name}")
        print(f"  Stations : {workout.stations}")
        print(f"  Pods     : {workout.pods}")
        print(f"  Sets     : {workout.sets}")
        print(f"  Laps     : {workout.laps}")
        print(f"  Timing   : {workout.timing}")
        print(f"  Exercises: {len(workout.exercises)}")
        for exercise in workout.exercises:
            print(f"    {exercise}")

        print()
