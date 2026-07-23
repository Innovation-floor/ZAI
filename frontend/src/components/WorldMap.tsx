import { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import type { MapPayload, Language } from '@/types/api';
import { t, fmt } from '@/lib/i18n';
import 'leaflet/dist/leaflet.css';

const RISK_COLOR: Record<string, string> = {
  Low: '#1D9E75', Medium: '#EF9F27', High: '#E24B4A',
};

function FlyTo({ map: payload, action }: { map: MapPayload; action: string }) {
  const leaflet = useMap();
  useEffect(() => {
    if (action === 'world' || !payload.bounds) {
      leaflet.flyTo([18, 30], 2, { duration: 0.9 });
    } else if (action !== 'none' && payload.bounds) {
      const b = payload.bounds;
      leaflet.flyToBounds([[b.south, b.west], [b.north, b.east]], {
        duration: 0.9, maxZoom: 6, padding: [30, 30],
      });
    }
  }, [payload, action, leaflet]);
  return null;
}

interface Props {
  data: MapPayload;
  action: string;
  lang: Language;
}

export function WorldMap({ data, action, lang }: Props) {
  return (
    <div className="card map-card">
      <div className="card-head">
        <h2>{t('mapTitle', lang)}</h2>
      </div>
      <MapContainer
        center={[18, 30]}
        zoom={2}
        style={{ height: 400, borderRadius: 12, background: '#12243A' }}
        zoomControl
        attributionControl={false}
        worldCopyJump
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          maxZoom={18}
          subdomains="abcd"
        />
        <FlyTo map={data} action={action} />
        {data.markers.map((m) => (
          <CircleMarker
            key={m.id}
            center={[m.lat, m.lon]}
            radius={Math.max(5, Math.min(18, Math.sqrt(m.beneficiaries) / 26))}
            pathOptions={{
              color: RISK_COLOR[m.risk] || '#888',
              fillColor: RISK_COLOR[m.risk] || '#888',
              fillOpacity: m.featured ? 0.85 : 0.42,
              weight: m.featured ? 2 : 1,
            }}
          >
            <Popup>
              <b>{m.name}</b><br />
              {m.country} · {m.sector}<br />
              AED {m.investment}M · {fmt(m.beneficiaries, lang)} beneficiaries<br />
              {m.status} · {m.completion}% complete · {m.risk} risk
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      <div className="legend">
        <span><i className="sw low" /> Low risk</span>
        <span><i className="sw med" /> Medium risk</span>
        <span><i className="sw high" /> High risk</span>
      </div>
    </div>
  );
}
