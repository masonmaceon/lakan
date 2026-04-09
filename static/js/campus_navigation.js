// campus_navigation.js - Pure Campus Navigation System
// No external routing APIs - complete control over pathfinding

class CampusNavigationEngine {
    constructor() {
        this.nodes = new Map();           // All walkable points
        this.edges = new Map();           // Connections with weights
        this.buildings = new Map();       // Building/POI data
        this.pathways = new Map();        // Named pathway data
        this.isReady = false;
    }

    async initialize() {
        if (this.isReady) return;
        
        console.log("🚀 Initializing Campus Navigation Engine...");
        
        try {
            // Load all data from Firebase
            await Promise.all([
                this.loadPathways(),
                this.loadBuildings(),
                this.loadLinks()
            ]);
            
            // Build the navigation graph
            this.buildNavigationGraph();
            
            this.isReady = true;
            console.log(`✅ Navigation ready: ${this.nodes.size} nodes, ${this.countEdges()} connections`);
            
        } catch (error) {
            console.error("❌ Initialization failed:", error);
            throw error;
        }
    }

    async loadPathways() {
        const response = await fetch('/get-all-pathways');
        const pathways = await response.json();
        
        pathways.forEach(pathway => {
            this.pathways.set(pathway.id, {
                id: pathway.id,
                name: pathway.name || pathway.id,
                points: pathway.points,
                type: pathway.type || 'walkway',
                surface: pathway.surface || 'concrete',
                width: pathway.width || 2,
                shaded: pathway.shaded || false,
                accessible: pathway.accessible !== false
            });
        });
        
        console.log(`📍 Loaded ${this.pathways.size} pathways`);
    }

    async loadBuildings() {
        const response = await fetch('/get-all-locations');
        const locations = await response.json();
        
        locations.forEach(location => {
            this.buildings.set(location.id, {
                id: location.id,
                name: location.name || location.id,
                coordinates: location.coordinates,
                type: 'building',
                entrances: location.entrances || [location.coordinates]
            });
        });
        
        console.log(`🏛️ Loaded ${this.buildings.size} buildings`);
    }

    async loadLinks() {
        const response = await fetch('/get-all-links');
        const links = await response.json();
        
        this.links = links;
        console.log(`🔗 Loaded ${links.length} pathway links`);
    }

