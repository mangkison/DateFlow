import type { CoursePlace } from "../types/course";

interface Props {
    place: CoursePlace;
    onSelectAlternative: () => void;
    onShowLowCrowd: () => void;
    tabVisible: boolean;
}

export default function ActionButtonGroup({ place, onSelectAlternative, onShowLowCrowd, tabVisible }: Props) {

    // 카카오맵 길찾기 URL 생성 — 장소명과 좌표를 파라미터로 전달
    const handleNavigation = () => {
        window.open(
            `https://map.kakao.com/link/to/${place.name},${place.lat},${place.lng}`,
            '_blank'
        );
    };

    // 예약 버튼 클릭 — 예약 가능 여부에 따라 분기
    const handleReservation = () => {
        if (place.reservationAvailable && place.reservationUrl) {
            window.open(place.reservationUrl, '_blank');
        } else {
            alert('현재 온라인 예약이 제공되지 않는 장소예요.\n직접 방문하거나 전화로 문의해주세요.');
        }
    };

    // 예약 버튼 스타일 분기 — 가능/불가 상태를 색상과 커서로 구분
    const reservationButtonStyle: React.CSSProperties = place.reservationAvailable
        ? {
            flex: 1,
            padding: '10px 8px',
            background: '#b8a9d9',
            color: '#ffffff',
            border: '1px solid #b8a9d9',
            borderRadius: '10px',
            fontSize: '12px',
            fontWeight: 700,
            cursor: 'pointer',
            lineHeight: '1.4',
        }
        : {
            flex: 1,
            padding: '10px 8px',
            background: '#f0f0f0',
            color: '#bbb',
            border: '1px solid #e0e0e0',
            borderRadius: '10px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
            lineHeight: '1.4',
        };

    return (
        <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>

            {/* 웨이팅 적은 시간대 버튼 — CrowdChart의 highlightLow 토글 */}
            <button
                onClick={onShowLowCrowd}
                style={{
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
                }}
            >
                웨이팅 적은<br />시간대로
            </button>

            {/* 대체 장소 버튼 — 대체 장소가 있고 탭이 아직 열리지 않았을 때만 표시 */}
            {place.alternativePlace && !tabVisible && (
                <button
                    onClick={onSelectAlternative}
                    style={{
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
                    }}
                >
                    대체 장소<br />추천
                </button>
            )}

            {/* 길찾기 버튼 — 카카오맵 외부 링크로 연결 */}
            <button
                onClick={handleNavigation}
                style={{
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
                }}
            >
                길찾기
            </button>

            {/* 예약 버튼 — 예약 가능 여부에 따라 스타일과 텍스트 분기 */}
            <button
                onClick={handleReservation}
                style={reservationButtonStyle}
            >
                {place.reservationAvailable ? (
                    <>캐치테이블<br />예약하기</>
                ) : (
                    <>예약<br />불가</>
                )}
            </button>
        </div>
    );
}