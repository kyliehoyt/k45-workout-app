"""
This module defines the Exercise data model.
"""

from dataclasses import dataclass


@dataclass
class Exercise:
    """
    This data class represents a canonical exercise movement, independent of a
    workout's prescribed equipment.
     Attributes:
        name (str): The name of the exercise.
    """

    name: str
