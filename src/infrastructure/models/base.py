"""
This model includes basic data models that are used in the whole application.
"""

import json
from typing import TypeVar

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Extra

__all__ = ("InternalModel", "_InternalModel", "PublicModel", "_PublicModel")


def to_camelcase(string: str) -> str:
    """The alias generator for PublicModel."""

    resp = "".join(
        word.capitalize() if index else word
        for index, word in enumerate(string.split("_"))
    )
    return resp


_json_encoders = {np.float32: lambda v: float(v) if v else None}


class InternalModel(BaseModel):
    class Config:
        json_encoders = _json_encoders
        extra = Extra.forbid
        orm_mode = True
        use_enum_values = True
        allow_population_by_field_name = True
        validate_assignment = True
        arbitrary_types_allowed = True

    def flat_dict(self) -> dict:
        """This method might be useful is the data should be passed
        only with primitives that are allowed by JSON format.
        """
        return json.loads(self.json())


_InternalModel = TypeVar("_InternalModel", bound=InternalModel)


class PublicModel(BaseModel):
    class Config:
        json_encoders = _json_encoders
        extra = Extra.ignore
        orm_mode = True
        use_enum_values = True
        validate_assignment = True
        alias_generator = to_camelcase
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

    def encoded_dict(self, by_alias=True) -> dict:
        """This method might be useful is the data should be passed
        only with primitives that are allowed by JSON format.
        The regular .dict() does not return the ISO datetime format
        but the .json() - does. This method is a combination of them.
        """
        return json.loads(self.json(by_alias=by_alias))


_PublicModel = TypeVar("_PublicModel", bound=PublicModel)