    buildNavigationGraph() {
        console.log("🔨 Building navigation graph...");
        
        // Step 1: Add all pathway points as nodes
        this.pathways.forEach((pathway, pathwayId) => {
            pathway.points.forEach((coord, index) => {
                const nodeId = `${pathwayId}_${index}`;
                
                this.nodes.set(nodeId, {
                    id: nodeId,
                    coordinates: coord,
                    type: 'pathway',
                    pathwayId: pathwayId,
                    index: index,
                    properties: {
                        surface: pathway.surface,
                        shaded: pathway.shaded,
                        accessible: pathway.accessible
                    }
                });
            });
            
            // Connect sequential points along the pathway
            for (let i = 0; i < pathway.points.length - 1; i++) {
                const nodeA = `${pathwayId}_${i}`;
                const nodeB = `${pathwayId}_${i + 1}`;
                const distance = this.calculateDistance(
                    pathway.points[i],
                    pathway.points[i + 1]
                );
                
                this.addEdge(nodeA, nodeB, distance, pathway);
            }
        });

        // Step 2a: Connect pathways using MySQL pathway_connections
        if (this.links && this.links.length > 0) {
            console.log(`🔗 Applying ${this.links.length} pathway connections from database...`);
            
            this.links.forEach(link => {
                const node1Id = `${link.pathway1}_${link.pathway1_index}`;
                const node2Id = `${link.pathway2}_${link.pathway2_index}`;
                
                const node1 = this.nodes.get(node1Id);
                const node2 = this.nodes.get(node2Id);
                
                if (node1 && node2) {
                    const distance = this.calculateDistance(node1.coordinates, node2.coordinates);
                    const node1PathwayId = node1Id.split('_').slice(0, -1).join('_');
                    const pathwayData = this.pathways.get(node1PathwayId) || { type: 'database_link' };
                    this.addEdge(node1Id, node2Id, distance, pathwayData);
                    console.log(`🔗 DB-connected: ${node1Id} ↔ ${node2Id} (${distance.toFixed(1)}m)`);
                } else {
                    if (!node1) console.warn(`⚠️ Missing node: ${node1Id}`);
                    if (!node2) console.warn(`⚠️ Missing node: ${node2Id}`);
                }
            });
        }

        // Step 2b: Auto-detect pathway intersections by matching coordinates (backup method)
        console.log("🔍 Auto-detecting pathway intersections...");
        const coordinateMap = new Map();

        // Index all pathway nodes by coordinates
        this.nodes.forEach((node, nodeId) => {
            if (node.type === 'pathway') {
                const coordKey = `${node.coordinates[0].toFixed(6)},${node.coordinates[1].toFixed(6)}`;
                if (!coordinateMap.has(coordKey)) {
                    coordinateMap.set(coordKey, []);
                }
                coordinateMap.get(coordKey).push(nodeId);
            }
        });

        // Connect nodes that share the same coordinates
        coordinateMap.forEach((nodeIds, coordKey) => {
            if (nodeIds.length > 1) {
                // Multiple pathways meet at this point - connect them all
                for (let i = 0; i < nodeIds.length; i++) {
                    for (let j = i + 1; j < nodeIds.length; j++) {
                        this.addEdge(nodeIds[i], nodeIds[j], 0.1, { type: 'intersection' });
                        console.log(`🔗 Auto-connected: ${nodeIds[i]} ↔ ${nodeIds[j]} (shared coordinate)`);
                    }
                }
            }
        });

        // Step 3: Connect buildings to nearest pathway nodes
        this.buildings.forEach((building, buildingId) => {
            const nearestResult = this.findNearestNode(building.coordinates, null, 100);
            
            if (nearestResult && nearestResult.nodeId) {
                // Create a virtual entrance node
                const entranceNodeId = `entrance_${buildingId}`;
                this.nodes.set(entranceNodeId, {
                    id: entranceNodeId,
                    coordinates: building.coordinates,
                    type: 'entrance',
                    buildingId: buildingId
                });
                
                // Connect entrance to nearest pathway
                const distance = this.calculateDistance(
                    building.coordinates,
                    this.nodes.get(nearestResult.nodeId).coordinates
                );
                
                this.addEdge(entranceNodeId, nearestResult.nodeId, distance, { type: 'entrance' });
                
                // Store entrance reference in building
                building.entranceNodeId = entranceNodeId;
                
                console.log(`🏛️ ${buildingId} → ${nearestResult.nodeId} (${distance.toFixed(1)}m)`);
            } else {
                console.error(`❌ Could not connect ${buildingId} to any pathway`);
            }
        });

        console.log(`✅ Graph built: ${this.nodes.size} nodes, ${this.countEdges()} edges`);
        console.log("🔍 Debugging connections:");
        console.log("Gate 1 entrance connects to:", this.edges.get('entrance_Gate 1'));
        console.log("JFH entrance connects to:", this.edges.get('entrance_JFH'));
        console.log("rotunda_7 connects to:", this.edges.get('rotunda_7'));
        console.log("jflane_0 connects to:", this.edges.get('jflane_0'));
        console.log("jflane_1 connects to:", this.edges.get('jflane_1'));
        console.log("univlane1_7 connects to:", this.edges.get('univlane1_7'));
    }

    addEdge(nodeAId, nodeBId, distance, properties = {}) {
        if (!this.nodes.has(nodeAId) || !this.nodes.has(nodeBId)) return;
        
        // Initialize edge lists if needed
        if (!this.edges.has(nodeAId)) {
            this.edges.set(nodeAId, []);
        }
        if (!this.edges.has(nodeBId)) {
            this.edges.set(nodeBId, []);
        }
        
        // Calculate weight (can be modified based on preferences)
        let weight = distance;
        
        // Add penalties/bonuses based on properties
        if (properties.surface === 'grass') weight *= 1.3;
        if (properties.shaded) weight *= 0.9;  // Prefer shaded paths
        if (!properties.accessible) weight *= 1.5;  // Discourage stairs
        if (properties.type === 'vehicle') weight *= 2.0;
        
        // Add bidirectional edges
        this.edges.get(nodeAId).push({
            to: nodeBId,
            distance: distance,
            weight: weight,
            properties: properties
        });
        
        this.edges.get(nodeBId).push({
            to: nodeAId,
            distance: distance,
            weight: weight,
            properties: properties
        });
    }

