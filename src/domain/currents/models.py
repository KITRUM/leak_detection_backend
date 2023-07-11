import numpy as np

from src.infrastructure.models import InternalModel

__all__ = ("Current",)


class Current(InternalModel):
    """The subsea current."""

    u: np.float32  # unit: m/s
    v: np.float32  # unit: m/s
    magnitude: np.float32  # unit: m/s
    angle_from_north: np.float32  # in radians, positive toward east

    @classmethod
    def from_raw(cls, data: dict) -> "Current":
        u = np.float32(data["u"])
        v = np.float32(data["v"])

        # TODO:: Add the current_u_v_components parameter condition
        #   if self.options.current_u_v_components:
        #       currents[i, 0:2] = current.u, current.v
        #       currents[i, 2:4] = current.magnitude, current.angle_from_north
        #   else:
        #       # assuming current magnitude is given in m/s
        #       currents[i, 2] = current.u
        #       # assuming direction is given in radians
        #       currents[i, 3] = current.v

        return cls(
            u=u,
            v=v,
            magnitude=np.float32(np.sqrt(u**2 + v**2)),
            angle_from_north=np.float32(np.arctan2(u, v)),
        )
