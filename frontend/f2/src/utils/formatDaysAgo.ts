// daysAgo 숫자를 사람이 읽기 좋은 문자열로 변환
// — 숫자 그대로 노출 시 "1423일 전" 같은 어색한 표현 방지
export function formatDaysAgo(days: number): string {
    if (days < 7) {
        return `${days}일 전`;
    } else if (days < 30) {
        const weeks = Math.floor(days / 7);
        return `${weeks}주 전`;
    } else if (days < 365) {
        const months = Math.floor(days / 30);
        return `${months}달 전`;
    } else {
        const years = Math.floor(days / 365);
        return `${years}년 전`;
    }
}