import { useState } from "react";
import type { CoursePlace } from "../types/course";
import CoursePlaceItem from "./CoursePlaceItem";
import { mockAlternativePlaces } from "../mocks/courseData";
// mockAlternativePlaces — 대체 장소 존재 여부 확인용

interface Props {
    places: CoursePlace[];
    onSelectPlace: (place: CoursePlace) => void;
    onReRequest: (rejectedPlace: CoursePlace[]) => void;
    reRequestCount: Record<string, number>;
}

export default function CourseTimeline({ places, onSelectPlace, onReRequest, reRequestCount }: Props) {
    const [checkedNames, setCheckedNames] = useState<Set<string>>(new Set());

    const handleCheck = (name: string) => {
        setCheckedNames((prev) => {
            const next = new Set(prev);
            if (next.has(name)) {
                next.delete(name);
            } else {
                next.add(name);
            }
            return next;
        });
    };

    const handleReRequest = () => {
        // 체크된 장소만 필터링해서 상위 컴포넌트로 전달
        const reRequested = places.filter((p) => checkedNames.has(p.name));
        onReRequest(reRequested);
    };

    const hasRejected = checkedNames.size > 0;

    return (
        <div style={{ padding: '0 16px' }}>
            <h2 style={{ color: "#888", fontSize: '16px', fontWeight: 'bold', marginBottom: '4px' }}>
                코스 타임라인
            </h2>
            <p style={{ fontSize: '12px', color: "#888", marginBottom: '12px' }}>
                마음에 들지 않는 장소는 체크하고 다시 추천받아요
            </p>

            {places.map((place, index) => {
                const placeKey = place.originalName ?? place.name;

                return (
                <div key={index}>
                    {/* 대체 장소 없는 장소 위에 개별 안내 — 체크박스 없는 이유 설명 */}
                    {(!mockAlternativePlaces[place.name] || (reRequestCount[place.name] ?? 0) >= mockAlternativePlaces[place.name].length) && (
                        <div style={{
                            fontSize: '11px',
                            color: '#b8a9d9',
                            marginTop: '4px',
                            marginLeft: '24px',
                            marginBottom: '4px',
                        }}>
                            {(reRequestCount[place.name] ?? 0) >= (mockAlternativePlaces[place.name]?.length ?? 0)
                                && mockAlternativePlaces[place.name]
                                ? '🚫 추천 횟수가 모두 소진됐어요'
                                : '💜 대체 장소 수집 중'
                            }
                        </div>
                    )}

                    {mockAlternativePlaces[place.name] && (reRequestCount[place.name] ?? 0) > 0 && (reRequestCount[place.name] ?? 0) < mockAlternativePlaces[place.name].length && (
                        <div style={{
                            fontSize: '11px',
                            color: '#b8a9d9',
                            marginTop: '4px',
                            marginLeft: '24px',
                            marginBottom: '4px',
                        }}>
                            💜 추천 횟수 {reRequestCount[place.name]}/{mockAlternativePlaces[place.name].length}
                        </div>
                    )}

                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                        {/* 대체 장소 있으면 체크박스, 없으면 – 표시 */}
                    
                        {mockAlternativePlaces[place.name] && (reRequestCount[place.name] ?? 0) < mockAlternativePlaces[place.name].length ? (
                            <input
                                type="checkbox"
                                    checked={checkedNames.has(place.name)}
                                    onChange={() => handleCheck(place.name)}
                                    style={{ marginTop: '16px', width: '16px', height: '16px', cursor: 'pointer' }}
                                />
                            ) : (
                                <span style={{
                                    marginTop: '18px',
                                    fontSize: '10px',
                                    color: '#bbb',
                                    minWidth: '16px',
                                    textAlign: 'center',
                                }}>
                                    –
                                </span>
                            )}

                            <div style={{ flex: 1 }}>
                                <CoursePlaceItem
                                    place={place}
                                    onClick={onSelectPlace}
                                />
                            </div>
                        </div>
                    </div>
                );
            })}

            {/* 체크된 장소 있을 때만 다시 추천받기 버튼 표시 */}
            {hasRejected && (
                <button
                    onClick={handleReRequest}
                    style={{
                        marginTop: '16px',
                        width: '100%',
                        padding: '12px',
                        background: '#E8899A',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        fontSize: '14px',
                        fontWeight: 'bold',
                        cursor: 'pointer',
                    }}
                >
                    체크한 장소 다시 추천 받기
                </button>
            )}
        </div>
    );
}