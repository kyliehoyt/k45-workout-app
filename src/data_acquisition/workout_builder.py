"""Build structured workout models from parsed workout text."""

import argparse
from dataclasses import replace
from pathlib import Path
import re

from data_acquisition.models.exercise import Exercise
from data_acquisition.models.set_timing import SetTiming, TimingQualifier
from data_acquisition.models.workout import (
    ExerciseSet,
    ExercisePrescription,
    Lap,
    Pod,
    Station,
    Workout,
)
from data_acquisition.workout_text_parser import ParsedWorkout, WorkoutTextParser


class WorkoutBuilder:
    """
    Build Workout objects from ParsedWorkout data.

    The text parser keeps the source data intentionally loose. This builder turns
    those strings into the nested workout model and uses repetition counts where
    the workout structure repeats with the same exercises and timing.
    """

    COUNT_PATTERN = re.compile(r"\d+")
    EXERCISE_PATTERN = re.compile(r"^(\d+)\.\s*(.+)$")
    POD_SCOPE_PATTERN = re.compile(r"\bpods?\s+([0-9&,\sand]+)", re.IGNORECASE)
    LAP_SCOPE_PATTERN = re.compile(r"\blaps?\s+(\d+)", re.IGNORECASE)
    SET_SCOPE_PATTERN = re.compile(r"\bsets?\s+([0-9&,\sand]+)", re.IGNORECASE)
    DEFAULT_TIMING = SetTiming(
        work_duration_seconds=45, rest_duration_seconds=15)

    def __init__(self, exercise_repository=None):
        """
        Initialize the builder.

        Args:
            exercise_repository: Optional repository with get_exercise_by_name(name).
        """
        self.exercise_repository = exercise_repository

    def build_workout(self, parsed_workout: ParsedWorkout) -> Workout:
        """
        Construct a Workout object from a ParsedWorkout instance.

        Args:
            parsed_workout: The parsed workout data.

        Returns:
            Workout populated with pods, laps, stations, sets, timing, and exercises.
        """
        pods = self._build_pods(parsed_workout)
        return Workout(
            name=parsed_workout.name,
            pods=pods,
        )

    def _build_pods(self, parsed_workout: ParsedWorkout) -> list[Pod]:
        pod_count = parsed_workout.pods or 1
        station_count = self._parse_count(parsed_workout.stations) or 1
        set_count = self._parse_count(parsed_workout.sets) or 1
        lap_count = self._parse_count(parsed_workout.laps) or 1
        timing_rules = self._parse_timing_rules(parsed_workout.timing)
        station_groups = self._build_station_exercise_groups(
            parsed_workout.exercises,
            station_count,
            set_count,
            parsed_workout.sets,
        )
        pod_station_groups = self._split_stations_by_pod(
            station_groups,
            pod_count,
            timing_rules,
        )

        return [
            Pod(
                laps=self._build_laps_for_pod(
                    pod_index=index + 1,
                    station_groups=groups,
                    lap_count=lap_count,
                    set_count=set_count,
                    timing_rules=timing_rules,
                )
            )
            for index, groups in enumerate(pod_station_groups)
        ]

    def _build_laps_for_pod(
        self,
        pod_index: int,
        station_groups: list[list[list[str]]],
        lap_count: int,
        set_count: int,
        timing_rules: list[dict],
    ) -> list[Lap]:
        laps = []
        for lap_index in range(1, lap_count + 1):
            stations = [
                self._build_station(
                    pod_index=pod_index,
                    lap_index=lap_index,
                    station_group=station_group,
                    set_count=set_count,
                    timing_rules=timing_rules,
                )
                for station_group in station_groups
            ]
            laps.append(Lap(stations=stations))

        return self._compress_laps(laps)

    def _build_station(
        self,
        pod_index: int,
        lap_index: int,
        station_group: list[list[str]],
        set_count: int,
        timing_rules: list[dict],
    ) -> Station:
        sets = []
        for set_index in range(1, set_count + 1):
            exercise_names = station_group[min(
                set_index - 1, len(station_group) - 1)]
            exercises, qualifier = self._build_exercises(exercise_names)
            timing = self._timing_for(
                timing_rules=timing_rules,
                pod_index=pod_index,
                lap_index=lap_index,
                set_index=set_index,
                qualifier=qualifier,
            )
            sets.append(
                ExerciseSet(
                    exercises=exercises,
                    timing=timing,
                    repetitions=self._set_repetitions_for(
                        timing_rules=timing_rules,
                        pod_index=pod_index,
                        lap_index=lap_index,
                        set_index=set_index,
                    ),
                )
            )

        return Station(sets=self._compress_exercise_sets(sets))

    def _build_station_exercise_groups(
        self,
        numbered_exercises: list[str],
        station_count: int,
        set_count: int,
        sets_text: str,
    ) -> list[list[list[str]]]:
        exercises_by_number = self._exercise_names_by_number(
            numbered_exercises)
        if self._uses_repeated_numbered_options(exercises_by_number, station_count):
            return [
                [[name for name in exercises_by_number[number]]]
                for number in sorted(exercises_by_number)
            ]

        exercise_names = [
            name
            for number in sorted(exercises_by_number)
            for name in exercises_by_number[number]
        ]
        if self._uses_sequential_station_sets(
            exercise_count=len(exercise_names),
            station_count=station_count,
            set_count=set_count,
            sets_text=sets_text,
        ):
            groups = []
            for index in range(0, len(exercise_names), 2):
                activation = exercise_names[index]
                main = exercise_names[index + 1]
                groups.append([[activation], [main]])
            return groups

        return [[[name]] for name in exercise_names[:station_count]]

    def _exercise_names_by_number(self, numbered_exercises: list[str]) -> dict[int, list[str]]:
        exercises_by_number: dict[int, list[str]] = {}
        for text in numbered_exercises:
            match = self.EXERCISE_PATTERN.match(text)
            if not match:
                continue
            number = int(match.group(1))
            exercise_name = match.group(2).strip()
            exercises_by_number.setdefault(number, []).append(exercise_name)
        return exercises_by_number

    def _uses_repeated_numbered_options(
        self,
        exercises_by_number: dict[int, list[str]],
        station_count: int,
    ) -> bool:
        return (
            bool(exercises_by_number)
            and max(exercises_by_number) == station_count
            and any(len(names) > 1 for names in exercises_by_number.values())
        )

    def _uses_sequential_station_sets(
        self,
        exercise_count: int,
        station_count: int,
        set_count: int,
        sets_text: str,
    ) -> bool:
        lower_sets = sets_text.lower()
        effective_station_count = self._parenthetical_count(
            sets_text) or station_count
        return (
            exercise_count == effective_station_count * 2
            and set_count > 1
            and ("activation" in lower_sets or "combo" in lower_sets)
        )

    def _split_stations_by_pod(
        self,
        station_groups: list[list[list[str]]],
        pod_count: int,
        timing_rules: list[dict],
    ) -> list[list[list[list[str]]]]:
        if pod_count <= 1:
            return [station_groups]

        single_station_pods = {
            pod
            for rule in timing_rules
            if rule["timing"].timing_qualifier == TimingQualifier.ELEVEN_FORTYFIVE
            for pod in rule.get("pods", [])
        }
        remaining_station_count = len(
            station_groups) - len(single_station_pods)
        flexible_pod_count = pod_count - len(single_station_pods)
        base_size = remaining_station_count // flexible_pod_count if flexible_pod_count else 0
        extra = remaining_station_count % flexible_pod_count if flexible_pod_count else 0

        pod_station_groups = []
        station_index = 0
        for pod_index in range(1, pod_count + 1):
            if pod_index in single_station_pods:
                size = 1
            else:
                size = base_size + (1 if extra > 0 else 0)
                extra -= 1 if extra > 0 else 0
            pod_station_groups.append(
                station_groups[station_index:station_index + size])
            station_index += size

        return pod_station_groups

    def _build_exercises(
        self,
        exercise_names: list[str],
    ) -> tuple[list[ExercisePrescription], TimingQualifier | None]:
        exercises = []
        timing_qualifier = None
        for exercise_name in exercise_names:
            clean_name, qualifier = self._extract_timing_qualifier(
                exercise_name)
            timing_qualifier = timing_qualifier or qualifier
            exercises.append(self._exercise_prescription_from_name(clean_name))
        return exercises, timing_qualifier

    def _exercise_prescription_from_name(self, exercise_name: str) -> ExercisePrescription:
        if self.exercise_repository is None:
            return ExercisePrescription(
                exercise=Exercise(name=exercise_name),
                source_name=exercise_name,
            )

        if hasattr(self.exercise_repository, "get_or_create_exercise"):
            return ExercisePrescription(
                exercise=self.exercise_repository.get_or_create_exercise(
                    exercise_name),
                source_name=exercise_name,
                prescribed_equipment=(
                    self.exercise_repository.prescribed_equipment_from_name(
                        exercise_name)
                ),
            )

        exercise = self.exercise_repository.get_exercise_by_name(exercise_name)
        return ExercisePrescription(
            exercise=exercise or Exercise(name=exercise_name),
            source_name=exercise_name,
        )

    def _extract_timing_qualifier(
        self,
        exercise_name: str,
    ) -> tuple[str, TimingQualifier | None]:
        clean_name = exercise_name
        qualifier = None

        if re.search(r"\bygig\b", clean_name, flags=re.IGNORECASE):
            clean_name = re.sub(r"\bygig\b", "", clean_name,
                                flags=re.IGNORECASE)
            qualifier = TimingQualifier.YOU_GO_I_GO

        return self._normalize_spaces(clean_name), qualifier

    def _parse_timing_rules(self, timing_lines: list[str]) -> list[dict]:
        rules = []
        for line in timing_lines:
            timing = self._parse_timing(line)
            if timing is None:
                continue
            rules.append(
                {
                    # parse the scope this line may apply to, e.g. "pods 1&3" or "pod 2"
                    "pods": self._parse_scope(self.POD_SCOPE_PATTERN, line),
                    "laps": self._parse_scope(self.LAP_SCOPE_PATTERN, line),
                    "sets": self._parse_scope(self.SET_SCOPE_PATTERN, line),
                    # sometimes set repetitions are here instead of in the sets section
                    "set_repetitions": self._parse_trailing_count("sets?", line),
                    "timing": timing,
                }
            )
        return rules

    def _parse_timing(self, text: str) -> SetTiming | None:
        # quotes are often used for seconds
        normalized = self._normalize_quotes(text.lower())
        if "11:45" in normalized:
            return SetTiming(
                work_duration_seconds=705,
                rest_duration_seconds=0,
                timing_qualifier=TimingQualifier.ELEVEN_FORTYFIVE,
            )

        work_match = re.search(
            r"(\d+)\s*(?:\"|s|sec|seconds?)?\s*work", normalized)  # e.g. '30" work'
        rest_match = re.search(
            r"(\d+)\s*(?:\"|s|sec|seconds?)?\s*rest", normalized)  # e.g. '30" rest'
        if not work_match:
            return None

        return SetTiming(
            work_duration_seconds=int(work_match.group(1)),
            rest_duration_seconds=int(
                rest_match.group(1)) if rest_match else 0,
        )

    def _timing_for(
        self,
        timing_rules: list[dict],
        pod_index: int,
        lap_index: int,
        set_index: int,
        qualifier: TimingQualifier | None,
    ) -> SetTiming:
        matching_rules = [
            rule
            for rule in timing_rules
            if self._rule_matches(rule, pod_index, lap_index, set_index)
        ]
        rule = max(matching_rules,
                   key=self._rule_specificity) if matching_rules else None
        timing = rule["timing"] if rule else self.DEFAULT_TIMING
        if qualifier and timing.timing_qualifier is None:
            return replace(timing, timing_qualifier=qualifier)
        return timing

    def _rule_matches(
        self,
        rule: dict,
        pod_index: int,
        lap_index: int,
        set_index: int,
    ) -> bool:
        return (
            (not rule["pods"] or pod_index in rule["pods"])
            and (not rule["laps"] or lap_index in rule["laps"])
            and (not rule["sets"] or set_index in rule["sets"])
        )

    def _rule_specificity(self, rule: dict) -> int:
        return sum(bool(rule[scope]) for scope in ("pods", "laps", "sets"))

    def _set_repetitions_for(
        self,
        timing_rules: list[dict],
        pod_index: int,
        lap_index: int,
        set_index: int,
    ) -> int:
        matching_rules = [
            rule
            for rule in timing_rules
            if rule["set_repetitions"]
            and self._rule_matches(rule, pod_index, lap_index, set_index)
        ]
        rule = max(matching_rules,
                   key=self._rule_specificity) if matching_rules else None
        return rule["set_repetitions"] if rule else 1

    def _parse_scope(self, pattern: re.Pattern, text: str) -> set[int]:
        match = pattern.search(text)
        if not match:
            return set()
        return {int(value) for value in re.findall(r"\d+", match.group(1))}

    def _parse_trailing_count(self, label_pattern: str, text: str) -> int | None:
        match = re.search(
            rf"\b(\d+)\s+{label_pattern}\b", text, flags=re.IGNORECASE)
        return int(match.group(1)) if match else None

    def _compress_laps(self, laps: list[Lap]) -> list[Lap]:
        compressed = []
        for lap in laps:
            if compressed and compressed[-1].stations == lap.stations:
                compressed[-1].repetitions += 1
            else:
                compressed.append(lap)
        return compressed

    def _compress_exercise_sets(self, sets: list[ExerciseSet]) -> list[ExerciseSet]:
        compressed = []
        for exercise_set in sets:
            if (
                compressed
                and compressed[-1].exercises == exercise_set.exercises
                and compressed[-1].timing == exercise_set.timing
            ):
                compressed[-1].repetitions += 1
            else:
                compressed.append(exercise_set)
        return compressed

    def _parse_count(self, text: str) -> int | None:
        # find the first occurrence of a number in the text
        match = self.COUNT_PATTERN.search(text or "")
        return int(match.group()) if match else None

    def _parenthetical_count(self, text: str) -> int | None:
        # find the first occurrence of a number in parentheses
        match = re.search(r"\((\d+)", text or "")
        return int(match.group(1)) if match else None

    def _normalize_quotes(self, text: str) -> str:
        return text.replace("”", '"').replace("“", '"').replace("â€", '"')

    def _normalize_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


