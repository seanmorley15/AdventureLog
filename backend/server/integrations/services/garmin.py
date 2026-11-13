"""Garmin attribution for activity data that came from a Garmin device (#895).

Since 1 November 2025 the Strava API terms require apps that show Garmin-sourced activity data
to credit Garmin the way Garmin's API brand guidelines ask: "Garmin [device model]" next to the
activity's title, or "Garmin" alone when the model is unknown.
"""

GARMIN = 'Garmin'


def garmin_attribution(device_name: str | None, external_id: str | None = None) -> str | None:
    """
    The credit line for an activity, or None when nothing says it came from Garmin.

    Strava's detailed activity names the device ("Garmin Forerunner 965"); its activity list
    does not, but an upload synced from Garmin Connect has an ``external_id`` such as
    ``garmin_ping_123456789``.
    """
    device = (device_name or '').strip()
    if 'garmin' in device.lower():
        if device.lower().startswith('garmin'):
            return GARMIN + device[len(GARMIN):]
        return f'{GARMIN} {device}'
    if (external_id or '').strip().lower().startswith('garmin'):
        return GARMIN
    return None
