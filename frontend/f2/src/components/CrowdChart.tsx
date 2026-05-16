import type { CrowdByHour } from "../types/course";

interface Props {
    crowdData: CrowdByHour[];
    highlightLow?: boolean;
}

function getBarColor(level: 'low' | 'mid' | 'high'): string {
    switch (level) {
        case "low": return '#b8a9d9';
        case "mid": return '#e8a0b4';
        case "high": return '#d4849a';
    }
}

function getLevelText(level: 'low' | 'mid' | 'high'): string {
    switch (level) {
        case "low": return '한산';
        case "mid": return '보통';
        case "high": return '혼잡';
    }
}

function getBarHeight(level: 'low' | 'mid' | 'high'): string {
    switch (level) {
        case "low": return '20%';
        case "mid": return '55%';
        case "high": return '100%';
    }
}

export default function CrowdChart({ crowdData, highlightLow = false }: Props) {
    return (
        <div style={{
            background: "#ffffff",
            borderRadius: '16px',
            padding: '16px',
            border: '1px solid #e8e4f4',
            boxShadow: '0 1px 4px rgba(184, 169, 217, 0.15)',
        }}>
            <p style={{ fontSize: '13px', fontWeight: 600, color: '#3d3d3d', marginBottom: '16px' }}>
                시간대별 혼잡도
            </p>

            <div style={{
                display: 'flex',
                alignItems: 'flex-end',
                gap: '8px',
                height: '120px',
                marginBottom: '8px',
            }}>
                {crowdData.map((item) => (
                    <div
                        key={item.hour}
                        style={{
                            flex: 1,
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'flex-end',
                            height: '100%',
                        }}
                    >
                        <span style={{
                            fontSize: '9px',
                            color: getBarColor(item.level),
                            marginBottom: '4px',
                            fontWeight: 600,
                        }}>
                            {getLevelText(item.level)}
                        </span>
                        <div style={{
                            width: '100%',
                            height: getBarHeight(item.level),
                            background: getBarColor(item.level),
                            borderRadius: '4px 4px 0 0',
                            outline: highlightLow && item.level === 'low' ? '2px solid #5a4480' : 'none',
                        }} />
                    </div>
                ))}
            </div>

            <div style={{
                display: 'flex',
                gap: '8px',
                borderTop: '1px solid #e8e4f4',
                paddingTop: '8px',
            }}>
                {crowdData.map((item) => (
                    <div
                        key={item.hour}
                        style={{
                            flex: 1,
                            textAlign: 'center',
                            fontSize: '11px',
                            color: "#999",
                        }}
                    >
                        {item.hour}시
                    </div>
                ))}
            </div>

            <div style={{
                display: 'flex',
                gap: '16px',
                marginTop: '12px',
                justifyContent: 'center',
            }}>
                {(['low', 'mid', 'high'] as const).map((level) => (
                    <div key={level} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <span style={{
                            width: '10px',
                            height: '10px',
                            borderRadius: '2px',
                            background: getBarColor(level),
                            display: 'inline-block',
                        }} />
                        <span style={{ fontSize: '11px', color: '#999' }}>
                            {getLevelText(level)}
                        </span>
                    </div>
                ))}
            </div>

            {highlightLow && (
                <p style={{ fontSize: '12px', color: '#5a4480', textAlign: 'center', marginTop: '8px', fontWeight: 600 }}>
                    💜 표시된 시간대에 방문하면 웨이팅이 적어요!
                </p>
            )}
        </div>
    );
}