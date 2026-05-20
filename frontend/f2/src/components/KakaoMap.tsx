import { useEffect, useRef, useState } from 'react';
import type { CoursePlace } from '../types/course';

interface Props {
    places: CoursePlace[];
    selectedPlace: CoursePlace | null;
    onSelectPlace: (place: CoursePlace) => void;
}

interface KakaoMaps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
}

declare global {
    interface Window {
        kakao: { maps: KakaoMaps };
    }
}

const CATEGORY_COLOR: Record<string, string> = {
    cafe:       '#B89CE0',
    restaurant: '#E07777',
    activity:   '#77B8E0',
    shopping:   '#E0C077',
    culture:    '#77E0B8',
};

export default function KakaoMap({ places, selectedPlace, onSelectPlace }: Props) {
    const containerRef = useRef<HTMLDivElement>(null);
    const mapRef       = useRef<KakaoMaps | null>(null);

    // SDK가 이미 로드된 경우 true로 초기화
    const [loaded, setLoaded] = useState(() => !!(window.kakao?.maps));

    const apiKey = import.meta.env.VITE_KAKAO_MAPS_API_KEY as string | undefined;

    // SDK 로드 — 아직 로드되지 않은 경우에만 실행
    useEffect(() => {
        if (!apiKey || loaded) return;

        const existing = document.getElementById('kakao-maps-sdk');
        if (existing) {
            existing.addEventListener('load', () => setLoaded(true));
            return;
        }

        const script = document.createElement('script');
        script.id  = 'kakao-maps-sdk';
        script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${apiKey}&autoload=false`;
        script.onload = () => window.kakao.maps.load(() => setLoaded(true));
        document.head.appendChild(script);
    }, [apiKey, loaded]);

    // 지도 초기화 — SDK 로드 완료 후 1회 실행
    useEffect(() => {
        if (!loaded || !containerRef.current || mapRef.current) return;

        const center = places.length > 0
            ? new window.kakao.maps.LatLng(places[0].lat, places[0].lng)
            : new window.kakao.maps.LatLng(37.5665, 126.9780);

        mapRef.current = new window.kakao.maps.Map(containerRef.current, { center, level: 4 });
    }, [loaded, places]);

    // 마커 + 동선 폴리라인 렌더링
    useEffect(() => {
        if (!mapRef.current || !loaded) return;

        const { LatLng, LatLngBounds, CustomOverlay, Polyline } = window.kakao.maps;
        const bounds   = new LatLngBounds();
        const overlays: KakaoMaps[] = [];

        places.forEach((place, idx) => {
            const pos        = new LatLng(place.lat, place.lng);
            const isSelected = selectedPlace?.name === place.name;
            const color      = CATEGORY_COLOR[place.category] ?? '#B89CE0';

            bounds.extend(pos);

            const el = document.createElement('div');
            el.style.cssText = [
                `width:${isSelected ? 34 : 28}px`,
                `height:${isSelected ? 34 : 28}px`,
                `background:${isSelected ? '#5a4480' : color}`,
                'border-radius:50%',
                'border:2px solid white',
                'box-shadow:0 2px 6px rgba(0,0,0,0.25)',
                'display:flex',
                'align-items:center',
                'justify-content:center',
                'color:white',
                `font-size:${isSelected ? 14 : 12}px`,
                'font-weight:700',
                'cursor:pointer',
                `transform:${isSelected ? 'scale(1.15)' : 'scale(1)'}`,
                'transition:all 0.15s',
            ].join(';');
            el.textContent = String(idx + 1);
            el.addEventListener('click', () => onSelectPlace(place));

            const overlay = new CustomOverlay({ position: pos, content: el, map: mapRef.current });
            overlays.push(overlay);
        });

        if (places.length > 0) mapRef.current.setBounds(bounds);

        // 동선 연결 폴리라인
        const polyline = new Polyline({
            path: places.map(p => new LatLng(p.lat, p.lng)),
            strokeWeight: 2,
            strokeColor: '#b8a9d9',
            strokeOpacity: 0.8,
            strokeStyle: 'shortdash',
            map: mapRef.current,
        });

        return () => {
            overlays.forEach(o => o.setMap(null));
            polyline.setMap(null);
        };
    }, [loaded, places, selectedPlace, onSelectPlace]);

    const showPlaceholder = !apiKey || !loaded;

    return (
        <div style={{ position: 'relative', width: '100%', height: '280px' }}>
            <div
                ref={containerRef}
                style={{
                    width: '100%',
                    height: '100%',
                    borderRadius: '12px',
                    overflow: 'hidden',
                    border: '1px solid #e8e4f4',
                }}
            />
            {showPlaceholder && (
                <div style={{
                    position: 'absolute',
                    inset: 0,
                    background: '#f0edf8',
                    borderRadius: '12px',
                    border: '1px dashed #c9bfed',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#9e8ec8',
                    fontSize: '13px',
                }}>
                    {!apiKey
                        ? '.env.local에 VITE_KAKAO_MAPS_API_KEY를 설정해 주세요'
                        : '지도 불러오는 중...'}
                </div>
            )}
        </div>
    );
}
