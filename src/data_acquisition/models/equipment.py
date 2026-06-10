"""
This module defines the Equipment data model, which represents a piece of equipment used
in exercises.
"""

from dataclasses import dataclass


@dataclass
class Equipment:
    """
    Represents a piece of equipment used in exercises.
     Attributes:
        name (str): The name of the equipment.
    """

    name: str


@dataclass
class EquipmentOption:
    """
    Represents an equipment option for an exercise. It includes the primary equipment and any
    substitutes that can be used in place of it.
    """

    option: Equipment
    substitutes: list[Equipment] = None
