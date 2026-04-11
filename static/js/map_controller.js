// map_controller.js - Handles all map visualization and user interaction

class CampusMapController {
    constructor(mapElementId) {
        this.mapElementId = mapElementId;
        this.map = null;
        this.currentRoute = null;
        this.userMarker = null;
        this.activeMarkers = [];
        this.activeLines = [];
        this.isTracking = false;
    }

    initialize(centerCoords = [14.3217, 120.9636], zoom = 17) {
        // Remove existing map if any
        if (this.map) {
            this.map.remove();
        }

        // Create new map
        this.map = L.map(this.mapElementId).setView(centerCoords, zoom);
        
        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(this.map);

        window.map = this.map;

        console.log("Map initialized");
        return this.map;
    }

    async showRoute(startLocation, endLocation, navigationEngine) {
        console.log(`Showing route: ${startLocation} → ${endLocation}`);

        // Clear previous route
        this.clearRoute();

        // Get route from navigation engine
        const route = navigationEngine.findShortestPath(startLocation, endLocation);

        if (!route) {
            console.error("Could not find route");
            return null;
        }

        this.currentRoute = route;

        // Draw route on map
        this.drawRoute(route);

        // Add markers
        this.addStartEndMarkers(route);

        // Add instruction markers
        this.addInstructionMarkers(route.instructions);

        // Fit map to show entire route
        this.fitToRoute(route);

        return route;
    }

    drawRoute(route) {
        // Main route outline (drawn first = lower z-order)
        const routeOutline = L.polyline(route.coordinates, {
            color: '#ffffff',
            weight: 10,
            opacity: 0.5,
            lineCap: 'round',
            lineJoin: 'round'
        }).addTo(this.map);

        // Main route line (on top of outline, below markers)
        const routeLine = L.polyline(route.coordinates, {
            color: '#006341',
            weight: 6,
            opacity: 0.85,
            lineCap: 'round',
            lineJoin: 'round',
            className: 'route-line'
        }).addTo(this.map);

        this.activeLines.push(routeLine, routeOutline);

        console.log(`Drew route with ${route.coordinates.length} points`);
    }

    addStartEndMarkers(route) {
        if (!route || !route.coordinates || route.coordinates.length === 0) return;

        // Start marker - clean green dot
        const startMarker = L.circleMarker(route.coordinates[0], {
            radius: 8,
            fillColor: '#22c55e',
            color: '#ffffff',
            weight: 3,
            fillOpacity: 1,
            zIndexOffset: 1000
        }).addTo(this.map);

        // End marker with destination label
        const destName = route.endLocation?.name || 'Destination';
        const endMarker = L.marker(route.coordinates[route.coordinates.length - 1], {
            icon: L.divIcon({
                className: 'custom-marker',
                html: `<div style="
                    background: #006341;
                    color: white;
                    padding: 4px 10px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                    white-space: nowrap;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                ">📍 ${destName}</div>`,
                iconSize: [120, 28],
                iconAnchor: [60, 28]
            }),
            zIndexOffset: 1000
        }).addTo(this.map);

        this.activeMarkers.push(startMarker, endMarker);
    }

    addInstructionMarkers(instructions) {
        // Skip first and last (already have start/end markers)
        for (let i = 1; i < instructions.length - 1; i++) {
            const instruction = instructions[i];
            
            const marker = L.circleMarker(instruction.coordinates, {
                radius: 8,
                fillColor: '#3b82f6',
                color: '#ffffff',
                weight: 2,
                fillOpacity: 0.9
            }).addTo(this.map);

            marker.bindPopup(`
                <div class="route-popup">
                    <h4>Step ${instruction.step}</h4>
                    <p>${instruction.text}</p>
                </div>
            `);

            this.activeMarkers.push(marker);
        }
    }

    createCustomIcon(label, color, emoji = '') {
        return L.divIcon({
            className: 'custom-marker',
            html: `
                <div style="
                    background-color: ${color};
                    color: white;
                    border-radius: 50%;
                    width: 36px;
                    height: 36px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 16px;
                    border: 3px solid white;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                ">
                    ${emoji || label}
                </div>
            `,
            iconSize: [36, 36],
            iconAnchor: [18, 18],
            popupAnchor: [0, -18]
        });
    }