    findNearestNode(coordinates, excludePathwayId = null, maxDistance = 100) {
        let closestNode = null;
        let minDistance = Infinity;
        
        this.nodes.forEach((node, nodeId) => {
            // Only look at pathway nodes for connections
            if (node.type === 'pathway') {
                // Skip excluded pathway if specified
                if (excludePathwayId) {
                    const nodePathwayId = nodeId.split('_')[0];
                    if (nodePathwayId === excludePathwayId) {
                        return;
                    }
                }
                
                const distance = this.calculateDistance(node.coordinates, coordinates);
                if (distance < minDistance && distance < maxDistance) {
                    minDistance = distance;
                    closestNode = nodeId;
                }
            }
        });
        
        console.log(`Nearest node to ${coordinates}: ${closestNode} (${minDistance.toFixed(1)}m away)`);
        
        // Return object with both nodeId and distance
        return {
            nodeId: closestNode,
            distance: minDistance === Infinity ? null : minDistance
        };
    }

    // Dijkstra's algorithm for shortest path
    findShortestPath(startLocation, endLocation, preferences = {}) {
        console.log(`🎯 Finding path: ${startLocation} → ${endLocation}`);
        
        let startNodeId, endNodeId;
        
        // Check if startLocation is already a node ID (for admin mode GPS)
        if (this.nodes.has(startLocation)) {
            // It's a pathway node ID - use it directly!
            startNodeId = startLocation;
            console.log(`📍 Start: Using pathway node ${startNodeId} directly`);
        } else {
            // It's a building name - look it up
            const startBuilding = this.buildings.get(startLocation);
            if (!startBuilding) {
                console.error(`❌ Start location "${startLocation}" not found in buildings database`);
                return null;
            }
            
            const startNearestResult = this.findNearestNode(startBuilding.coordinates, null, 100);
            if (!startNearestResult || !startNearestResult.nodeId) {
                console.error(`❌ ${startLocation} is too far from any pathway (${startNearestResult?.distance || 'unknown'}m)`);
                return null;
            }
            startNodeId = startNearestResult.nodeId;
            console.log(`📍 Start: ${startLocation} → ${startNodeId} (${startNearestResult.distance.toFixed(1)}m away)`);
        }
        
        // Check if endLocation is already a node ID
        if (this.nodes.has(endLocation)) {
            // It's a pathway node ID - use it directly!
            endNodeId = endLocation;
            console.log(`📍 End: Using pathway node ${endNodeId} directly`);
        } else {
            // It's a building name - look it up
            const endBuilding = this.buildings.get(endLocation);
            if (!endBuilding) {
                console.error(`❌ End location "${endLocation}" not found in buildings database`);
                return null;
            }
            
            const endNearestResult = this.findNearestNode(endBuilding.coordinates, null, 100);
            if (!endNearestResult || !endNearestResult.nodeId) {
                console.error(`❌ ${endLocation} is too far from any pathway (${endNearestResult?.distance || 'unknown'}m)`);
                return null;
            }
            endNodeId = endNearestResult.nodeId;
            console.log(`📍 End: ${endLocation} → ${endNodeId} (${endNearestResult.distance.toFixed(1)}m away)`);
        }
        
        // Dijkstra's algorithm
        const distances = new Map();
        const previous = new Map();
        const unvisited = new Set();
        
        // Initialize
        this.nodes.forEach((_, nodeId) => {
            distances.set(nodeId, Infinity);
            unvisited.add(nodeId);
        });
        distances.set(startNodeId, 0);
        
        while (unvisited.size > 0) {
            // Find node with minimum distance
            let currentNode = null;
            let minDist = Infinity;
            
            for (const nodeId of unvisited) {
                const dist = distances.get(nodeId);
                if (dist < minDist) {
                    minDist = dist;
                    currentNode = nodeId;
                }
            }
            
            // No path found
            if (currentNode === null || minDist === Infinity) {
                console.log("❌ No path exists between these locations");
                return null;
            }
            
            // Reached destination
            if (currentNode === endNodeId) {
                console.log("✅ Path found!");
                break;
            }
            
            unvisited.delete(currentNode);
            
            // Check neighbors
            const neighbors = this.edges.get(currentNode) || [];
            for (const edge of neighbors) {
                if (unvisited.has(edge.to)) {
                    const altDistance = distances.get(currentNode) + edge.weight;
                    
                    if (altDistance < distances.get(edge.to)) {
                        distances.set(edge.to, altDistance);
                        previous.set(edge.to, currentNode);
                    }
                }
            }
        }
        
        // Reconstruct path
        const path = [];
        let current = endNodeId;
        
        while (current !== undefined) {
            path.unshift(current);
            current = previous.get(current);
        }
        
        if (path.length === 0 || path[0] !== startNodeId) {
            return null;
        }
        
        // Convert to route object
// Convert to route object
        return this.buildRouteObject(path, distances.get(endNodeId), startLocation, endLocation);    }

