"""Build structured workout models from parsed workout text."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import re

from data_acquisition.equipment_repository import EquipmentRepository
from data_acquisition.exercise_repository import ExerciseRepository
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
            exercise_repository: Optional repository with get_or_create_exercise_from_text(text).
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
            exercise_texts = station_group[min(
                set_index - 1, len(station_group) - 1)]
            exercises, qualifier = self._build_exercises(exercise_texts)
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
        numbered_exercise_texts: list[str],
        station_count: int,
        set_count: int,
        sets_text: str,
        # list of stations, each with a list of sets, each with a list of exercise texts
    ) -> list[list[list[str]]]:
        exercise_texts_by_number = self._exercise_text_by_number(
            numbered_exercise_texts
        )
        if self._uses_repeated_numbered_options(
            exercise_texts_by_number, station_count
        ):
            # exercises are given as two lists: 1, 2, 3, 4, 1, 2, 3, 4
            # where each station has multiple exercise options
            return [
                [list(exercise_texts_by_number[number])]
                for number in sorted(exercise_texts_by_number)
            ]

        exercise_texts = [  # texts in order of their numbers, flattened into a single list
            text
            for number in sorted(exercise_texts_by_number)
            for text in exercise_texts_by_number[number]
        ]
        if self._uses_sequential_station_sets(
            exercise_count=len(exercise_texts),
            station_count=station_count,
            set_count=set_count,
            sets_text=sets_text,
        ):
            # exercises are implicitly given as activation + main exercise pairs: 1, 2, 3, 4, 5, 6,
            # where each station has an activation exercise (e.g. 1) and a main exercise (e.g. 2)
            groups = []
            for index in range(0, len(exercise_texts), 2):
                activation_exercise_text = exercise_texts[index]
                main_exercise_text = exercise_texts[index + 1]
                groups.append(
                    [[activation_exercise_text], [main_exercise_text]])
            return groups

        # exercises are given as a single list of exercises, one per station
        return [[[text]] for text in exercise_texts[:station_count]]

    def _exercise_text_by_number(
        self, numbered_exercise_texts: list[str]
    ) -> dict[int, list[str]]:
        exercise_texts_by_number: dict[int, list[str]] = {}
        for text in numbered_exercise_texts:
            match = self.EXERCISE_PATTERN.match(text)
            if not match:
                continue
            number = int(match.group(1))
            exercise_text = match.group(2).strip()
            exercise_texts_by_number.setdefault(
                number, []).append(exercise_text)
        return exercise_texts_by_number

    def _uses_repeated_numbered_options(
        self,
        exercise_texts_by_number: dict[int, list[str]],
        station_count: int,
    ) -> bool:
        return (
            bool(exercise_texts_by_number)  # any exercises found
            # the highest numbered exercise matches the station count
            and max(exercise_texts_by_number) == station_count
            # any number has multiple exercises
            and any(len(text) > 1 for text in exercise_texts_by_number.values())
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
        base_size = (
            remaining_station_count // flexible_pod_count if flexible_pod_count else 0
        )
        extra = (
            remaining_station_count % flexible_pod_count if flexible_pod_count else 0
        )

        pod_station_groups = []
        station_index = 0
        for pod_index in range(1, pod_count + 1):
            if pod_index in single_station_pods:
                size = 1
            else:
                size = base_size + (1 if extra > 0 else 0)
                extra -= 1 if extra > 0 else 0
            pod_station_groups.append(
                station_groups[station_index: station_index + size]
            )
            station_index += size

        return pod_station_groups

    def _build_exercises(
        self,
        exercise_texts: list[str],
    ) -> tuple[list[ExercisePrescription], TimingQualifier | None]:
        exercise_prescriptions = []
        timing_qualifier = None
        for exercise_text in exercise_texts:
            equipment_and_exercise, qualifier = self._extract_timing_qualifier(
                exercise_text
            )
            timing_qualifier = timing_qualifier or qualifier
            exercise_prescriptions.append(
                self._exercise_prescription_from_text(equipment_and_exercise)
            )
        return exercise_prescriptions, timing_qualifier

    def _exercise_prescription_from_text(
        self, exercise_text: str
    ) -> ExercisePrescription:
        if self.exercise_repository is None:
            return ExercisePrescription(
                exercise=Exercise(name=exercise_text),
                source_text=exercise_text,
            )

        equipment, exercise = self.exercise_repository.get_or_create_exercise_from_text(
            exercise_text
        )
        return ExercisePrescription(
            exercise=exercise,
            source_text=exercise_text,
            prescribed_equipment=equipment,
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
            r"(\d+)\s*(?:\"|s|sec|seconds?)?\s*work", normalized
        )  # e.g. '30" work'
        rest_match = re.search(
            r"(\d+)\s*(?:\"|s|sec|seconds?)?\s*rest", normalized
        )  # e.g. '30" rest'
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
        rule = (
            max(matching_rules, key=self._rule_specificity) if matching_rules else None
        )
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
        rule = (
            max(matching_rules, key=self._rule_specificity) if matching_rules else None
        )
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

    def save_workout_to_json(self, workout: Workout, output_file: str | Path) -> None:
        """
        Save a Workout object to a JSON file.

        Args:
            workout: The Workout object to save.
            output_file: The path to the output JSON file.
        """
        workout_dict = {
            "name": workout.name,
            "import_date": datetime.now().strftime("%Y-%m-%d"),
            "pods": [
                {
                    "laps": [
                        {
                            "stations": [
                                {
                                    "sets": [
                                        {
                                            "exercises": [
                                                {
                                                    "name": exercise_prescription.exercise.name,
                                                    "source_text": exercise_prescription.source_text,
                                                    "prescribed_equipment": [
                                                        {
                                                            "name": equipment_option.option.name
                                                            if equipment_option.option
                                                            else None
                                                        }
                                                        for equipment_option in exercise_prescription.prescribed_equipment
                                                    ] if exercise_prescription.prescribed_equipment else [],
                                                }
                                                for exercise_prescription in exercise_set.exercises
                                            ],
                                            "timing": {
                                                "work_duration_seconds": exercise_set.timing.work_duration_seconds,
                                                "rest_duration_seconds": exercise_set.timing.rest_duration_seconds,
                                                "timing_qualifier": exercise_set.timing.timing_qualifier.value
                                                if exercise_set.timing.timing_qualifier
                                                else None,
                                            },
                                            "repetitions": exercise_set.repetitions,
                                        }
                                        for exercise_set in station.sets
                                    ]
                                }
                                for station in lap.stations
                            ],
                            "repetitions": lap.repetitions,
                        }
                        for lap in pod.laps
                    ]
                }
                for pod in workout.pods
            ],
        }

        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(workout_dict, file, ensure_ascii=False, indent=4)


def _format_timing(timing: SetTiming) -> str:
    timing_text = (
        f"{timing.work_duration_seconds}s work / {timing.rest_duration_seconds}s rest"
    )
    if timing.timing_qualifier:
        timing_text += f" ({timing.timing_qualifier.value})"
    return timing_text


def _print_workout(workout: Workout) -> None:
    print(workout.name)
    print(f"  Pods      : {len(workout.pods)}")

    for pod_number, pod in enumerate(workout.pods, start=1):
        print(f"  Pod {pod_number}: {len(pod.laps)} lap pattern(s)")
        for lap_number, lap in enumerate(pod.laps, start=1):
            lap_suffix = f" x{lap.repetitions}" if lap.repetitions > 1 else ""
            print(
                f"    Lap {lap_number}{lap_suffix}: {len(lap.stations)} station(s)")
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
                    exercise_names = " OR ".join(
                        exercise_prescription.exercise.name
                        for exercise_prescription in exercise_set.exercises
                    )
                    equipment_names = []
                    for exercise_prescription in exercise_set.exercises:
                        if exercise_prescription.prescribed_equipment:
                            for (
                                equipment_option
                            ) in exercise_prescription.prescribed_equipment:
                                if equipment_option.option:
                                    equipment_names.append(
                                        equipment_option.option.name)

                    unique_equipment = set(equipment_names)
                    unique_equipment_str = (
                        ", ".join(unique_equipment) if unique_equipment else ""
                    )
                    print(
                        f"        Set {set_number}{set_suffix}: "
                        f"{_format_timing(exercise_set.timing)} | {exercise_names}"
                        f"{' | ' + unique_equipment_str if unique_equipment_str else ''}"
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
    file_text = input_file.read_text(encoding="utf-8")

    parsed_workouts = WorkoutTextParser().parse(file_text)
    exercise_repository = ExerciseRepository(
        args.exercise_dir, EquipmentRepository(args.equipment_dir)
    )
    workouts = [
        WorkoutBuilder(exercise_repository).build_workout(workout)
        for workout in parsed_workouts
    ]

    print(f"Built {len(workouts)} workout(s) from {input_file}.\n")
    for workout in workouts:
        WorkoutBuilder().save_workout_to_json(
            workout, Path("src") / "data" / "workouts" /
            f"{workout.name}.json"
        )
        _print_workout(workout)


if __name__ == "__main__":
    main()
