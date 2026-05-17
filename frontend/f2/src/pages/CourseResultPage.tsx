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
    const [places] = useState<CoursePlace[]>(mockCourseData.places);

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

                {/* 예산 초과 아닐 때만 예산 정보 표시 */}
                {!isOverBudget && (
                    <p style={{ fontSize: '13px', color: '#b8a9d9', margin: '6px 0 0 0' }}>
                        예산 {mockCourseData.budget.toLocaleString()}원 중 {totalCost.toLocaleString()}원 사용
                    </p>
                )}

                {/* 전체 예산 초과 경고 박스 */}
                {isOverBudget && (
                    <div style={{
                        background: '#fff4e6',
                        border: '1px solid #f5d08a',
                        borderRadius: '12px',
                        padding: '14px 18px',
                        marginTop: '12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                    }}>
                        <span style={{ fontSize: '24px' }}>⚠️</span>
                        <div>
                            <p style={{ fontSize: '14px', fontWeight: 700, color: '#d47c00', margin: 0 }}>
                                전체 예산을 초과한 코스예요
                            </p>
                            <p style={{ fontSize: '12px', color: '#b36200', margin: '4px 0 0 0' }}>
                                예산 {mockCourseData.budget.toLocaleString()}원 · 예상 총 비용 {totalCost.toLocaleString()}원
                                ({Math.round((totalCost / mockCourseData.budget) * 100)}% 사용)
                            </p>
                        </div>
                    </div>
                )}
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
                    />
                </div>
            )}
        </div>
    );
}