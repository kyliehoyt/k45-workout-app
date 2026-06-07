"""
This module defines the Workout model in the K45 system.
"""

from dataclasses import dataclass
import enum

from data_acquisition.src.models.exercise import Exercise
from data_acquisition.src.models.set_timing import SetTiming


class WorkoutCategory(enum.Enum):
    """
    This enum represents the different categories that K45 workouts can belong to.
    """

    RESISTANCE = "Resistance"
    CARDIO = "Cardio"
    HYBRID = "Hybrid"
    RECOVERY = "Recovery"


@dataclass
class ExerciseSet:
    """
    Represents a set of an exercise performed at a station. It includes the exercise being performed
    and the timing for the set.
     Attributes:
        exercises (Exercise): The exercises that could be performed in the set. Only one 
        exercise will be performed in a given set, but multiple options are provided to allow for 
        variety and substitutions.    
        set_timing (SetTiming): The timing for the set, including work and rest durations.
    """

    exercises: list[Exercise]
    timing: SetTiming


@dataclass
class Station:
    """
    Represents a station, which is a specific exercise or activity that is performed as part of a
    workout. 1 or more sets are performed at a station before advancing to the next station.
     Attributes:
        sets (list[ExerciseSet]): A list of sets that are performed at the station. Each 
        set includes an exercise and its timing.
    """
    sets: list[ExerciseSet]


@dataclass
class Lap:
    """
    Represents a lap, which is a single round of performing the stations in a pod.
     Attributes:
        stations (list[Station]): The stations that belong to the lap. Stations can be 
        performed in any order within the lap, but all stations must be completed before 
        advancing to the next lap.   
    """
    stations: list[Station]


@dataclass
class Pod:
    """
    Represents a pod, which is a group of stations that are performed together in a workout. 1 or
     more laps are performed within a pod before advancing to the next pod.
     Attributes:
        laps (list[Lap]): The laps of stations that are to be performed in the pod. Laps 
        are performed in order and listed out because SetTiming may differ between laps.
    """

    laps: list[Lap]


@dataclass
class Workout:
    """
    Represents a workout, which includes its name, category, description, and various parameters
    related to the structure of the workout.
     Attributes:
        name (str): The name of the workout.
        category (WorkoutCategory): The category that the workout belongs to.
        description (str): A brief description of the workout.
        pods (list[Pod]): An ordered list of pods that belong to the workout. Each pod 
        includes a list of stations.
    """

    name: str
    category: WorkoutCategory
    description: str = ""
    pods: list[Pod] = None