    showRouteFromCoordinates(startCoords, destinationBuildingId) {
        console.log(`🗺️ Routing from [${startCoords.lat}, ${startCoords.lng}] to ${destinationBuildingId}`);
        
        // Find nearest pathway point to start
        const nearestStart = this.findNearestNode([startCoords.lat, startCoords.lng], null, 100);
        
        if (!nearestStart || !nearestStart.nodeId) {
            console.error('❌ Too far from pathway');
            alert('You are too far from any pathway!');
            return null;
        }
        
        console.log(`📍 Starting from: ${nearestStart.nodeId} (${nearestStart.distance.toFixed(1)}m away)`);
        
        // Get destination building
        const destinationBuilding = this.buildings.get(destinationBuildingId);
        if (!destinationBuilding) {
            console.error(`❌ Building ${destinationBuildingId} not found`);
            return null;
        }
        
        // Find nearest pathway point to destination
        const nearestEnd = this.findNearestNode(destinationBuilding.coordinates, null, 100);
        
        if (!nearestEnd || !nearestEnd.nodeId) {
            console.error(`❌ ${destinationBuildingId} too far from pathway`);
            return null;
        }
        
        console.log(`📍 End: ${destinationBuildingId} → ${nearestEnd.nodeId} (${nearestEnd.distance.toFixed(1)}m away)`);
        
        // Run Dijkstra pathfinding from start node to end node
        const distances = new Map();
        const previous = new Map();
        const unvisited = new Set();
        
        this.nodes.forEach((node, nodeId) => {
            distances.set(nodeId, Infinity);
            unvisited.add(nodeId);
        });
        distances.set(nearestStart.nodeId, 0);
        
        while (unvisited.size > 0) {
            let currentNode = null;
            let minDist = Infinity;
            
            for (const nodeId of unvisited) {
                const dist = distances.get(nodeId);
                if (dist < minDist) {
                    minDist = dist;
                    currentNode = nodeId;
                }
            }
            
            if (currentNode === null || minDist === Infinity) {
                console.error('❌ No path found');
                alert('Could not find route!');
                return null;
            }
            
            if (currentNode === nearestEnd.nodeId) {
                console.log('✅ Path found!');
                break;
            }
            
            unvisited.delete(currentNode);
            
            const neighbors = this.edges.get(currentNode) || [];
            for (const edge of neighbors) {
                if (unvisited.has(edge.to)) {
                    const altDistance = distances.get(currentNode) + edge.weight;
                    
                    if (altDistance < distances.get(edge.to)) {
                        distances.set(edge.to, altDistance);
                        previous.set(edge.to, currentNode);
                    }
                }
            }
        }
        
        // Reconstruct path
        const path = [];
        let current = nearestEnd.nodeId;
        
        while (current !== undefined) {
            path.unshift(current);
            current = previous.get(current);
        }
        
        if (path.length === 0 || path[0] !== nearestStart.nodeId) {
            console.error('❌ Could not reconstruct path');
            return null;
        }
        
        const pathCoords = [];
        // Add start building coords
        const startBuilding = this.buildings.get(startLocation);
        if (startBuilding) pathCoords.push(startBuilding.coordinates);

        path.forEach(nodeId => {
            const node = this.nodes.get(nodeId);
            if (node) pathCoords.push(node.coordinates);
        });
        // Add end building coords
        pathCoords.push(destinationBuilding.coordinates);
        
        // Draw route on map
        if (this.currentRouteLine) {
            window.map.removeLayer(this.currentRouteLine);
        }
        
        this.currentRouteLine = L.polyline(pathCoords, {
            color: '#006341',
            weight: 6,
            opacity: 0.8
        }).addTo(window.map);
        
        // Add start marker
        if (this.startMarker) window.map.removeLayer(this.startMarker);
        this.startMarker = L.marker([startCoords.lat, startCoords.lng], {
            icon: L.divIcon({
                className: 'custom-marker',
                html: '<div style="background: red; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white;"></div>',
                iconSize: [20, 20]
            })
        }).addTo(window.map);
        
        // Add destination marker
        if (this.endMarker) window.map.removeLayer(this.endMarker);
        this.endMarker = L.marker(destinationBuilding.coordinates, {
            icon: L.divIcon({
                className: 'custom-marker',
                html: `<div style="
                    background: #006341;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 13px;
                    font-weight: bold;
                    white-space: nowrap;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                    border: 2px solid white;
                ">📍 ${destinationBuilding.name}</div>`,                iconSize: [20, 20]
            })
        }).addTo(window.map);
        
        // Fit bounds
        window.map.fitBounds(L.latLngBounds(pathCoords), { padding: [50, 50] });
        
        const totalDistance = distances.get(nearestEnd.nodeId) + nearestStart.distance + nearestEnd.distance;
        console.log(`✅ Route: ${totalDistance.toFixed(0)}m`);
        
        return {
            path: path,
            coordinates: pathCoords,
            totalDistance: Math.round(totalDistance),
            estimatedTime: Math.ceil(totalDistance / 80),
            instructions: [{step: 1, text: `Walk ${Math.round(totalDistance)}m to ${destinationBuilding.name}`}],
            startLocation: { name: 'Your Location', coordinates: [startCoords.lat, startCoords.lng] },
            endLocation: { name: destinationBuilding.name, coordinates: destinationBuilding.coordinates }
        };
    }

buildRouteObject(pathNodeIds, totalDistance, startLocation, endLocation) {
        const coordinates = [];
        const instructions = [];
        let currentPathway = null;

        // Prepend start building coords if available
        const startBuilding = startLocation ? this.buildings.get(startLocation) : null;
        if (startBuilding) coordinates.push(startBuilding.coordinates);

        pathNodeIds.forEach((nodeId, index) => {
            const node = this.nodes.get(nodeId);
            if (!node) return;
            coordinates.push(node.coordinates);
            
            if (node.type === 'entrance') {
                if (index === 0) {
                    instructions.push({
                        step: instructions.length + 1,
                        type: 'start',
                        text: `Start at ${this.buildings.get(node.buildingId)?.name || node.buildingId}`,
                        coordinates: node.coordinates
                    });
                } else {
                    instructions.push({
                        step: instructions.length + 1,
                        type: 'arrive',
                        text: `Arrive at ${this.buildings.get(node.buildingId)?.name || node.buildingId}`,
                        coordinates: node.coordinates
                    });
                }
            } else if (node.type === 'pathway') {
                if (currentPathway !== node.pathwayId) {
                    const pathway = this.pathways.get(node.pathwayId);
                    if (pathway) {
                        if (instructions.length > 0 && currentPathway !== null) {
                            instructions.push({
                                step: instructions.length + 1,
                                type: 'turn',
                                text: `Continue on ${pathway.name}`,
                                coordinates: node.coordinates
                            });
                        } else if (instructions.length === 1) {
                            instructions.push({
                                step: instructions.length + 1,
                                type: 'walk',
                                text: `Walk along ${pathway.name}`,
                                coordinates: node.coordinates
                            });
                        }
                    }
                    currentPathway = node.pathwayId;
                }
            }
        });

        // Append end building coords if available
        const endBuilding = endLocation ? this.buildings.get(endLocation) : null;
        if (endBuilding) coordinates.push(endBuilding.coordinates);
        
        return {
            path: pathNodeIds,
            coordinates: coordinates,
            instructions: instructions,
            distance: Math.round(totalDistance),
            totalDistance: Math.round(totalDistance),
            estimatedTime: Math.ceil(totalDistance / 80),
            pathType: 'campus_pathway'
        };
    }

    calculateDistance(coord1, coord2) {
        const [lat1, lon1] = coord1;
        const [lat2, lon2] = coord2;
        
        const R = 6371e3; // Earth's radius in meters
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

    countEdges() {
        let count = 0;
        this.edges.forEach(edgeList => count += edgeList.length);
        return count / 2; // Bidirectional edges counted twice
    }

    // Debug helper
    getGraphStats() {
        return {
            nodes: this.nodes.size,
            edges: this.countEdges(),
            buildings: this.buildings.size,
            pathways: this.pathways.size,
            ready: this.isReady
        };
    }
}

// Export singleton instance
const campusNav = new CampusNavigationEngine();