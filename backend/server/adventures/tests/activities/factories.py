"""Builders for activity files in every supported format, from one description of a recording."""

import io
import math
import struct
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from adventures.services.activities.track import TrackPoint

START = datetime(2026, 6, 6, 8, 0, 0, tzinfo=timezone.utc)
METERS_PER_DEGREE = 111_195.0  # one degree of latitude


@dataclass
class Sample:
    """One recorded second: ``north`` meters from the start, an altitude and optional heart rate."""

    seconds: int
    north: float
    ele: float | None = None
    hr: int | None = None

    def point(self, lon=2.0, lat=41.0):
        return TrackPoint(
            lat=lat + self.north / METERS_PER_DEGREE,
            lon=lon,
            ele=self.ele,
            time=START + timedelta(seconds=self.seconds),
            heart_rate=self.hr,
        )


def walk(seconds, speed=1.4, ele=lambda i: 100.0, hr=None, start=0):
    """A straight walk north at ``speed`` m/s, one sample a second."""
    return [
        Sample(start + i, i * speed, ele(i), hr(i) if hr else None)
        for i in range(seconds)
    ]


def points(samples):
    return [sample.point() for sample in samples]


def _iso(moment):
    return moment.strftime('%Y-%m-%dT%H:%M:%SZ')


def make_gpx(samples, name='Morning Hike', kind='hiking', waypoints=()):
    trkpts = ''
    for sample in samples:
        p = sample.point()
        ele = f'<ele>{p.ele}</ele>' if p.ele is not None else ''
        extension = (
            f'<extensions><gpxtpx:TrackPointExtension><gpxtpx:hr>{p.heart_rate}</gpxtpx:hr>'
            '</gpxtpx:TrackPointExtension></extensions>' if p.heart_rate is not None else ''
        )
        trkpts += f'<trkpt lat="{p.lat}" lon="{p.lon}">{ele}<time>{_iso(p.time)}</time>{extension}</trkpt>'
    wpts = ''.join(f'<wpt lat="{lat}" lon="{lon}"><ele>{ele}</ele></wpt>' for lat, lon, ele in waypoints)
    return (
        '<?xml version="1.0"?><gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1" '
        'xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">'
        f'{wpts}<trk><name>{name}</name><type>{kind}</type><trkseg>{trkpts}</trkseg></trk></gpx>'
    ).encode()


def make_tcx(samples, sport='Running', total_seconds=None, distance=None, calories=None):
    trackpoints = ''
    for sample in samples:
        p = sample.point()
        hr = f'<HeartRateBpm><Value>{p.heart_rate}</Value></HeartRateBpm>' if p.heart_rate is not None else ''
        ele = f'<AltitudeMeters>{p.ele}</AltitudeMeters>' if p.ele is not None else ''
        trackpoints += (
            f'<Trackpoint><Time>{_iso(p.time)}</Time><Position><LatitudeDegrees>{p.lat}</LatitudeDegrees>'
            f'<LongitudeDegrees>{p.lon}</LongitudeDegrees></Position>{ele}{hr}</Trackpoint>'
        )
    totals = ''
    if total_seconds is not None:
        totals += f'<TotalTimeSeconds>{total_seconds}</TotalTimeSeconds>'
    if distance is not None:
        totals += f'<DistanceMeters>{distance}</DistanceMeters>'
    if calories is not None:
        totals += f'<Calories>{calories}</Calories>'
    return (
        '<?xml version="1.0"?><TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">'
        f'<Activities><Activity Sport="{sport}"><Id>{_iso(START)}</Id><Lap StartTime="{_iso(START)}">{totals}'
        f'<Track>{trackpoints}</Track></Lap></Activity></Activities></TrainingCenterDatabase>'
    ).encode()


def make_kml(samples, name='Ridge walk'):
    coordinates = ' '.join(f'{p.lon},{p.lat},{p.ele or 0}' for p in (s.point() for s in samples))
    return (
        '<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        f'<name>{name}</name><Placemark><LineString><coordinates>{coordinates}</coordinates></LineString>'
        '</Placemark></Document></kml>'
    ).encode()


