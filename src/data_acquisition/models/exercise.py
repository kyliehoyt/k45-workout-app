"""
This module defines the Exercise data model.
"""

from dataclasses import dataclass, field
import enum

from data_acquisition.models.equipment import EquipmentOption


class MuscleGroup(enum.Enum):
    """
    This enum represents the different muscle groups that can be targeted by exercises. It includes
    both traditional muscle groups (like chest, back, legs) and a category for cardio exercises
    (heart).
    """

    CHEST = "Chest"
    BACK = "Back"
    LEGS = "Legs"
    ARMS = "Arms"
    SHOULDERS = "Shoulders"
    CORE = "Core"
    HEART = "Heart"  # Cardio


@dataclass
class Exercise:
    """
    This data class represents an exercise, which includes its name, description, visual
    representation, required equipment, and target muscle groups.
     Attributes:
        name (str): The name of the exercise.
        description (str): A brief description of the exercise.
        visual_url (str): The URL of the visual representation of the exercise.
        required_equipment (list[EquipmentOption]): The equipment required for the exercise.
        target_muscle_groups (list[MuscleGroup]): The muscle groups targeted by the exercise.
    """

    name: str
    description: str = ""
    visual_url: str = ""
    required_equipment: list[EquipmentOption] = field(default_factory=list)
    target_muscle_groups: list[MuscleGroup] = field(default_factory=list)
