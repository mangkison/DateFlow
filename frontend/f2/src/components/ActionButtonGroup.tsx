import type { CoursePlace } from "../types/course";

interface Props {
    place: CoursePlace;
}

export default function ActionButtonGroup({ place }: Props) {

    const handleNavigation = () => {
        window.open(
            `https://map.kakao.com/link/to/${place.name},${place.lat},${place.lng}`,
            '_blank'
        );
    };

    const handleInstagram = () => {
        window.open(
            `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(place.name)}`,
            '_blank'
        );
    };

    const handleParking = () => {
        window.open(
            `https://map.naver.com/v5/search/${encodeURIComponent(place.name + ' 주차')}`,
            '_blank'
        );
    };

    const handlePhone = () => {
        if (place.phone) {
            window.location.href = `tel:${place.phone}`;
        }
    };

    const base: React.CSSProperties = {
        flex: 1,
        padding: '10px 8px',
        background: '#f5f3fb',
        color: '#5a4480',
        border: '1px solid #e8e4f4',
        borderRadius: '10px',
        fontSize: '12px',
        fontWeight: 600,
        cursor: 'pointer',
        lineHeight: '1.4',
    };

    const disabled: React.CSSProperties = {
        ...base,
        background: '#f5f5f5',
        color: '#ccc',
        border: '1px solid #eee',
        cursor: 'default',
    };

    return (
        <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
            <button onClick={handleNavigation} style={base}>
                길찾기
            </button>

            <button onClick={handleInstagram} style={base}>
                인스타<br />검색
            </button>

            <button
                onClick={place.parkingAvailable ? handleParking : undefined}
                style={place.parkingAvailable ? base : disabled}
            >
                {place.parkingAvailable ? '주차 가능' : '주차 불가'}
            </button>

            <button
                onClick={place.phone ? handlePhone : undefined}
                style={place.phone ? base : disabled}
            >
                {place.phone ? '전화하기' : '번호 없음'}
            </button>
        </div>
    );
}
