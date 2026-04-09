/*
Admin Mode - COMPACT VERSION (doesn't block view)
*/

let adminMode = {
    enabled: false,
    customLocation: null,
    marker: null
};

function initAdminMode() {
    // Create compact admin mode button
    const adminButton = document.createElement('button');
    adminButton.id = 'admin-mode-btn';
    adminButton.innerHTML = '🔧';
    adminButton.title = 'Admin Mode: OFF';
    adminButton.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        z-index: 99999;
        padding: 10px;
        background: #dc3545;
        color: white;
        border: none;
        border-radius: 50%;
        width: 45px;
        height: 45px;
        font-size: 20px;
        cursor: pointer;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        display: none;
        align-items: center;
        justify-content: center;
    `;
    
    adminButton.onclick = toggleAdminMode;
    document.body.appendChild(adminButton);
    
    // Create COMPACT info panel (hidden by default)
    const infoPanel = document.createElement('div');
    infoPanel.id = 'admin-info-panel';
    infoPanel.style.cssText = `
        position: fixed;
        top: 135px;
        right: 20px;
        z-index: 99999;
        padding: 12px;
        background: rgba(0, 99, 65, 0.95);
        color: white;
        border-radius: 8px;
        width: 220px;
        display: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        font-size: 12px;
    `;
    infoPanel.innerHTML = `
        <div style="font-weight: bold; margin-bottom: 8px; font-size: 13px;">📍 Admin Mode</div>
        <div style="margin-bottom: 8px;">Click map to set location</div>
        <div id="admin-location-coords" style="font-family: monospace; background: rgba(0,0,0,0.3); padding: 4px; border-radius: 4px; font-size: 10px; margin-bottom: 8px;">
            No location set
        </div>
        <button id="admin-reset-btn" style="padding: 6px 10px; background: white; color: #006341; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%; font-size: 11px;">
            Reset to Gate 1
        </button>
    `;
    document.body.appendChild(infoPanel);
    
    setTimeout(() => {
        const resetBtn = document.getElementById('admin-reset-btn');
        if (resetBtn) {
            resetBtn.onclick = resetAdminLocation;
        }
    }, 100);
}

function toggleAdminMode() {
    adminMode.enabled = !adminMode.enabled;
    
    const button = document.getElementById('admin-mode-btn');
    const panel = document.getElementById('admin-info-panel');
    
    if (adminMode.enabled) {
        button.style.background = '#28a745';
        button.title = 'Admin Mode: ON (Click to disable)';
        panel.style.display = 'block';
        
        enableAdminMapClick();
        
        console.log('✅ Admin Mode ENABLED - Click map to set location');
    } else {
        button.style.background = '#dc3545';
        button.title = 'Admin Mode: OFF (Click to enable)';
        panel.style.display = 'none';
        
        disableAdminMapClick();
        
        if (adminMode.marker) {
            adminMode.marker.remove();
            adminMode.marker = null;
        }
        adminMode.customLocation = null;
        
        console.log('❌ Admin Mode DISABLED');
    }
}

function enableAdminMapClick() {
    window.adminMapClickHandler = (e) => {
        if (!adminMode.enabled) return;
        
        const lat = e.latlng.lat;
        const lng = e.latlng.lng;
        
        setAdminLocation(lat, lng);
    };
    
    if (window.map) {
        window.map.on('click', window.adminMapClickHandler);
    }
}

function disableAdminMapClick() {
    if (window.map && window.adminMapClickHandler) {
        window.map.off('click', window.adminMapClickHandler);
    }
}

function setAdminLocation(lat, lng) {
    adminMode.customLocation = { lat, lng };
    
    const coordsDiv = document.getElementById('admin-location-coords');
    if (coordsDiv) {
        coordsDiv.innerHTML = `
            Lat: ${lat.toFixed(5)}<br>
            Lng: ${lng.toFixed(5)}
        `;
    }
    
    if (adminMode.marker) {
        adminMode.marker.remove();
    }
    
    adminMode.marker = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'admin-location-marker',
            html: `
                <div style="
                    width: 24px;
                    height: 24px;
                    background: #ff6b6b;
                    border: 3px solid white;
                    border-radius: 50%;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
                    position: relative;
                ">
                    <div style="
                        position: absolute;
                        top: -22px;
                        left: 50%;
                        transform: translateX(-50%);
                        background: #ff6b6b;
                        color: white;
                        padding: 2px 6px;
                        border-radius: 3px;
                        white-space: nowrap;
                        font-size: 10px;
                        font-weight: bold;
                    ">YOU</div>
                </div>
            `,
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        })
    }).addTo(window.map);
    
    console.log(`📍 Admin location set to: [${lat.toFixed(6)}, ${lng.toFixed(6)}]`);
    
    showAdminNotification(`Location set!`);
}

function resetAdminLocation() {
    setAdminLocation(14.321726, 120.963558);
    showAdminNotification('Reset to Gate 1');
}

function showAdminNotification(message) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        bottom: 100px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.85);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 100000;
        font-size: 14px;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 1500);
}

function getStartLocation() {
    if (adminMode.enabled && adminMode.customLocation) {
        console.log('🔧 Using admin custom location:', adminMode.customLocation);
        return adminMode.customLocation;
    } else {
        console.log('📍 Using default Gate 1');
        return 'Gate 1';
    }
}

function isInsideCampusGeofence(location) {
    const campusBounds = {
        north: 14.3290,
        south: 14.3195,
        east: 120.9650,
        west: 120.9575
    };
    
    const isInside = location.lat >= campusBounds.south &&
           location.lat <= campusBounds.north &&
           location.lng >= campusBounds.west &&
           location.lng <= campusBounds.east;
    
    if (adminMode.enabled) {
        console.log(`🗺️ Location ${isInside ? 'INSIDE' : 'OUTSIDE'} campus geofence`);
    }
    
    return isInside;
}

function initAdminModeWhenReady() {
    if (window.map) {
        initAdminMode();
        console.log('🔧 Admin mode initialized - Button available in top-right corner');
    } else {
        console.log('⏳ Waiting for map...');
        setTimeout(initAdminModeWhenReady, 500);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdminModeWhenReady);
} else {
    initAdminModeWhenReady();
}

window.adminMode = adminMode;
window.getStartLocation = getStartLocation;
window.isInsideCampusGeofence = isInsideCampusGeofence;

// Call this after admin login to reveal the button
window.showAdminModeButton = function() {
    const btn = document.getElementById('admin-mode-btn');
    if (btn) btn.style.display = 'flex';
};

window.hideAdminModeButton = function() {
    const btn = document.getElementById('admin-mode-btn');
    if (btn) btn.style.display = 'none';
};
