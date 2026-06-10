"""
This module defines the SetTiming data model, which represents the timing for a set in a workout,
including work and rest durations.
"""

from dataclasses import dataclass
import enum


class TimingQualifier(enum.Enum):
    """
    This enum represents qualifiers for the timing of a set. It can be used to indicate whether the
    timing of a set has special characteristics.
    """

    # Two people alternate performing the set, with one person working while the other rests
    YOU_GO_I_GO = "You Go, I Go"
    # Move as much as possible in 11 minutes and 45 seconds
    ELEVEN_FORTYFIVE = "11:45"


@dataclass
class SetTiming:
    """
    Represents the timing for a set in a workout.
     Attributes:
        work_duration_seconds (int): The duration of the work phase in seconds.
        rest_duration_seconds (int): The duration of the rest phase in seconds.
        timing_qualifier (TimingQualifier): An optional qualifier for the timing of the set.
    """

    work_duration_seconds: int
    rest_duration_seconds: int
    timing_qualifier: TimingQualifier | None = None
