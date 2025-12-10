"""
Sport-specific training modules.
"""

from .running import RUNNING_MODULE
from .swimming import SWIMMING_MODULE
from .triathlon import TRIATHLON_MODULE

__all__ = ['RUNNING_MODULE', 'SWIMMING_MODULE', 'TRIATHLON_MODULE']

