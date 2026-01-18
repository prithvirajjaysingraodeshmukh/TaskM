import { useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';

interface SiteData {
  site_id?: string | number;
  lat: number;
  lon: number;
  area_class: string;
  density: number;
}

interface SiteMapProps {
  sites: SiteData[];
}

// Color mapping based on area classification
const AREA_COLORS: Record<string, string> = {
  Dense: '#b71c1c',      // Dark Red
  Urban: '#ed6c02',       // Orange
  Suburban: '#1976d2',    // Blue
  Rural: '#2e7d32',       // Green
};

// Helper component to auto-center map bounds
function ChangeView({ bounds }: { bounds: L.LatLngBounds | null }) {
  const map = useMap();

  useEffect(() => {
    if (bounds && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    }
  }, [map, bounds]);

  return null;
}

const SiteMap = ({ sites }: SiteMapProps) => {
  // Calculate bounds from all sites
  const bounds: L.LatLngBounds | null = sites.length > 0
    ? (() => {
        const validSites = sites.filter(s => !isNaN(s.lat) && !isNaN(s.lon) && s.lat !== 0 && s.lon !== 0);
        
        if (validSites.length === 0) return null;
        
        const lats = validSites.map(s => s.lat);
        const lons = validSites.map(s => s.lon);
        
        const minLat = Math.min(...lats);
        const maxLat = Math.max(...lats);
        const minLon = Math.min(...lons);
        const maxLon = Math.max(...lons);
        
        return L.latLngBounds(
          [minLat, minLon],
          [maxLat, maxLon]
        );
      })()
    : null;

  // Default center if no sites
  const defaultCenter: [number, number] = [40.7128, -74.0060]; // NYC as fallback

  // Get color for area class
  const getColor = (areaClass: string): string => {
    return AREA_COLORS[areaClass] || '#999999';
  };

  return (
    <MapContainer
      center={defaultCenter}
      zoom={10}
      style={{ height: '500px', width: '100%', borderRadius: '8px' }}
      scrollWheelZoom={true}
    >
      <ChangeView bounds={bounds} />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {sites.map((site, index) => {
        const lat = Number(site.lat);
        const lon = Number(site.lon);
        
        // Skip invalid coordinates
        if (isNaN(lat) || isNaN(lon) || lat === 0 || lon === 0) return null;

        const color = getColor(site.area_class);
        const siteId = site.site_id || `Site ${index + 1}`;
        const density = Number(site.density) || 0;

        return (
          <CircleMarker
            key={index}
            center={[lat, lon]}
            radius={5}
            pathOptions={{
              fillColor: color,
              color: color,
              fillOpacity: 0.7,
              weight: 2,
            }}
          >
            <Popup>
              <div style={{ minWidth: '150px' }}>
                <strong>Site ID:</strong> {String(siteId)}<br />
                <strong>Density:</strong> {density.toFixed(4)} sites/km²<br />
                <strong>Classification:</strong> {site.area_class || 'Unknown'}
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
};

export default SiteMap;
