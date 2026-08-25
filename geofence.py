"""
Lakán DLSU-D — campus geofence (server-side mirror of static/js/geofence.js).

This is the team's official geofence: the bounding box originally defined
in admin_mode.js ("specific coordinates created for the geofence").
Map features (routing, building reveals) are on-campus only — the chat API
refuses those actions to users outside (or without) a verified location.
"""

# DLSU-D campus geofence bounds
CAMPUS_BOUNDS = {
    "north": 14.3290,
    "south": 14.3195,
    "east": 120.9650,
    "west": 120.9575,
}


def inside_campus(lat, lng) -> bool:
    """True only for points inside the official campus bounding box."""
    if lat is None or lng is None:
        return False
    return (CAMPUS_BOUNDS["south"] <= lat <= CAMPUS_BOUNDS["north"]
            and CAMPUS_BOUNDS["west"] <= lng <= CAMPUS_BOUNDS["east"])
