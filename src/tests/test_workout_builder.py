from data_acquisition.models.exercise import Exercise, MuscleGroup
from data_acquisition.models.set_timing import SetTiming, TimingQualifier
from data_acquisition.models.workout import WorkoutCategory
from data_acquisition.workout_builder import WorkoutBuilder
from data_acquisition.workout_text_parser import ParsedWorkout


def exercise_names(exercise_set):
    return [
        prescription.exercise.name
        for prescription in exercise_set.exercises
    ]


def test_uniform_laps_are_compressed_into_repetitions():
    workout = WorkoutBuilder().build_workout(
        ParsedWorkout(
            name="Forty Five",
            pods=4,
            stations="16",
            sets="1",
            laps="3",
            timing=['45" work 0" rest'],
            exercises=[
                f"{number}. exercise {number}" for number in range(1, 17)],
        )
    )

    assert len(workout.pods) == 4
    assert len(workout.pods[0].laps) == 1
    assert workout.pods[0].laps[0].repetitions == 3
    assert len(workout.pods[0].laps[0].stations) == 4
    assert workout.pods[0].laps[0].stations[0].sets[0].timing == SetTiming(
        45, 0)


def test_uniform_sets_are_compressed_into_repetitions():
    workout = WorkoutBuilder().build_workout(
        ParsedWorkout(
            name="Panthers",
            pods=1,
            stations="2",
            sets="3",
            laps="1",
            timing=['35" work 20" rest'],
            exercises=["1. squat", "2. press"],
        )
    )

    exercise_set = workout.pods[0].laps[0].stations[0].sets[0]
    assert len(workout.pods[0].laps[0].stations[0].sets) == 1
    assert exercise_set.repetitions == 3
    assert exercise_names(exercise_set) == ["squat"]


def test_missing_or_unparseable_timing_falls_back_to_default():
    workouts = [
        WorkoutBuilder().build_workout(
            ParsedWorkout(
                name="No Timing",
                pods=1,
                stations="1",
                sets="1",
                laps="1",
                timing=timing,
                exercises=["1. squat"],
            )
        )
        for timing in ([], ["timing TBD"])
    ]

    assert [
        workout.pods[0].laps[0].stations[0].sets[0].timing for workout in workouts
    ] == [
        SetTiming(45, 15),
        SetTiming(45, 15),
    ]


def test_lap_scoped_timing_prevents_lap_compression_and_extracts_ygig():
    workout = WorkoutBuilder().build_workout(
        ParsedWorkout(
            name="Track Stars",
            pods=1,
            stations="2",
            sets="1",
            laps="2",
            timing=['Lap 1: 90" work 10" rest', 'Lap 2: 60" work 10" rest'],
            exercises=["1. static lunge ygig", "2. devils press ygig"],
        )
    )

    assert len(workout.pods[0].laps) == 2
    first_set = workout.pods[0].laps[0].stations[0].sets[0]
    assert exercise_names(first_set) == ["static lunge"]
    assert first_set.timing == SetTiming(
        90,
        10,
        TimingQualifier.YOU_GO_I_GO,
    )
    assert workout.pods[0].laps[1].stations[0].sets[0].timing == SetTiming(
        60,
        10,
        TimingQualifier.YOU_GO_I_GO,
    )


def test_set_scoped_timing_and_sequential_activation_main_exercises():
    workout = WorkoutBuilder().build_workout(
        ParsedWorkout(
            name="Medusa",
            pods=1,
            stations="2",
            sets="3 (set 1 activation, set 2 & 3 main lift)",
            laps="1",
            timing=[
                'set 1: 60" work, 15" rest',
                'set 2: 60" work, 20" rest',
                'set 3: 60" work, 20" rest',
            ],
            exercises=[
                "1. mobility",
                "2. sumo rdl",
                "3. stretch",
                "4. front squat",
            ],
        )
    )

    station = workout.pods[0].laps[0].stations[0]
    assert exercise_names(station.sets[0]) == ["mobility"]
    assert station.sets[0].timing == SetTiming(60, 15)
    assert exercise_names(station.sets[1]) == ["sumo rdl"]
    assert station.sets[1].timing == SetTiming(60, 20)
    assert station.sets[1].repetitions == 2


def test_repeated_number_headers_become_exercise_options():
    workout = WorkoutBuilder().build_workout(
        ParsedWorkout(
            name="Desert Heat",
            pods=1,
            stations="2 (cardio OR resistance)",
            sets="2",
            laps="2",
            timing=['40" work 20" rest'],
            exercises=[
                "1. burpees",
                "2. row erg",
                "1. floor row",
                "2. bicep curl",
            ],
        )
    )

    exercise_set = workout.pods[0].laps[0].stations[0].sets[0]
    assert workout.pods[0].laps[0].repetitions == 2
    assert exercise_set.repetitions == 2
    assert exercise_names(exercise_set) == ["burpees", "floor row"]


def test_pod_scoped_timing_splits_special_middle_pod():
    workout = WorkoutBuilder().build_workout(
        ParsedWorkout(
            name="Apollo",
            pods=3,
            stations="7",
            sets="1",
            laps="1",
            timing=[
                'pod 1&3 - 35" work 25" rest, 4 sets, 1 lap',
                "pod 2 - 11:45 work",
            ],
            exercises=[
                *(f"{number}. upper {number}" for number in range(1, 8)),
                *(f"{number}. lower {number}" for number in range(1, 8)),
            ],
        )
    )

    assert [len(pod.laps[0].stations) for pod in workout.pods] == [3, 1, 3]
    pod_1_set = workout.pods[0].laps[0].stations[0].sets[0]
    pod_2_set = workout.pods[1].laps[0].stations[0].sets[0]
    assert pod_1_set.repetitions == 4
    assert exercise_names(pod_1_set) == ["upper 1", "lower 1"]
    assert pod_1_set.timing == SetTiming(35, 25)
    assert pod_2_set.timing == SetTiming(
        705,
        0,
        TimingQualifier.ELEVEN_FORTYFIVE,
    )


def test_categories_can_be_derived_from_repository_exercises():
    class Repository:
        def get_exercise_by_name(self, exercise_name):
            if exercise_name == "row erg":
                return Exercise(name=exercise_name, target_muscle_groups=[MuscleGroup.HEART])
            return Exercise(name=exercise_name, target_muscle_groups=[MuscleGroup.LEGS])

    workout = WorkoutBuilder(Repository()).build_workout(
        ParsedWorkout(
            name="Hybrid",
            pods=1,
            stations="2",
            sets="1",
            laps="1",
            timing=['30" work 15" rest'],
            exercises=["1. row erg", "2. squat"],
        )
    )

    assert workout.categories == [WorkoutCategory.HYBRID]
