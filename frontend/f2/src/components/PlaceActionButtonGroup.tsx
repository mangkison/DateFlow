import { useState } from "react";
import type { CoursePlace } from "../types/course";

interface Props {
    place: CoursePlace;
    onSkip: (place: CoursePlace) => void;
    onRecommendOther: (place: CoursePlace) => void;
    onWishlist: (place: CoursePlace) => void;
    onClose: () => void;
}

export default function PlaceActionButtonGroup({ place, onSkip, onRecommendOther, onWishlist, onClose }: Props) {
    const [wishlisted, setWishlisted] = useState(false);
    const [shareOpen, setShareOpen] = useState(false);

    const handleCopyLink = async () => {
        try {
            await navigator.clipboard.writeText(window.location.href);
            setShareOpen(false);
            alert('링크가 복사됐어요!');
        } catch {
            alert('링크 복사에 실패했어요.');
        }
    };

    const handleKakaoShare = () => {
        if (navigator.share) {
            navigator.share({ title: place.name, text: place.desc, url: window.location.href });
        } else {
            alert('카카오톡 공유는 모바일에서 지원돼요.');
        }
        setShareOpen(false);
    };

    const base: React.CSSProperties = {
        flex: 1,
        padding: '8px',
        background: '#f5f3fb',
        border: '1px solid #e8e4f4',
        borderRadius: '10px',
        fontSize: '12px',
        fontWeight: 600,
        cursor: 'pointer',
    };

    return (
        <div style={{ display: 'flex', gap: '8px' }}>
            <button
                onClick={() => { onSkip(place); onClose(); }}
                style={{ ...base, color: '#888' }}
            >
                🚫 건너뛰기
            </button>

            {/* 다른 장소 추천 — Week 3에 실제 API로 교체 예정 */}
            <button
                onClick={() => onRecommendOther(place)}
                style={{ ...base, color: '#5a4480' }}
            >
                🔄 다른 장소 추천
            </button>

            <button
                onClick={() => { setWishlisted(p => !p); onWishlist(place); }}
                style={{ ...base, background: wishlisted ? '#faeef2' : '#f5f3fb', color: wishlisted ? '#c0607a' : '#888', border: `1px solid ${wishlisted ? '#f0c0cc' : '#e8e4f4'}` }}
            >
                {wishlisted ? '💜 찜 완료' : '🤍 찜하기'}
            </button>

            {/* 공유하기 — 드롭다운으로 링크복사 / 카카오톡 선택 */}
            <div style={{ flex: 1, position: 'relative' }}>
                <button
                    onClick={() => setShareOpen(o => !o)}
                    style={{ ...base, width: '100%', background: shareOpen ? '#e8e4f4' : '#f5f3fb', color: '#5a4480' }}
                >
                    🔗 공유하기
                </button>
                {shareOpen && (
                    <div style={{ position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, background: '#fff', border: '1px solid #e8e4f4', borderRadius: '10px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', zIndex: 10, overflow: 'hidden' }}>
                        <button onClick={handleCopyLink} style={{ display: 'block', width: '100%', padding: '10px 12px', background: 'none', border: 'none', textAlign: 'left', fontSize: '12px', color: '#5a4480', cursor: 'pointer', fontWeight: 600 }}>
                            🔗 링크 복사
                        </button>
                        <button onClick={handleKakaoShare} style={{ display: 'block', width: '100%', padding: '10px 12px', background: 'none', border: 'none', borderTop: '1px solid #f0edf8', textAlign: 'left', fontSize: '12px', color: '#5a4480', cursor: 'pointer', fontWeight: 600 }}>
                            💬 카카오톡 공유
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
