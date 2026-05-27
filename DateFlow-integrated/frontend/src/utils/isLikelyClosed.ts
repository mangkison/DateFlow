import type { PlaceCategory } from "../types/course";

// 카테고리별 폐점 경고 기준일 — 업종 특성에 따라 다르게 설정
const THRESHOLD_BY_CATEGORY: Record<PlaceCategory, number> = {
    restaurant: 180,  // 6개월
    cafe: 180,        // 6개월
    shopping: 270,    // 9개월
    culture: 365,     // 1년
    activity: 545,    // 1년 6개월
};

export function isLikelyClosed(crawledAt?: string, category?: PlaceCategory): boolean {
    if (!crawledAt) return false;

    const threshold = category ? THRESHOLD_BY_CATEGORY[category] : 180;

    const diffDays = Math.floor(
        (new Date().getTime() - new Date(crawledAt).getTime()) / (1000 * 60 * 60 * 24)
    );

    return diffDays >= threshold;
}