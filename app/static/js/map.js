// Map Configuration
const mapConfig = {
    defaultCenter: { lat: 50.0755, lng: 14.4378 }, // Prague
    defaultZoom: 12,
    styles: [
        {
            featureType: 'poi',
            elementType: 'labels',
            stylers: [{ visibility: 'off' }]
        },
        {
            featureType: 'transit',
            elementType: 'labels',
            stylers: [{ visibility: 'off' }]
        }
    ]
};

// Marker Icons
const markerIcons = {
    warehouse: {
        url: '/static/images/warehouse.png',
        scaledSize: new google.maps.Size(32, 32)
    },
    delivery: {
        url: '/static/images/delivery.png',
        scaledSize: new google.maps.Size(32, 32)
    },
    driver: {
        url: '/static/images/driver.png',
        scaledSize: new google.maps.Size(32, 32)
    }
};

// Map Class
class DeliveryMap {
    constructor(elementId, options = {}) {
        this.elementId = elementId;
        this.options = { ...mapConfig, ...options };
        this.map = null;
        this.markers = new Map();
        this.directionsService = new google.maps.DirectionsService();
        this.directionsRenderer = new google.maps.DirectionsRenderer({
            suppressMarkers: true,
            polylineOptions: {
                strokeColor: '#007bff',
                strokeWeight: 4
            }
        });
    }

    init() {
        const mapElement = document.getElementById(this.elementId);
        if (!mapElement) return null;

        this.map = new google.maps.Map(mapElement, {
            center: this.options.defaultCenter,
            zoom: this.options.defaultZoom,
            styles: this.options.styles
        });

        this.directionsRenderer.setMap(this.map);
        return this.map;
    }

    addMarker(id, position, title, icon = null) {
        if (this.markers.has(id)) {
            this.markers.get(id).setMap(null);
        }

        const marker = new google.maps.Marker({
            position,
            map: this.map,
            title,
            icon: icon ? markerIcons[icon] : null
        });

        this.markers.set(id, marker);
        return marker;
    }

    removeMarker(id) {
        if (this.markers.has(id)) {
            this.markers.get(id).setMap(null);
            this.markers.delete(id);
        }
    }

    clearMarkers() {
        this.markers.forEach(marker => marker.setMap(null));
        this.markers.clear();
    }

    showRoute(origin, destination, waypoints = []) {
        const request = {
            origin,
            destination,
            waypoints: waypoints.map(point => ({
                location: point,
                stopover: true
            })),
            optimizeWaypoints: true,
            travelMode: google.maps.TravelMode.DRIVING
        };

        this.directionsService.route(request, (result, status) => {
            if (status === 'OK') {
                this.directionsRenderer.setDirections(result);
            } else {
                console.error('Directions request failed:', status);
            }
        });
    }

    clearRoute() {
        this.directionsRenderer.setDirections({ routes: [] });
    }

    fitBounds() {
        if (this.markers.size === 0) return;

        const bounds = new google.maps.LatLngBounds();
        this.markers.forEach(marker => bounds.extend(marker.getPosition()));
        this.map.fitBounds(bounds);
    }

    addClickListener(callback) {
        this.map.addListener('click', (event) => {
            callback(event.latLng);
        });
    }

    addMarkerClickListener(markerId, callback) {
        const marker = this.markers.get(markerId);
        if (marker) {
            marker.addListener('click', () => callback(marker));
        }
    }
}

// Export
window.DeliveryMap = DeliveryMap; 