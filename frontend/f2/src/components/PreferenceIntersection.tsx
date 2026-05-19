interface PreferenceIntersectionProps {
    personA: string[];
    personB: string[];
    common: string[];
}

interface TagProps {
    label: string;
    variant: 'a' | 'b' | 'common';
}

function getTagStyle(variant: TagProps['variant']): React.CSSProperties {
    switch (variant) {
        case 'a': return { background: '#E8E4F4', color: '#7B6BAD' };
        case 'b': return { background: '#FAEEF2', color: '#c0607a' };
        case 'common': return { background: '#E4EEF8', color: '#5a84b0' };
    }
}

function getLegendColor(variant: 'a' | 'b' | 'common'): string {
    switch (variant) {
        case "a": return '#b8a9d9';
        case "b": return '#e8a0b4';
        case "common": return '#a8c4e0';
    }
}

function Tag({ label, variant }: TagProps) {
    return (
        <span style={{
            ...getTagStyle(variant),
            display: 'inline-block',
            padding: '4px 12px',
            borderRadius: '999px',
            fontSize: '13px',
            fontWeight: 500,
        }}>
            {label}
        </span>
    );
}

function LegendDot({ variant, label }: { variant: 'a' | 'b' | 'common'; label: string }) {
    return (
        <div style={{ display: "flex", alignItems: "center", gap: '4px', fontSize: '12px', color: '#999' }}>
            <span style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                background: getLegendColor(variant),
                display: 'inline-block',
            }} />
            {label}
        </div>
    );
}

export default function PreferenceIntersection({ personA, personB, common }: PreferenceIntersectionProps) {
    return (
        <div style={{
            background: '#FFFFFF',
            borderRadius: '16px',
            padding: '16px',
            border: '1px solid #E8E4F4',
            boxShadow: '0 1px 4px rgba(184,169,217,0.15)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
        }}>
            <div>
                <p style={{ fontSize: '11px', color: '#B8A9D9', marginBottom: '6px', fontWeight: 600 }}>
                    A님 선호
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {personA.map((keyword) => (
                        <Tag key={keyword} label={keyword} variant="a" />
                    ))}
                </div>
            </div>

            <div>
                <p style={{ fontSize: '11px', color: '#E8A0B4', marginBottom: '6px', fontWeight: 600 }}>
                    B님 선호
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {personB.map((keyword) => (
                        <Tag key={keyword} label={keyword} variant="b" />
                    ))}
                </div>
            </div>

            <hr style={{ border: 'none', borderTop: '1px solid #E8E4F4' }} />

            <div>
                <p style={{ fontSize: '11px', color: '#A8C4E0', marginBottom: '6px', fontWeight: 600 }}>
                    공통 교집합
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {common.map((keyword) => (
                        <Tag key={keyword} label={keyword} variant="common" />
                    ))}
                </div>
            </div>

            <div style={{ display: 'flex', gap: '16px', paddingTop: '4px' }}>
                <LegendDot variant="a" label="A님" />
                <LegendDot variant="b" label="B님" />
                <LegendDot variant="common" label="공통" />
            </div>
        </div>
    );
}