import math
import os
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
KMA_API_KEY = os.getenv("KMA_API_KEY")

# 강수형태 코드
PTY_CODE = {
    0: "없음",
    1: "비",
    2: "비/눈",
    3: "눈",
    4: "소나기",
    5: "빗방울",
    6: "빗방울/눈날림",
    7: "눈날림",
}


def latlon_to_grid(lat: float, lon: float) -> dict:
    """위경도 → 기상청 격자 좌표 변환"""
    RE = 6371.00877
    GRID = 5.0
    SLAT1 = 30.0
    SLAT2 = 60.0
    OLON = 126.0
    OLAT = 38.0
    XO = 43
    YO = 136

    DEGRAD = math.pi / 180.0

    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)

    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    nx = int(ra * math.sin(theta) + XO + 0.5)
    ny = int(ro - ra * math.cos(theta) + YO + 0.5)

    return {"nx": nx, "ny": ny}


async def get_weather(lat: float, lon: float, region: str = "알 수 없음") -> dict:
    """위경도 기반 날씨 조회"""
    grid = latlon_to_grid(lat, lon)

    now = datetime.now()
    prev = now - timedelta(hours=1)
    base_date = prev.strftime("%Y%m%d")
    base_time = prev.strftime("%H00")

    url = (
        f"http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
        f"?serviceKey={KMA_API_KEY}"
        f"&numOfRows=10&pageNo=1&dataType=JSON"
        f"&base_date={base_date}&base_time={base_time}"
        f"&nx={grid['nx']}&ny={grid['ny']}"
    )

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=5.0)
            data = res.json()

        items = data["response"]["body"]["items"]["item"]

        result = {}
        for item in items:
            result[item["category"]] = item["obsrValue"]

        temp     = float(result.get("T1H", 0))
        rain     = float(result.get("RN1", 0))
        humidity = float(result.get("REH", 0))
        wind     = float(result.get("WSD", 0))
        pty      = int(float(result.get("PTY", 0)))

        pty_desc = PTY_CODE.get(pty, "알 수 없음")
        # TODO: 빗방울(5), 눈날림(7) 등 약한 강수는 야외 가능하도록 세분화 필요

        is_outdoor_ok = pty == 0

        return {
            "region":        region,
            "temperature":   temp,
            "rainfall":      rain,
            "humidity":      humidity,
            "wind_speed":    wind,
            "pty_code":      pty,
            "description":   pty_desc,
            "is_outdoor_ok": is_outdoor_ok,
        }

    except Exception as e:
        return {
            "region":        region,
            "temperature":   None,
            "rainfall":      None,
            "humidity":      None,
            "wind_speed":    None,
            "pty_code":      None,
            "description":   "날씨 정보 없음",
            "is_outdoor_ok": True,
            "error":         str(e),
        }