/**
 * explore_mode.js — Lakán Campus Explore Mode
 * Shows all campus buildings as clickable markers on the map
 * Integrates with existing navigation engine and GPS
 */

(function() {

// ── CONFIG ───────────────────────────────────────────────────
const EXCLUDED_IDS = ['Gate 1', 'Gate 2', 'Gate 3', 'Gate 4'];

const FULL_NAMES = {
    'Admin': 'Ayuntamiento de Gonzalez',
    'Alumni': 'Alumni Center',
    'bahay_pagasa_dasmariñas': 'Bahay Pag-asa Dasmariñas',
    'Botanical Garden': 'Botanical Garden',
    'CBAA': 'College of Business Administration and Accountancy',
    'CEAT': 'College of Engineering, Architecture and Technology',
    'Chapel': 'Chapel',
    'CTH': 'Candido Tirona Hall',
    'CTHM': 'College of Tourism and Hospitality Management',
    'FCH': 'Felipe Calderon Hall',
    'FDH': 'Dr. Fe Del Mundo Hall',
    'GMH': 'Gregorio Montoya Hall',
    'Grandstand': 'Grandstand',
    'high_school_complex': 'High School Complex',
    'hotel_rafael': 'Hotel Rafael',
    'ICTC': 'Information and Communications Technology Center',
    'JFH': 'Julian Felipe Hall',
    'Ladies Dorm': 'Ladies Dormitory',
    'LDH': 'Ladislao Diwa Hall',
    'Library': 'Rizal Library',
    'Mens Dorm': 'Mens Dormitory',
    'MTH': 'Mariano Trias Hall',
    'Museo': 'Museo De La Salle',
    'PCH': 'Pablo Campos Hall',
    'Residencia': 'Residencia de San Miguel',
    'Square': 'University Square',
    'ULS': 'Ugnayang La Salle',
    'VBH': 'Vito Belarmino Hall',
};

const ICONS = {
    'Admin': '🏛️', 'Library': '📚', 'Chapel': '⛪', 'Square': '🍽️',
    'Grandstand': '🏟️', 'Museo': '🏺', 'Botanical Garden': '🌿',
    'Ladies Dorm': '🏠', 'Mens Dorm': '🏠', 'ULS': '🏫',
    'CBAA': '💼', 'CEAT': '⚙️', 'CTHM': '🍽️', 'JFH': '🏢',
    'GMH': '🏢', 'LDH': '🏢', 'MTH': '🏢', 'VBH': '🏢',
    'FCH': '🏢', 'PCH': '🏢', 'ICTC': '💻', 'Alumni': '🎓',
    'Residencia': '🏠', 'high_school_complex': '🏫',
    'hotel_rafael': '🏨', 'Botanical Garden': '🌿',
    'bahay_pagasa_dasmariñas': '🏢',
};

const DESCRIPTIONS = {
    'Admin': 'The main administration building of DLSU-D, housing university offices and administrative services.',
    'CBAA': 'Home to the College of Business Administration and Accountancy programs.',
    'CEAT': 'Houses the College of Engineering, Architecture and Technology.',
    'CTHM': 'The College of Tourism and Hospitality Management building.',
    'JFH': 'Julian Felipe Hall — a multi-purpose academic building.',
    'Library': 'The Rizal Library — the main academic library of DLSU-D with extensive resources.',
    'Chapel': 'The DLSU-D Chapel, open for masses, prayers, and spiritual activities.',
    'Square': 'The University Square — an open-air area with food stalls and small stores.',
    'Grandstand': 'The DIHS Grandstand, used for major campus events and activities.',
    'Museo': 'Museo De La Salle — showcasing La Sallian heritage and history.',
    'Botanical Garden': 'A green space featuring various plant species within the campus.',
    'ULS': 'Ugnayang La Salle — the La Salle integrated school complex.',
    'GMH': 'Gregorio Montoya Hall — academic building.',
    'LDH': 'Ladislao Diwa Hall — academic building.',
    'MTH': 'Mariano Trias Hall — academic building.',
    'FCH': 'Felipe Calderon Hall — academic building.',
    'PCH': 'Pablo Campos Hall — academic building.',
    'VBH': 'Vito Belarmino Hall — academic building.',
    'ICTC': 'Information and Communications Technology Center.',
    'Ladies Dorm': 'Ladies Dormitory — residential facility for female students.',
    'Mens Dorm': 'Mens Dormitory — residential facility for male students.',
    'FDH': 'Dr. Fe Del Mundo Hall — formerly the College of Sciences building.',
    'Residencia': 'Residencia de San Miguel — residential facility.',
    'Alumni': 'Alumni Center — for DLSU-D alumni activities and events.',
    'high_school_complex': 'The DLSU-D High School Complex.',
    'hotel_rafael': 'Hotel Rafael — on-campus hospitality training facility.',
    'bahay_pagasa_dasmariñas': 'Bahay Pag-asa Dasmariñas — community outreach center.',
};

// ── STATE ────────────────────────────────────────────────────
let exploreActive = false;
let exploreMarkers = [];
let allBuildings = [];
let currentBuilding = null;

// ── INIT ─────────────────────────────────────────────────────
function initExploreMode() {
    injectStyles();
    injectModal();
    console.log('🗺️ Explore Mode initialized');
}

// ── TOGGLE ───────────────────────────────────────────────────
async function toggleExploreMode() {
    exploreActive = !exploreActive;
    const btn = document.getElementById('exploreModeBtn');

    if (exploreActive) {
        btn.style.background = '#C8A951';
        btn.style.color = '#1a1a1a';
        btn.title = 'Exit Explore Mode';
        btn.innerHTML = '<i class="fas fa-times"></i>';
        await loadAndPlotBuildings();
    } else {
        exitExploreMode();
    }
}

function exitExploreMode() {
    exploreActive = false;
    const btn = document.getElementById('exploreModeBtn');
    if (btn) {
        btn.style.background = '';
        btn.style.color = '';
        btn.title = 'Explore Campus';
        btn.innerHTML = '<i class="fas fa-compass"></i>';
    }
    clearExploreMarkers();
    closeExploreModal();
}

// ── LOAD BUILDINGS ────────────────────────────────────────────
async function loadAndPlotBuildings() {
    try {
        const res = await fetch('/get-all-locations');
        allBuildings = await res.json();

        allBuildings
            .filter(b => !EXCLUDED_IDS.includes(b.id))
            .forEach(b => plotBuilding(b));

        // Fit to campus
        if (window.map) {
            window.map.fitBounds([
                [14.3188, 120.9558],
                [14.3295, 120.9650]
            ], { padding: [30, 30], animate: true });
        }
    } catch(e) {
        console.error('Explore mode: failed to load buildings', e);
    }
}

// ── PLOT MARKER ───────────────────────────────────────────────
function plotBuilding(building) {
    if (!window.map) return;
    const displayName = FULL_NAMES[building.id] || building.name || building.id;
    const shortName = building.id.length <= 5
        ? building.id
        : (displayName.length > 16 ? displayName.substring(0, 14) + '…' : displayName);

    const icon = L.divIcon({
        className: '',
        html: `<div class="explore-pin" onclick="window.__exploreTap('${building.id}')">${shortName}</div>`,
        iconAnchor: [0, 0]
    });

    const marker = L.marker(building.coordinates, { icon }).addTo(window.map);
    exploreMarkers.push(marker);
}

// ── CLEAR MARKERS ─────────────────────────────────────────────
function clearExploreMarkers() {
    exploreMarkers.forEach(m => m.remove());
    exploreMarkers = [];
}

// ── OPEN MODAL ────────────────────────────────────────────────
window.__exploreTap = function(buildingId) {
    const building = allBuildings.find(b => b.id === buildingId);
    if (!building) return;
    currentBuilding = building;

    const displayName = FULL_NAMES[buildingId] || building.name || buildingId;
    const icon = ICONS[buildingId] || '🏢';
    const desc = DESCRIPTIONS[buildingId] || `${displayName} is a facility within the DLSU-Dasmariñas campus.`;

    document.getElementById('exploreModalIcon').textContent = icon;
    document.getElementById('exploreModalName').textContent = displayName;
    document.getElementById('exploreModalDesc').textContent = desc;
    document.getElementById('exploreNavBtn').dataset.buildingId = buildingId;
    document.getElementById('exploreModal').style.display = 'flex';

    // Fly to building
    if (window.map) window.map.flyTo(building.coordinates, 19, { animate: true, duration: 0.8 });
};

// ── CLOSE MODAL ───────────────────────────────────────────────
function closeExploreModal() {
    document.getElementById('exploreModal').style.display = 'none';
    currentBuilding = null;
}

// ── NAVIGATE ─────────────────────────────────────────────────
function exploreNavigate() {
    const btn = document.getElementById('exploreNavBtn');
    const buildingId = btn ? btn.dataset.buildingId : null;
    if (!buildingId) return;

    closeExploreModal();
    exitExploreMode();

    const hasGPS = window.userGPSLocation || (window.adminMode && window.adminMode.customLocation);
    if (hasGPS && window.adminMode) {
        window.adminMode.customLocation = window.userGPSLocation || window.adminMode.customLocation;
        window.adminMode.enabled = true;
    }

    if (window.showNavigation) {
        window.showNavigation('Gate 1', buildingId);
    }
}

// ── INJECT STYLES ─────────────────────────────────────────────
function injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .explore-pin {
            background: #006341;
            color: white;
            padding: 4px 9px;
            border-radius: 6px;
            font-size: 10.5px;
            font-weight: 700;
            white-space: normal;
            max-width: 120px;
            text-align: center;
            line-height: 1.3;
            box-shadow: 0 2px 8px rgba(0,0,0,0.35);
            cursor: pointer;
            border: 1.5px solid rgba(255,255,255,0.25);
            transition: transform 0.15s, background 0.15s;
        }
        .explore-pin:hover {
            background: #004d30;
            transform: scale(1.06);
        }

        #exploreModal {
            position: fixed;
            inset: 0;
            z-index: 99998;
            display: none;
            align-items: flex-end;
            justify-content: center;
        }
        .explore-backdrop {
            position: absolute;
            inset: 0;
            background: rgba(0,0,0,0.45);
            backdrop-filter: blur(3px);
        }
        .explore-sheet {
            position: relative;
            background: #0f2318;
            border-radius: 22px 22px 0 0;
            width: 100%;
            max-width: 500px;
            padding: 20px 22px 28px;
            border-top: 1px solid rgba(0,99,65,0.4);
            animation: exploreSlideUp 0.28s ease;
            z-index: 1;
        }
        @keyframes exploreSlideUp {
            from { transform: translateY(100%); }
            to { transform: translateY(0); }
        }
        .explore-handle {
            width: 36px; height: 4px;
            background: rgba(255,255,255,0.15);
            border-radius: 2px;
            margin: 0 auto 16px;
        }
        .explore-modal-icon { font-size: 30px; display: block; margin-bottom: 6px; }
        .explore-modal-name {
            font-size: 18px;
            font-weight: 800;
            color: white;
            margin-bottom: 10px;
            line-height: 1.3;
        }
        .explore-modal-desc {
            font-size: 13px;
            color: rgba(255,255,255,0.7);
            line-height: 1.65;
            margin-bottom: 18px;
        }
        .explore-modal-btns { display: flex; gap: 10px; }
        .explore-btn-nav {
            flex: 1;
            background: #006341;
            color: white;
            border: none;
            border-radius: 12px;
            padding: 13px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            transition: background 0.2s;
        }
        .explore-btn-nav:hover { background: #004d30; }
        .explore-btn-close {
            background: rgba(255,255,255,0.08);
            color: white;
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 12px;
            padding: 13px 18px;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .explore-btn-close:hover { background: rgba(255,255,255,0.15); }
    `;
    document.head.appendChild(style);
}

// ── INJECT MODAL ─────────────────────────────────────────────
function injectModal() {
    const modal = document.createElement('div');
    modal.id = 'exploreModal';
    modal.innerHTML = `
        <div class="explore-backdrop" onclick="window.__exploreClose()"></div>
        <div class="explore-sheet">
            <div class="explore-handle"></div>
            <span class="explore-modal-icon" id="exploreModalIcon">🏢</span>
            <div class="explore-modal-name" id="exploreModalName">Building</div>
            <div class="explore-modal-desc" id="exploreModalDesc"></div>
            <div class="explore-modal-btns">
                <button class="explore-btn-nav" id="exploreNavBtn" onclick="window.__exploreNavigate()">
                    🗺️ Navigate Here
                </button>
                <button class="explore-btn-close" onclick="window.__exploreClose()">✕ Close</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

// ── EXPOSE GLOBALS ────────────────────────────────────────────
window.__exploreClose = closeExploreModal;
window.__exploreNavigate = exploreNavigate;
window.toggleExploreMode = toggleExploreMode;

// ── AUTO INIT ─────────────────────────────────────────────────
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initExploreMode);
} else {
    initExploreMode();
}

})();
