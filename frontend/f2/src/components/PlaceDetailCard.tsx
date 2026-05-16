import { useState } from "react";
import type { CoursePlace } from "../types/course";
import CrowdChart from "./CrowdChart";
import ActionButtonGroup from "./ActionButtonGroup";
import { mockCrowdData, mockReviews } from "../mocks/courseData";
import { formatDaysAgo } from "../utils/formatDaysAgo";
import { isLikelyClosed } from "../utils/isLikelyClosed";
// 후기 날짜 포맷 유틸, 폐점 가능성 판단 유틸

interface Props {
    place: CoursePlace;
    onClose: () => void;
}

export default function PlaceDetailCard({ place, onClose }: Props) {
    const [activeTab, setActiveTab] = useState<'original' | 'alternative'>('original');
    const [showTab, setShowTab] = useState(false);
    const [showLowCrowd, setShowLowCrowd] = useState(false);

    const displayPlace = activeTab === 'alternative' && place.alternativePlace
        ? place.alternativePlace
        : place;

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
                        {displayPlace.name}
                        {activeTab === 'alternative' && (
                            <span style={{
                                marginLeft: '8px',
                                fontSize: '11px',
                                background: '#e4eef8',
                                color: '#5a84b0',
                                padding: '2px 8px',
                                borderRadius: '999px',
                                fontWeight: 500,
                                verticalAlign: 'middle',
                            }}>
                                대체
                            </span>
                        )}
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
                        {displayPlace.desc}
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

            {/* 탭 — 대체 장소 있을 때만 표시 */}
            {showTab && place.alternativePlace && (
                <div style={{
                    display: 'flex',
                    gap: '8px',
                    borderBottom: '2px solid #e8e4f4',
                }}>
                    <button
                        onClick={() => setActiveTab('original')}
                        style={{
                            padding: '8px 16px',
                            background: 'none',
                            border: 'none',
                            borderBottom: activeTab === 'original' ? '2px solid #b8a9d9' : '2px solid transparent',
                            color: activeTab === 'original' ? '#5a4480' : '#999',
                            fontWeight: activeTab === 'original' ? 700 : 400,
                            fontSize: '13px',
                            cursor: 'pointer',
                            marginBottom: '-2px',
                        }}
                    >
                        원래 장소
                    </button>
                    <button
                        onClick={() => { setShowTab(true); setActiveTab('alternative'); }}
                        style={{
                            padding: '8px 16px',
                            background: 'none',
                            border: 'none',
                            borderBottom: activeTab === 'alternative' ? '2px solid #b8a9d9' : '2px solid transparent',
                            color: activeTab === 'alternative' ? '#5a4480' : '#999',
                            fontWeight: activeTab === 'alternative' ? 700 : 400,
                            fontSize: '13px',
                            cursor: 'pointer',
                            marginBottom: '-2px',
                        }}
                    >
                        대체 장소
                    </button>
                </div>
            )}

            {/* 웨이팅 + 공간 유형 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ background: '#f5f3fb', borderRadius: '12px', padding: '12px' }}>
                    <p style={{ fontSize: '11px', color: '#b8a9d9', margin: '0 0 4px 0', fontWeight: 600 }}>현재 웨이팅</p>
                    <p style={{ fontSize: '16px', fontWeight: 'bold', color: '#5a4480', margin: 0 }}>
                        {displayPlace.waitingTime ?? '정보 없음'}
                    </p>
                </div>
                <div style={{ background: '#f5f3fb', borderRadius: '12px', padding: '12px' }}>
                    <p style={{ fontSize: '11px', color: '#b8a9d9', margin: '0 0 4px 0', fontWeight: 600 }}>공간 유형</p>
                    <p style={{ fontSize: '16px', fontWeight: 'bold', color: '#5a4480', margin: 0 }}>
                        {displayPlace.spaceType === 'indoor' ? '실내' : displayPlace.spaceType === 'outdoor' ? '실외' : '복합'}
                    </p>
                </div>
            </div>

            {/* 입장료 */}
            {displayPlace.admissionFee !== undefined && displayPlace.admissionFee > 0 && (
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
                        {displayPlace.admissionFee.toLocaleString()}원
                    </span>
                </div>
            )}

            {/* 액티비티 or 메뉴 */}
            {displayPlace.category === 'activity' ? (
                <div>
                    <p style={{ fontSize: '13px', fontWeight: 600, color: '#3d3d3d', marginBottom: '8px' }}>액티비티 목록</p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {displayPlace.recommendedMenus.map((menu) => (
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
                        <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#5a4480' }}>{displayPlace.estimatedCost.toLocaleString()}원</span>
                    </div>
                </div>
            ) : (
                <div>
                    <p style={{ fontSize: '13px', fontWeight: 600, color: '#3d3d3d', marginBottom: '8px' }}>메뉴 가격</p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {displayPlace.recommendedMenus.map((menu) => (
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
                        <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#5a4480' }}>{displayPlace.estimatedCost.toLocaleString()}원</span>
                    </div>
                </div>
            )}

            {/* 혼잡도 차트 */}
            <CrowdChart crowdData={mockCrowdData} highlightLow={showLowCrowd} />

            {/* 최근 방문 후기 — mockReviews Mock 데이터, Week 3에 실제 API로 교체 예정 */}
            <div>
                <p style={{ fontSize: '13px', fontWeight: 600, color: '#3d3d3d', marginBottom: '10px' }}>
                    최근 방문 후기
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {mockReviews.map((review, index) => (
                        <div key={index} style={{ background: '#f5f3fb', borderRadius: '12px', padding: '12px' }}>
                            {/* 출처 뱃지 + 며칠 전 */}
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

            {/* 예산 초과 경고 */}
            {displayPlace.isOverBudget && (
                <div style={{
                    background: '#fff4e6',
                    borderRadius: '10px',
                    padding: '12px 14px',
                    border: '1px solid #f5d08a',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                }}>
                    <span style={{ fontSize: '13px', color: '#d47c00', fontWeight: 700 }}>⚠ 예산 초과 장소예요</span>
                    <span style={{ fontSize: '12px', color: '#b36200' }}>
                        예상 비용 {displayPlace.estimatedCost.toLocaleString()}원 · 전체 예산의 {displayPlace.budgetRatio}% 차지해요
                    </span>
                </div>
            )}

            {/* 폐점 경고 — crawledAt 날짜 함께 표시 */}
            {(displayPlace.possiblyClosedWarning || isLikelyClosed(displayPlace.crawledAt, displayPlace.category)) && (
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
                        마지막 수집 정보: {displayPlace.crawledAt ?? '날짜 불명'} · 방문 전 확인을 권장해요
                    </span>
                </div>
            )}

            {/* 액션 버튼 */}
            <ActionButtonGroup
                place={displayPlace}
                onSelectAlternative={() => { setShowTab(true); setActiveTab('alternative'); }}
                onShowLowCrowd={() => setShowLowCrowd((prev) => !prev)}
                tabVisible={showTab}
            />
        </div>
    );
}