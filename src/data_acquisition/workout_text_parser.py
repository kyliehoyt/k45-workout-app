
from dataclasses import dataclass, field
from pathlib import Path
from pprint import pprint
import re


@dataclass
class ParsedWorkout:
    name: str = ""
    pods: int | None = None
    stations: str = ""
    sets: str = ""
    laps: str = ""
    timing: list[str] = field(default_factory=list)
    exercises: list[str] = field(default_factory=list)


class WorkoutTextParser:

    HEADER_PATTERN = re.compile(
        # DayOfWeek Month Day: (name) to capture the name
        r"^[A-Za-z]+\s+[A-Za-z]+\s+\d+:\s+(.+)$"
    )

    EXERCISE_PATTERN = re.compile(
        # (number). (exerciseName) to capture the number and name
        re.compile(r"^(\d+)+\.\s+(.+)$")
    )

    def parse(self, text: str) -> list[ParsedWorkout]:
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
    input_file = Path("Raw Text Input.txt")

    with input_file.open("r", encoding="utf-8") as f:
        text = f.read()

    parser = WorkoutTextParser()
    workouts = parser.parse(text)

    print(f"Parsed {len(workouts)} workouts.\n")

    for workout in workouts:
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
