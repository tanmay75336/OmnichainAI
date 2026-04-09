from dataclasses import dataclass


@dataclass(frozen=True)
class RouteRequest:
    source: str
    destination: str
    transport_mode: str
    region_type: str

    def __post_init__(self):
        normalized_mode = self.transport_mode.strip().lower()
        normalized_region = self.region_type.strip().lower().replace("-", "_").replace(" ", "_")

        object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "destination", self.destination.strip())
        object.__setattr__(self, "transport_mode", normalized_mode)
        object.__setattr__(self, "region_type", normalized_region)