def _format_timing(timing: SetTiming) -> str:
    timing_text = (
        f"{timing.work_duration_seconds}s work / "
        f"{timing.rest_duration_seconds}s rest"
    )
    if timing.timing_qualifier:
        timing_text += f" ({timing.timing_qualifier.value})"
    return timing_text


def _print_workout(workout: Workout) -> None:
    categories = ", ".join(
        category.value for category in workout.categories) or "None"
    print(workout.name)
    print(f"  Categories: {categories}")
    print(f"  Pods      : {len(workout.pods)}")

    for pod_number, pod in enumerate(workout.pods, start=1):
        print(f"  Pod {pod_number}: {len(pod.laps)} lap pattern(s)")
        for lap_number, lap in enumerate(pod.laps, start=1):
            lap_suffix = (
                f" x{lap.repetitions}" if lap.repetitions > 1 else ""
            )
            print(
                f"    Lap {lap_number}{lap_suffix}: "
                f"{len(lap.stations)} station(s)"
            )
            for station_number, station in enumerate(lap.stations, start=1):
                print(
                    f"      Station {station_number}: "
                    f"{len(station.sets)} set pattern(s)"
                )
                for set_number, exercise_set in enumerate(station.sets, start=1):
                    set_suffix = (
                        f" x{exercise_set.repetitions}"
                        if exercise_set.repetitions > 1
                        else ""
                    )
                    exercise_names = ", ".join(
                        exercise.exercise.name for exercise in exercise_set.exercises
                    )
                    print(
                        f"        Set {set_number}{set_suffix}: "
                        f"{_format_timing(exercise_set.timing)} | {exercise_names}"
                    )
    print()


def main() -> None:
    """
    Main function to parse a raw workout text file and print built Workout models.
    """
    parser = argparse.ArgumentParser(
        description="Parse a raw workout text file and print built Workout models."
    )
    parser.add_argument("input_file", help="Path to the raw workout text file")
    args = parser.parse_args()

    input_file = Path(args.input_file)
    file_text = input_file.read_text(encoding="utf-8")

    parsed_workouts = WorkoutTextParser().parse(file_text)
    workouts = [WorkoutBuilder().build_workout(workout)
                for workout in parsed_workouts]

    print(f"Built {len(workouts)} workout(s) from {input_file}.\n")
    for workout in workouts:
        _print_workout(workout)


if __name__ == "__main__":
    main()
