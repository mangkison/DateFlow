import { useState } from "react";
import type { CoursePlace } from "../types/course";
import CrowdChart from "./CrowdChart";
import ActionButtonGroup from "./ActionButtonGroup";
import { mockCrowdData, mockReviews } from "../mocks/courseData";
import { formatDaysAgo } from "../utils/formatDaysAgo";
import { isLikelyClosed } from "../utils/isLikelyClosed";

interface Props {
    place: CoursePlace;
    onClose: () => void;
    onSkip: (place: CoursePlace) => void;       // 이 장소 건너뛰기
    onRecommendOther: (place: CoursePlace) => void; // 다른 장소 추천
    onWishlist: (place: CoursePlace) => void;    // 찜하기
}

export default function PlaceDetailCard({ place, onClose, onSkip, onRecommendOther, onWishlist }: Props) {
    const [wishlisted, setWishlisted] = useState(false); // 찜 상태 토글용

    return (
        <div style={{
            background: '#ffffff',
            borderRadius: '16px',
            padding: '20px',
            border: '1px solid #e8e4f4',
            boxShadow: '0 2px 8px rgba(184, 169, 217, 0.2)',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
        }}>
            {/* 상단 — 장소명 + 닫기 버튼 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#2d2d2d', margin: 0, textAlign: 'left' }}>
                        {place.name}
                    </h2>
                    <p style={{
                        fontSize: '13px',
                        color: '#999',
                        margin: '4px 0 0 0',
                        height: '36px',
                        overflow: 'hidden',
                        lineHeight: '18px',
                        textAlign: 'left',
                    }}>
                        {place.desc}
                    </p>
                </div>
                <button
                    onClick={onClose}
                    style={{
                        background: 'none',
                        border: 'none',
                        fontSize: '18px',
                        cursor: 'pointer',
                        color: '#b8a9d9',
                        padding: '0 0 0 12px',
                    }}
                >
                    ✕
                </button>
            </div>

            {/* 장소 액션 버튼 — 건너뛰기, 다른 장소 추천, 찜하기 */}
            <div style={{ display: 'flex', gap: '8px' }}>
                {/* 건너뛰기 — 이 장소를 코스에서 제외 */}
                <button
                    onClick={() => { onSkip(place); onClose(); }}
                    style={{
                        flex: 1,
                        padding: '8px',
                        background: '#f5f3fb',
                        color: '#888',
                        border: '1px solid #e8e4f4',
                        borderRadius: '10px',
                        fontSize: '12px',
                        fontWeight: 600,
                        cursor: 'pointer',
                    }}
                >
                    🚫 건너뛰기
                </button>

                {/* 다른 장소 추천 — Week 3에 실제 API로 교체 예정 */}
                <button
                    onClick={() => onRecommendOther(place)}
                    style={{
                        flex: 1,
                        padding: '8px',
                        background: '#f5f3fb',
                        color: '#5a4480',
                        border: '1px solid #e8e4f4',
                        borderRadius: '10px',
                        fontSize: '12px',
                        fontWeight: 600,
                        cursor: 'pointer',
                    }}
                >
                    🔄 다른 장소 추천
                </button>

                {/* 찜하기 — 토글 방식, DateReviewPage와 연동 예정 */}
                <button
                    onClick={() => { setWishlisted((prev) => !prev); onWishlist(place); }}
                    style={{
                        flex: 1,
                        padding: '8px',
                        background: wishlisted ? '#faeef2' : '#f5f3fb',
                        color: wishlisted ? '#c0607a' : '#888',
                        border: `1px solid ${wishlisted ? '#f0c0cc' : '#e8e4f4'}`,
                        borderRadius: '10px',
                        fontSize: '12px',
                        fontWeight: 600,
                        cursor: 'pointer',
                    }}
                >
                    {wishlisted ? '💜 찜 완료' : '🤍 찜하기'}
                </button>
            </div>

            {/* 웨이팅 + 공간 유형 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ background: '#f5f3fb', borderRadius: '12px', padding: '12px' }}>
                    <p style={{ fontSize: '11px', color: '#b8a9d9', margin: '0 0 4px 0', fontWeight: 600 }}>현재 웨이팅</p>
                    <p style={{ fontSize: '16px', fontWeight: 'bold', color: '#5a4480', margin: 0 }}>
                        {place.waitingTime ?? '정보 없음'}
                    </p>
                </div>
                <div style={{ background: '#f5f3fb', borderRadius: '12px', padding: '12px' }}>
                    <p style={{ fontSize: '11px', color: '#b8a9d9', margin: '0 0 4px 0', fontWeight: 600 }}>공간 유형</p>
                    <p style={{ fontSize: '16px', fontWeight: 'bold', color: '#5a4480', margin: 0 }}>
                        {place.spaceType === 'indoor' ? '실내' : place.spaceType === 'outdoor' ? '실외' : '복합'}
                    </p>
                </div>
            </div>

            {/* 입장료 */}
            {place.admissionFee !== undefined && place.admissionFee > 0 && (
                <div style={{
                    background: '#f5f3fb',
                    borderRadius: '12px',
                    padding: '12px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#5a4480' }}>입장료</span>
                    <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#5a4480' }}>
                        {place.admissionFee.toLocaleString()}원
                    </span>
                </div>
            )}

            {/* 영업 정보 — 영업시간, 브레이크 타임, 휴무일 */}
            <div style={{
                background: '#f5f3fb',
                borderRadius: '12px',
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
            }}>
                <p style={{ fontSize: '11px', color: '#b8a9d9', margin: '0 0 4px 0', fontWeight: 600 }}>
                    영업 정보
                </p>
                {place.openingHours && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '12px', color: '#888' }}>영업시간</span>
                        <span style={{ fontSize: '12px', fontWeight: 600, color: '#5a4480' }}>{place.openingHours}</span>
                    </div>
                )}
                {place.breakTime && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '12px', color: '#888' }}>브레이크 타임</span>
                        <span style={{ fontSize: '12px', fontWeight: 600, color: '#e8a0b4' }}>{place.breakTime}</span>
                    </div>
                )}
                {place.closedDays && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '12px', color: '#888' }}>정기 휴무</span>
                        <span style={{ fontSize: '12px', fontWeight: 600, color: '#888' }}>{place.closedDays}</span>
                    </div>
                )}
            </div>

            {/* 액티비티 or 메뉴 */}
            {place.category === 'activity' ? (
                <div>
                    <p style={{ fontSize: '13px', fontWeight: 600, color: '#3d3d3d', marginBottom: '8px' }}>액티비티 목록</p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {place.recommendedMenus.map((menu) => (
                            <div key={menu.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ fontSize: '13px', color: '#3d3d3d' }}>
                                    {menu.name}
                                    {menu.isSignature && (
                                        <span style={{ marginLeft: '6px', fontSize: '10px', background: '#e4eef8', color: '#5a84b0', padding: '2px 6px', borderRadius: '999px' }}>인기</span>
                                    )}
                                </span>
                                <span style={{ fontSize: '13px', color: '#5a5a5a', fontWeight: 500 }}>{menu.price.toLocaleString()}원</span>
                            </div>
                        ))}
                    </div>
                    <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #e8e4f4', display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '13px', color: '#999' }}>예상 비용</span>
                        <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#5a4480' }}>{place.estimatedCost.toLocaleString()}원</span>
                    </div>
                </div>
            ) : (
                <div>
                    <p style={{ fontSize: '13px', fontWeight: 600, color: '#3d3d3d', marginBottom: '8px' }}>메뉴 가격</p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {place.recommendedMenus.map((menu) => (
                            <div key={menu.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ fontSize: '13px', color: '#3d3d3d' }}>
                                    {menu.name}
                                    {menu.isSignature && (
                                        <span style={{ marginLeft: '6px', fontSize: '10px', background: '#faeef2', color: '#c0607a', padding: '2px 6px', borderRadius: '999px' }}>시그니처</span>
                                    )}
                                </span>
                                <span style={{ fontSize: '13px', color: '#5a5a5a', fontWeight: 500 }}>{menu.price.toLocaleString()}원</span>
                            </div>
                        ))}
                    </div>
                    <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #e8e4f4', display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '13px', color: '#999' }}>예상 비용</span>
                        <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#5a4480' }}>{place.estimatedCost.toLocaleString()}원</span>
                    </div>
                </div>
            )}

            {/* 혼잡도 차트 */}
            <CrowdChart crowdData={mockCrowdData} highlightLow={false} />

            {/* 최근 방문 후기 */}
            <div>
                <p style={{ fontSize: '13px', fontWeight: 600, color: '#3d3d3d', marginBottom: '10px' }}>
                    최근 방문 후기
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {mockReviews.map((review, index) => (
                        <div key={index} style={{ background: '#f5f3fb', borderRadius: '12px', padding: '12px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                                <span style={{
                                    fontSize: '11px',
                                    background: '#e8e4f4',
                                    color: '#7b6bad',
                                    padding: '2px 8px',
                                    borderRadius: '999px',
                                    fontWeight: 600,
                                }}>
                                    {review.source}
                                </span>
                                <span style={{ fontSize: '11px', color: '#bbb' }}>
                                    {formatDaysAgo(review.daysAgo)}
                                </span>
                            </div>
                            <p style={{ fontSize: '13px', color: '#555', margin: 0, lineHeight: '1.6' }}>
                                {review.content}
                            </p>
                        </div>
                    ))}
                </div>
                <p style={{ fontSize: '11px', color: '#bbb', marginTop: '8px', textAlign: 'center' }}>
                    네이버 블로그 · 인스타그램 · 포잇 실시간 수집 · 방문 기준 업데이트
                </p>
            </div>

            {/* 폐점 경고 */}
            {(place.possiblyClosedWarning || isLikelyClosed(place.crawledAt, place.category)) && (
                <div style={{
                    background: '#faeef2',
                    borderRadius: '10px',
                    padding: '12px 14px',
                    border: '1px solid #f0c0cc',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                }}>
                    <span style={{ fontSize: '13px', color: '#c0607a', fontWeight: 700 }}>⚠ 폐점 가능성이 있어요</span>
                    <span style={{ fontSize: '12px', color: '#d08090' }}>
                        마지막 수집 정보: {place.crawledAt ?? '날짜 불명'} · 방문 전 확인을 권장해요
                    </span>
                </div>
            )}

            {/* 액션 버튼 */}
            <ActionButtonGroup place={place} />
        </div>
    );
}