def make_kmz(samples, name='Ridge walk'):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('doc.kml', make_kml(samples, name))
    return buffer.getvalue()


# ---- FIT: a tiny encoder for the few messages the reader uses --------------------------------

_CRC_TABLE = [
    0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
]
_FIT_EPOCH = datetime(1989, 12, 31, tzinfo=timezone.utc)
_UINT8, _ENUM, _UINT16, _SINT32, _UINT32 = 0x02, 0x00, 0x84, 0x85, 0x86


def _crc(data, crc=0):
    for byte in data:
        tmp = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE[byte & 0xF]
        tmp = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE[(byte >> 4) & 0xF]
    return crc


def _fit_time(moment):
    return int((moment - _FIT_EPOCH).total_seconds())


def _semicircles(degrees):
    return int(round(degrees * 2**31 / 180))


def _definition(local, global_number, fields):
    body = struct.pack('<BBBHB', 0x40 | local, 0, 0, global_number, len(fields))
    for number, size, base in fields:
        body += struct.pack('<BBB', number, size, base)
    return body


def _data(local, fmt, *values):
    return bytes([local]) + struct.pack('<' + fmt, *values)


def make_fit(samples, sport=1, sub_sport=0, ascent=None, descent=None, calories=None,
             pause_after=None, utc_offset_hours=None, total_distance=None):
    """
    A FIT activity: ``record`` for every sample, a ``session`` with the device totals (the
    distance and altitude gain it is given), and a timer stop/start around ``pause_after``.
    """
    body = b''
    body += _definition(0, 20, [(253, 4, _UINT32), (0, 4, _SINT32), (1, 4, _SINT32), (2, 2, _UINT16), (3, 1, _UINT8)])
    body += _definition(1, 21, [(253, 4, _UINT32), (0, 1, _ENUM), (1, 1, _ENUM)])
    for sample in samples:
        p = sample.point()
        if pause_after is not None and sample.seconds == pause_after:
            body += _data(1, 'IBB', _fit_time(p.time), 0, 4)  # timer, stop_all
        record_ele = int(round(((p.ele or 0) + 500) * 5))
        body += _data(0, 'IiiHB', _fit_time(p.time), _semicircles(p.lat), _semicircles(p.lon), record_ele, p.heart_rate or 0)
        if pause_after is not None and sample.seconds == pause_after:
            body += _data(1, 'IBB', _fit_time(p.time), 0, 0)  # timer, start
    first, last = samples[0].point(), samples[-1].point()
    elapsed = (last.time - first.time).total_seconds()
    distance = total_distance if total_distance is not None else samples[-1].north
    body += _definition(2, 18, [
        (253, 4, _UINT32), (2, 4, _UINT32), (7, 4, _UINT32), (8, 4, _UINT32), (9, 4, _UINT32),
        (11, 2, _UINT16), (5, 1, _ENUM), (6, 1, _ENUM), (22, 2, _UINT16), (23, 2, _UINT16),
    ])
    body += _data(
        2, 'IIIIIHBBHH', _fit_time(last.time), _fit_time(first.time), int(elapsed * 1000), int(elapsed * 1000),
        int(distance * 100), calories or 0xFFFF, sport, sub_sport,
        ascent if ascent is not None else 0xFFFF, descent if descent is not None else 0xFFFF,
    )
    if utc_offset_hours is not None:
        body += _definition(3, 34, [(253, 4, _UINT32), (5, 4, _UINT32)])
        body += _data(3, 'II', _fit_time(last.time), _fit_time(last.time) + utc_offset_hours * 3600)
    header = struct.pack('<BBHI4s', 14, 0x20, 2100, len(body), b'.FIT')
    header += struct.pack('<H', _crc(header))
    payload = header + body
    return payload + struct.pack('<H', _crc(payload))


def hill(i, rise=100.0, length=600):
    """Altitude for second ``i``: a steady climb of ``rise`` meters over ``length`` seconds, then flat."""
    return 100.0 + rise * min(i, length) / length


def noisy_flat(i):
    """Flat ground read by an altimeter that wobbles +-4 m."""
    return 100.0 + 4.0 * math.sin(i * 1.3) * (1 if i % 2 else -1)
