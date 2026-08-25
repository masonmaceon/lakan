// Geofence for the DLSU-D campus — shared by the desktop and mobile pages.
// The team's official bounding box (previously defined only in admin_mode.js;
// now the single source of truth, mirrored server-side in geofence.py).
const CAMPUS_BOUNDS = { north: 14.3290, south: 14.3195, east: 120.9650, west: 120.9575 };

function isInsideCampus(lat, lng) {
    if (lat === null || lng === null || lat === undefined || lng === undefined) return false;
    return lat >= CAMPUS_BOUNDS.south && lat <= CAMPUS_BOUNDS.north &&
           lng >= CAMPUS_BOUNDS.west && lng <= CAMPUS_BOUNDS.east;
}

window.isInsideCampus = isInsideCampus;
window.CAMPUS_BOUNDS = CAMPUS_BOUNDS;
