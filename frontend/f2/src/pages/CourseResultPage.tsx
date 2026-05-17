import { useState } from "react";
import type { CoursePlace } from "../types/course";
import { mockCourseData } from "../mocks/courseData";
// mockAlternativePlaces 제거 — 대체 장소 기능 제거
import PreferenceIntersection from "../components/PreferenceIntersection";
import CourseTimeline from "../components/CourseTimeline";
import PlaceDetailCard from "../components/PlaceDetailCard";
import { getWeatherEmoji } from "../utils/getWeatherEmoji";

export default function CourseResultPage() {
    const [selectedPlace, setSelectedPlace] = useState<CoursePlace | null>(null);

    // places state — totalCost 자동 재계산을 위해 state로 관리
    const [places, setPlaces] = useState<CoursePlace[]>(mockCourseData.places);

    // places 기반 totalCost 실시간 계산
    const totalCost = places.reduce((sum, place) => sum + place.estimatedCost, 0);
    const isOverBudget = totalCost > mockCourseData.budget;

    return (
        <div style={{
            minHeight: '100vh',
            background: '#F5F3FB',
            padding: '24px 32px',
        }}>
            <div style={{ marginBottom: '24px' }}>
                <h1 style={{
                    fontSize: '24px',
                    fontWeight: 'bold',
                    color: '#5a4480',
                    margin: 0,
                }}>
                    {mockCourseData.title} {getWeatherEmoji(mockCourseData.weather.weatherType)}
                </h1>
            </div>

           {/* 예산 진행 바 — 항상 표시, 초과 시 빨간색으로 변경 */}
            <div style={{
                background: '#ffffff',
                borderRadius: '12px',
                padding: '14px 18px',
                marginTop: '12px',
                marginBottom: '24px', // 아래 공간 추가
                border: `1px solid ${isOverBudget ? '#f5c0c0' : '#e8e4f4'}`,
            }}>
                {/* 상단 — 예산 텍스트 정보 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontSize: '13px', color: '#888' }}>
                        예상 총 비용
                    </span>
                    <span style={{
                        fontSize: '14px',
                        fontWeight: 700,
                        color: isOverBudget ? '#e05555' : '#5a4480', // 초과 시 빨간색
                    }}>
                        {totalCost.toLocaleString()}원
                        <span style={{ fontSize: '12px', fontWeight: 400, color: '#aaa', marginLeft: '6px' }}>
                            / {mockCourseData.budget.toLocaleString()}원
                        </span>
                    </span>
                </div>

                {/* 진행 바 — 예산 대비 사용 비율 시각화 */}
                <div style={{
                    width: '100%',
                    height: '8px',
                    background: '#eee',
                    borderRadius: '999px',
                    overflow: 'hidden',
                }}>
                    <div style={{
                        width: `${Math.min((totalCost / mockCourseData.budget) * 100, 100)}%`,
                        height: '100%',
                        background: isOverBudget ? '#e05555' : '#b8a9d9', // 초과 시 빨간색
                        borderRadius: '999px',
                        transition: 'width 0.3s ease',
                    }} />
                </div>

                {/* 하단 — 남은 예산 or 초과 금액 */}
                <div style={{ marginTop: '6px', fontSize: '12px', color: isOverBudget ? '#e05555' : '#b8a9d9', textAlign: 'right' }}>
                    {isOverBudget
                        ? `⚠️ ${(totalCost - mockCourseData.budget).toLocaleString()}원 초과`
                        : `${(mockCourseData.budget - totalCost).toLocaleString()}원 남음`
                    }
                </div>
            </div>

            <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 2fr',
                gap: '24px',
                alignItems: 'start',
            }}>
                {/* 왼쪽 — 취향 교집합 */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <PreferenceIntersection
                        personA={mockCourseData.personA}
                        personB={mockCourseData.personB}
                        common={mockCourseData.common}
                    />
                    {/* 카카오 지도 — API 키 발급 후 추가 예정 */}
                </div>

                {/* 오른쪽 — 코스 타임라인 */}
                <div style={{
                    background: '#FFFFFF',
                    borderRadius: '16px',
                    padding: '16px',
                    border: '1px solid #E8E4F4',
                    boxShadow: '0 1px 4px rgba(184,169,217,0.15)',
                }}>
                    <CourseTimeline
                        places={places}
                        onSelectPlace={setSelectedPlace}
                    />
                </div>
            </div>

            {selectedPlace && (
                <div style={{ marginTop: '24px' }}>
                    <PlaceDetailCard
                        place={selectedPlace}
                        onClose={() => setSelectedPlace(null)}
                        onSkip={(place) => setPlaces((prev) => prev.filter((p) => p.name !== place.name))}
                        onRecommendOther={(place) => alert(`${place.name} 대신 다른 장소를 추천받을게요! (Week 3 API 연동 예정)`)}
                        onWishlist={(place) => console.log('찜하기:', place.name)}
                    />
                </div>
            )}
        </div>
    );
}