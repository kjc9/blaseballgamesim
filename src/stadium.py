from typing import Any, Dict, List

from common import StadiumStats


class Stadium(object):
    def __init__(
            self,
            team_id: str,
            stadium_id: str,
            name: str,
            mysticism: float,
            viscosity: float,
            elongation: float,
            obtuseness: float,
            forwardness: float,
            grandiosity: float,
            ominousness: float,
            mods: List[str],
    ):
        self.team_id = team_id
        self.stadium_id = stadium_id
        self.name = name
        self.stats: Dict[StadiumStats, float] = {
            StadiumStats.MYSTICISM: mysticism,
            StadiumStats.VISCOSITY: viscosity,
            StadiumStats.ELONGATION: elongation,
            StadiumStats.OBTUSENESS: obtuseness,
            StadiumStats.FORWARDNESS: forwardness,
            StadiumStats.GRANDIOSITY: grandiosity,
            StadiumStats.OMINOUSNESS: ominousness,
        }
        self.mods = mods
        self.has_peanut_mister = "PEANUT_MISTER" in mods
        self.has_big_buckets = "BIG_BUCKET" in mods

    def get_stadium_fv(self) -> List[float]:
        ret_val: List[float] = [
            self.stats[StadiumStats.MYSTICISM],
            self.stats[StadiumStats.VISCOSITY],
            self.stats[StadiumStats.ELONGATION],
            self.stats[StadiumStats.OBTUSENESS],
            self.stats[StadiumStats.FORWARDNESS],
            self.stats[StadiumStats.GRANDIOSITY],
            self.stats[StadiumStats.OMINOUSNESS],
        ]
        return ret_val

    def to_dict(self) -> Dict[str, Any]:
        """Gets a dict representation of the state for serialization"""
        serialization_dict = {
            "team_id": self.team_id,
            "stadium_id": self.stadium_id,
            "name": self.name,
            "stats": Stadium.convert_stats(self.stats),
            "mods": self.mods,
        }
        return serialization_dict

    @classmethod
    def convert_stats(cls, encoded: Dict[StadiumStats, float]) -> Dict[int, float]:
        ret_val: Dict[int, float] = {}
        for key in encoded:
            ret_val[key.value] = encoded[key]
        return ret_val

    @classmethod
    def encode_stats(cls, raw: Dict[int, float]) -> Dict[StadiumStats, float]:
        ret_val: Dict[StadiumStats, float] = {}
        for key in raw:
            ret_val[StadiumStats(int(key))] = float(raw[key])
        return ret_val

    @classmethod
    def from_config(cls, raw: Dict[str, Any]):
        team_id: str = raw["team_id"]
        stadium_id: str = raw["stadium_id"]
        name: str = raw["name"]
        stats: Dict[StadiumStats, float] = Stadium.encode_stats(raw["stats"])
        mods: List[str] = raw["mods"]
        return cls(
            team_id,
            stadium_id,
            name,
            stats[StadiumStats.MYSTICISM],
            stats[StadiumStats.VISCOSITY],
            stats[StadiumStats.ELONGATION],
            stats[StadiumStats.OBTUSENESS],
            stats[StadiumStats.FORWARDNESS],
            stats[StadiumStats.GRANDIOSITY],
            stats[StadiumStats.OMINOUSNESS],
            mods,
        )

    @classmethod
    def from_ballpark_json(cls, raw: Dict[str, Any]):
        return cls(
            raw["data"]["teamId"],
            raw["data"]["id"],
            raw["data"]["name"],
            raw["data"]["mysticism"],
            raw["data"]["viscosity"],
            raw["data"]["elongation"],
            raw["data"]["obtuseness"],
            raw["data"]["forwardness"],
            raw["data"]["grandiosity"],
            raw["data"]["ominousness"],
            raw["data"]["mods"],
        )
