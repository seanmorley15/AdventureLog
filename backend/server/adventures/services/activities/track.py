"""The format-neutral shape every activity file is read into."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class TrackPoint:
    """One recorded position. ``time`` is timezone-aware UTC when the file has timestamps."""

    lat: float
    lon: float
    ele: float | None = None
    time: datetime | None = None
    heart_rate: float | None = None
    cadence: float | None = None


@dataclass
class DeviceSummary:
    """
    Totals a recording device or provider reported itself (a FIT session, a TCX lap).

    These are more reliable than anything derived from the points (a barometric altimeter
    beats GPS altitude), so they win over computed values.
    """

    distance: float | None = None  # meters
    elevation_gain: float | None = None  # meters
    elevation_loss: float | None = None  # meters
    moving_time: timedelta | None = None
    elapsed_time: timedelta | None = None
    average_speed: float | None = None  # m/s
    max_speed: float | None = None  # m/s
    calories: float | None = None
    average_cadence: float | None = None
    average_heart_rate: float | None = None
    max_heart_rate: float | None = None
    start_time: datetime | None = None
    utc_offset: timedelta | None = None


@dataclass
class Track:
    """A recorded activity: ordered point segments plus whatever the file said about itself."""

    segments: list[list[TrackPoint]] = field(default_factory=list)
    name: str | None = None
    sport: str | None = None
    sub_sport: str | None = None  # a FIT sub_sport, more specific than ``sport``
    format: str = 'gpx'
    summary: DeviceSummary = field(default_factory=DeviceSummary)

    @property
    def points(self) -> list[TrackPoint]:
        return [point for segment in self.segments for point in segment]
