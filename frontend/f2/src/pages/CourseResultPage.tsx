import { useState, useEffect } from "react";
import type { CoursePlace, CourseResult, WeatherType } from "../types/course";
import { mockCourseData } from "../mocks/courseData";
import PreferenceIntersection from "../components/PreferenceIntersection";
import CourseTimeline from "../components/CourseTimeline";
import PlaceDetailCard from "../components/PlaceDetailCard";
import KakaoMap from "../components/KakaoMap";
import { getWeatherEmoji } from "../utils/getWeatherEmoji";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function mapCategory(cat: string): CoursePlace["category"] {
    if (cat.includes("카페")) return "cafe";
    if (cat.includes("식당") || cat.includes("레스토랑")) return "restaurant";
    if (cat.includes("바") || cat.includes("펍")) return "restaurant";
    if (cat.includes("쇼핑") || cat.includes("팝업")) return "shopping";
    if (cat.includes("전시") || cat.includes("갤러리")) return "culture";
    return "activity";
}

function adaptPlaces(backendPlaces: any[], budget: number): CoursePlace[] {
    const fallbackTimes = ["13:00", "15:30", "18:00", "20:00"];
    return backendPlaces.map((p: any, i: number) => {
        const cost = p.price || 0;
        return {
            time:                p.time || fallbackTimes[i] || "13:00",
            name:                p.name,
            desc:                p.category || "",
            category:            mapCategory(p.category || ""),
            spaceType:           "indoor" as const,
            satisfactionA:       70 + ((p.name.charCodeAt(0) || 0) % 25),
            satisfactionB:       68 + ((p.name.charCodeAt(1) || 0) % 27),
            lat:                 p.latitude  ? parseFloat(p.latitude)  : 37.5665,
            lng:                 p.longitude ? parseFloat(p.longitude) : 126.9780,
            estimatedCost:       cost,
            budgetRatio:         budget > 0 ? Math.round((cost / budget) * 100) : 0,
            isOverBudget:        cost > budget,
            recommendedMenus:    [],
            reservationAvailable: false,
            relationKeywords:    [],
            travelTimeToNext:    10,
            travelModeToNext:    "walk" as const,
        };
    });
}

