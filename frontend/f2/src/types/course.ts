// 장소 카테고리
export type PlaceCategory = 
    | 'cafe'
    | 'restaurant'
    | 'activity'
    | 'shopping'
    | 'culture'; // 전시, 영화 등

// 공간 유형
export type SpaceType = 
    | 'indoor'
    | 'outdoor'
    | 'mixed'; // 루프탑 등

// 날씨 분류
export type WeatherType = 'sunny' | 'rainy' | 'cloudy';

export interface WeatherInfo {
    precipitationRate: number; 
    weatherType: WeatherType;
    description: string; // 날씨 설명( ex: "맑음", "흐림", "비")
}

//추천 메뉴 데이터
export interface RecommendedMenu {
    name: string;
    price: number;
    isSignature: boolean;
    menuCategory: 'food' | 'drink' | 'dessert' | 'side';
}

// 장소 데이터
export interface CoursePlace {
    time: string;
    name: string;
    desc: string;
    category: PlaceCategory;
    spaceType: SpaceType;
    satisfactionA: number;
    satisfactionB: number;
    lat: number; // 위도
    lng: number; // 경도
    waitingTime?: string;
    relationKeywords: string[];
    crawledAt?: string; // 크롤링 날짜
    possiblyClosedWarning?: boolean;
    recommendedMenus: RecommendedMenu[];
    estimatedCost: number;
    budgetRatio: number;
    isOverBudget: boolean;
    phone?: string;
    parkingAvailable?: boolean;
    reservationAvailable: boolean;
    naverReservationUrl?: string;
    reservationUrl?: string;
    admissionFee?: number;
    originalName?: string;
    travelTimeToNext?: number;
    travelModeToNext?: 'walk' | 'car' | 'transit';
    openingHours?: string;
    closedDays?: string;
    breakTime?: string;
}

// 코스 전체 데이터
export interface CourseResult {
    title: string; 
    places: CoursePlace[];
    personA: string[];
    personB: string[];
    common: string[];
    weather: WeatherInfo;
    budget: number;
}

// 시간대별 혼잡도 데이터
export interface CrowdByHour {
    hour: number;
    level: 'low'| 'mid'| 'high';
}

// 후기 한 개의 데이터
export interface Review {
    source: string;
    content: string;
    daysAgo: number;
}