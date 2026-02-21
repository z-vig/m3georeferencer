from dataclasses import dataclass, field
from m3georeferencer.pkgtypes import AppMode
from m3georeferencer.services.gcp_model import GCPGroup


@dataclass
class AppState:
    mode: AppMode = AppMode.IDLE
    gcp_group: GCPGroup = field(default_factory=GCPGroup.empty)