export default function CourseResultPage() {
    const [selectedPlace, setSelectedPlace] = useState<CoursePlace | null>(null);
    const [courseData, setCourseData]       = useState<CourseResult>(mockCourseData);
    const [places, setPlaces]               = useState<CoursePlace[]>(mockCourseData.places);
    const [isLoading, setIsLoading]         = useState(false);

    useEffect(() => {
        const params  = new URLSearchParams(window.location.search);
        const session = params.get("session");
        if (!session) return; // 파라미터 없으면 mock 데이터 사용

        const region  = params.get("region")  || "성수동";
        const lat     = parseFloat(params.get("lat")    || "37.5665");
        const lon     = parseFloat(params.get("lon")    || "126.9780");
        const budget  = parseInt(params.get("budget")   || "100000");
        const weather = (params.get("weather") || "cloudy") as WeatherType;
        const tagsA   = (params.get("tagsA")  || "").split(",").filter(Boolean);
        const tagsB   = (params.get("tagsB")  || "").split(",").filter(Boolean);
        const common  = tagsA.filter(t => tagsB.includes(t));

        // URL 파라미터로 메타데이터 업데이트
        setCourseData(prev => ({
            ...prev,
            title:   `${region} 데이트 코스`,
            personA: tagsA.length > 0 ? tagsA : prev.personA,
            personB: tagsB.length > 0 ? tagsB : prev.personB,
            common:  tagsA.length > 0 || tagsB.length > 0 ? common : prev.common,
            budget,
            weather: {
                precipitationRate: parseInt(params.get("pop") || "0"),
                weatherType:       weather,
                description:       params.get("skyDesc") || weather,
            },
        }));

        // 백엔드에서 실제 코스 가져오기
        setIsLoading(true);
        fetch(`${API_BASE}/course/generate`, {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id:    `${session}_A`,
                region, lat, lon,
                start_time: "13:00",
                end_time:   "21:00",
                budget,
                weather,
            }),
        })
            .then(r => r.json())
            .then(data => {
                const backendPlaces = data.courses?.[0]?.places || [];
                const adapted = adaptPlaces(backendPlaces, budget);
                if (adapted.length > 0) setPlaces(adapted);
            })
            .catch(() => {}) // 백엔드 미연결 시 mock 유지
            .finally(() => setIsLoading(false));
    }, []);

    const totalCost    = places.reduce((sum, p) => sum + p.estimatedCost, 0);
    const isOverBudget = totalCost > courseData.budget;

    return (
        <div style={{ minHeight: "100vh", background: "#F5F3FB", padding: "24px 32px" }}>

            {/* 헤더 */}
            <div style={{ marginBottom: "24px" }}>
                <h1 style={{ fontSize: "24px", fontWeight: "bold", color: "#5a4480", margin: 0 }}>
                    {courseData.title} {getWeatherEmoji(courseData.weather.weatherType)}
                </h1>
                {isLoading && (
                    <p style={{ fontSize: "13px", color: "#B8A9D9", margin: "4px 0 0" }}>
                        코스 불러오는 중...
                    </p>
                )}
            </div>

            {/* 예산 진행 바 */}
            <div style={{
                background:    "#ffffff",
                borderRadius:  "12px",
                padding:       "14px 18px",
                marginBottom:  "24px",
                border:        `1px solid ${isOverBudget ? "#f5c0c0" : "#e8e4f4"}`,
            }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <span style={{ fontSize: "13px", color: "#888" }}>예상 총 비용</span>
                    <span style={{ fontSize: "14px", fontWeight: 700, color: isOverBudget ? "#e05555" : "#5a4480" }}>
                        {totalCost.toLocaleString()}원
                        <span style={{ fontSize: "12px", fontWeight: 400, color: "#aaa", marginLeft: "6px" }}>
                            / {courseData.budget.toLocaleString()}원
                        </span>
                    </span>
                </div>
                <div style={{ width: "100%", height: "8px", background: "#eee", borderRadius: "999px", overflow: "hidden" }}>
                    <div style={{
                        width:      `${Math.min((totalCost / courseData.budget) * 100, 100)}%`,
                        height:     "100%",
                        background: isOverBudget ? "#e05555" : "#b8a9d9",
                        borderRadius: "999px",
                        transition: "width 0.3s ease",
                    }} />
                </div>
                <div style={{ marginTop: "6px", fontSize: "12px", color: isOverBudget ? "#e05555" : "#b8a9d9", textAlign: "right" }}>
                    {isOverBudget
                        ? `⚠️ ${(totalCost - courseData.budget).toLocaleString()}원 초과`
                        : `${(courseData.budget - totalCost).toLocaleString()}원 남음`}
                </div>
            </div>

            {/* 메인 그리드 */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "24px", alignItems: "start" }}>

                {/* 왼쪽 — 취향 교집합 + 지도 */}
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                    <PreferenceIntersection
                        personA={courseData.personA}
                        personB={courseData.personB}
                        common={courseData.common}
                    />
                    <KakaoMap
                        places={places}
                        selectedPlace={selectedPlace}
                        onSelectPlace={setSelectedPlace}
                    />
                </div>

                {/* 오른쪽 — 코스 타임라인 */}
                <div style={{
                    background:   "#FFFFFF",
                    borderRadius: "16px",
                    padding:      "16px",
                    border:       "1px solid #E8E4F4",
                    boxShadow:    "0 1px 4px rgba(184,169,217,0.15)",
                }}>
                    <CourseTimeline
                        places={places}
                        onSelectPlace={setSelectedPlace}
                    />
                </div>
            </div>

            {/* 장소 상세 카드 */}
            {selectedPlace && (
                <div style={{ marginTop: "24px" }}>
                    <PlaceDetailCard
                        place={selectedPlace}
                        onClose={() => setSelectedPlace(null)}
                        onSkip={(place) => setPlaces(prev => prev.filter(p => p.name !== place.name))}
                        onRecommendOther={(place) => alert(`${place.name} 대신 다른 장소를 추천받을게요!`)}
                        onWishlist={(place) => console.log("찜하기:", place.name)}
                    />
                </div>
            )}
        </div>
    );
}
