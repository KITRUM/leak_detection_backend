"""The units registry module."""
from pint import UnitRegistry

# NOTE: This constant should be used for all variables that have quantity
#       and are used with different measurements in different cases.
ureg = UnitRegistry()