    fitToRoute(route) {
        const bounds = L.latLngBounds(route.coordinates);
        this.map.fitBounds(bounds, {
            padding: [50, 50],
            maxZoom: 18
        });
    }

    clearRoute() {
        // Remove all markers
        this.activeMarkers.forEach(marker => marker.remove());
        this.activeMarkers = [];

        // Remove all lines
        this.activeLines.forEach(line => line.remove());
        this.activeLines = [];

        this.currentRoute = null;
    }

    showLocation(coordinates, name, description = '') {
        this.clearRoute();

        const marker = L.marker(coordinates, {
            icon: this.createCustomIcon('📍', '#3b82f6')
        }).addTo(this.map);

        marker.bindPopup(`
            <div class="route-popup">
                <h3>${name}</h3>
                ${description ? `<p>${description}</p>` : ''}
            </div>
        `).openPopup();

        this.map.setView(coordinates, 18);
        this.activeMarkers.push(marker);
    }

    // Live GPS tracking
    startTracking() {
        if (!navigator.geolocation) {
            console.error("Geolocation not supported");
            return false;
        }

        this.isTracking = true;

        this.watchId = navigator.geolocation.watchPosition(
            (position) => this.updateUserPosition(position),
            (error) => this.handleTrackingError(error),
            {
                enableHighAccuracy: true,
                maximumAge: 5000,
                timeout: 10000
            }
        );

        console.log("GPS tracking started");
        return true;
    }

    stopTracking() {
        if (this.watchId) {
            navigator.geolocation.clearWatch(this.watchId);
            this.isTracking = false;
            console.log("GPS tracking stopped");
        }

        if (this.userMarker) {
            this.userMarker.remove();
            this.userMarker = null;
        }
    }

    updateUserPosition(position) {
        const coords = [position.coords.latitude, position.coords.longitude];

        // Create or update user marker
        if (!this.userMarker) {
            this.userMarker = L.marker(coords, {
                icon: this.createCustomIcon('👤', '#8b5cf6', '📍'),
                zIndexOffset: 1000
            }).addTo(this.map);
        } else {
            this.userMarker.setLatLng(coords);
            this.userMarker.setZIndexOffset(1000);
        }

        // Check if user is off route
        if (this.currentRoute) {
            const isOffRoute = this.checkIfOffRoute(coords);
            if (isOffRoute) {
                this.handleOffRoute(coords);
            }
        }
    }

    checkIfOffRoute(userCoords, threshold = 30) {
        if (!this.currentRoute) return false;

        // Find closest point on route
        let minDistance = Infinity;
        
        for (const routePoint of this.currentRoute.coordinates) {
            const distance = this.calculateDistance(userCoords, routePoint);
            if (distance < minDistance) {
                minDistance = distance;
            }
        }

        return minDistance > threshold;
    }

    handleOffRoute(userCoords) {
        console.warn("User is off route");
    }

    handleTrackingError(error) {
        console.error("GPS Error:", error.message);
    }

    calculateDistance(coord1, coord2) {
        const [lat1, lon1] = coord1;
        const [lat2, lon2] = coord2;
        
        const R = 6371e3;
        const φ1 = lat1 * Math.PI / 180;
        const φ2 = lat2 * Math.PI / 180;
        const Δφ = (lat2 - lat1) * Math.PI / 180;
        const Δλ = (lon2 - lon1) * Math.PI / 180;
        
        const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                  Math.cos(φ1) * Math.cos(φ2) *
                  Math.sin(Δλ/2) * Math.sin(Δλ/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        
        return R * c;
    }

    // Show all pathways (for debugging/overview)
    showAllPathways(navigationEngine) {
        this.clearRoute();

        navigationEngine.pathways.forEach((pathway, pathwayId) => {
            const line = L.polyline(pathway.points, {
                color: pathway.shaded ? '#10b981' : '#6b7280',
                weight: 3,
                opacity: 0.6
            }).addTo(this.map);

            line.bindPopup(`
                <div class="route-popup">
                    <h3>${pathway.name}</h3>
                    <p>Surface: ${pathway.surface}</p>
                    <p>Width: ${pathway.width}m</p>
                    <p>Shaded: ${pathway.shaded ? 'Yes' : 'No'}</p>
                </div>
            `);

            this.activeLines.push(line);
        });

        console.log(`Showing ${navigationEngine.pathways.size} pathways`);
    }

    getMapElement() {
        return this.map;
    }
}
