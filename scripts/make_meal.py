"""경북일고 중식 급식표 이미지를 만든다.

NEIS 급식 API에서 오늘(또는 MEAL_DATE=YYYYMMDD) 중식을 조회해
images/YYYY-MM-DD.png 와 images/YYYY-MM-DD.json 을 만든다.
json의 status: "ok"(이미지 생성) / "no_lunch"(등록된 중식 없음)
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageFont

KST = dt.timezone(dt.timedelta(hours=9))
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
API = ("https://open.neis.go.kr/hub/mealServiceDietInfo?Type=json"
       "&ATPT_OFCDC_SC_CODE=R10&SD_SCHUL_CODE=8750724&MLSV_YMD={ymd}")


def fetch_lunch(ymd):
    with urllib.request.urlopen(API.format(ymd=ymd), timeout=30) as r:
        data = json.load(r)
    if "mealServiceDietInfo" not in data:
        code = data.get("RESULT", {}).get("CODE", "")
        if code == "INFO-200":
            return None
        raise RuntimeError(f"NEIS 오류: {data}")
    rows = data["mealServiceDietInfo"][1]["row"]
    for row in rows:
        if row.get("MMEAL_SC_NM") == "중식":
            return row["DDISH_NM"]
    return None


def clean(ddish):
    items = []
    for p in ddish.split("<br/>"):
        p = p.strip().lstrip("ㅁ").strip()
        p = re.sub(r"\s*\([\d.\s]+\)\s*$", "", p)
        p = p.replace("(자율)", "").strip()
        p = re.sub(r"\s*,\s*", "&", p)
        if p:
            items.append(p)
    return items


def render(lines, path):
    img = Image.new("RGB", (1080, 1920), "white")
    d = ImageDraw.Draw(img)
    lh = 82
    top = (1920 - lh * len(lines)) // 2
    for i, text in enumerate(lines):
        size = 64
        font = ImageFont.truetype(FONT, size, index=1)
        while d.textlength(text, font=font) > 1000 and size > 20:
            size -= 2
            font = ImageFont.truetype(FONT, size, index=1)
        d.text((540, top + i * lh + lh // 2), text, font=font, fill="black", anchor="mm")
    img.save(path)


def dates():
    v = (os.environ.get("MEAL_DATE") or "").strip()
    if "-" in v:
        a, b = v.split("-")
        d = dt.datetime.strptime(a, "%Y%m%d").date()
        e = dt.datetime.strptime(b, "%Y%m%d").date()
        out = []
        while d <= e:
            if d.weekday() < 5:
                out.append(d.strftime("%Y%m%d"))
            d += dt.timedelta(days=1)
        return out
    return [v or dt.datetime.now(KST).strftime("%Y%m%d")]


def main():
    for ymd in dates():
        one(ymd)


def one(ymd):
    iso = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}"
    os.makedirs("images", exist_ok=True)
    ddish = fetch_lunch(ymd)
    status = {"date": iso, "source": "https://open.neis.go.kr"}
    if ddish is None:
        status.update(status="no_lunch", menu=[])
    else:
        menu = clean(ddish)
        render(["[중식]"] + menu, f"images/{iso}.png")
        status.update(status="ok", menu=menu)
    with open(f"images/{iso}.json", "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    print(json.dumps(status, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
