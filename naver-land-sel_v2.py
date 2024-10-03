import time
import json
import uuid
import pandas as pd
import os
from datetime import datetime
from geopy.geocoders import Nominatim
from requests import Request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from tkinter import Tk, Label, Entry, Button, StringVar, ttk, OptionMenu

tradTpCd = [
   {'tagCd': 'A1', 'uiTagNm': '매매'},
    {'tagCd': 'B1', 'uiTagNm': '전세'},
    {'tagCd': 'B2', 'uiTagNm': '월세'},
    {'tagCd': 'B3', 'uiTagNm': '단기임대'}
]

rletTpCd = [
    {'tagCd': 'APT', 'uiTagNm': '아파트'}, 
    {'tagCd': 'OPST', 'uiTagNm': '오피스텔'}, 
    {'tagCd': 'VL', 'uiTagNm': '빌라'},
    {'tagCd': 'ABYG', 'uiTagNm': '아파트분양권'}, 
    {'tagCd': 'OBYG', 'uiTagNm': '오피스텔분양권'}, 
    {'tagCd': 'JGC', 'uiTagNm': '재건축'},
    {'tagCd': 'JWJT', 'uiTagNm': '전원주택'}, 
    {'tagCd': 'DDDGG', 'uiTagNm': '단독/다가구'}, 
    {'tagCd': 'SGJT', 'uiTagNm': '상가주택'},
    {'tagCd': 'HOJT', 'uiTagNm': '한옥주택'}, 
    {'tagCd': 'JGB', 'uiTagNm': '재개발'}, 
    {'tagCd': 'OR', 'uiTagNm': '원룸'},
    {'tagCd': 'GSW', 'uiTagNm': '고시원'}, 
    {'tagCd': 'SG', 'uiTagNm': '상가'}, 
    {'tagCd': 'SMS', 'uiTagNm': '사무실'},
    {'tagCd': 'GJCG', 'uiTagNm': '공장/창고'}, 
    {'tagCd': 'GM', 'uiTagNm': '건물'}, 
    {'tagCd': 'TJ', 'uiTagNm': '토지'},
    {'tagCd': 'APTHGJ', 'uiTagNm': '지식산업센터'}
]

# GUI 관련 함수들
class RealEstateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("네이버 부동산 스크래퍼")
        self.create_widgets()

    def create_widgets(self):
        Label(self.root, text="매매 유형").grid(row=0, column=0)
        self.tradTp = StringVar()
        self.tradTp.set(tradTpCd[0]['uiTagNm'])  # 기본값 설정
        trad_options = [item['uiTagNm'] for item in tradTpCd]
        OptionMenu(self.root, self.tradTp, *trad_options).grid(row=0, column=1)

        Label(self.root, text="주택 유형").grid(row=1, column=0)
        self.rletTp = StringVar()
        self.rletTp.set(rletTpCd[0]['uiTagNm'])  # 기본값 설정
        rlet_options = [item['uiTagNm'] for item in rletTpCd]
        OptionMenu(self.root, self.rletTp, *rlet_options).grid(row=1, column=1)

        Label(self.root, text="검색 지역").grid(row=2, column=0)
        self.input_area = StringVar()
        Entry(self.root, textvariable=self.input_area).grid(row=2, column=1)

        Label(self.root, text="최소 가격 (만원)").grid(row=3, column=0)
        self.minPrice = StringVar()
        Entry(self.root, textvariable=self.minPrice).grid(row=3, column=1)

        Label(self.root, text="최대 가격 (만원)").grid(row=4, column=0)
        self.maxPrice = StringVar()
        Entry(self.root, textvariable=self.maxPrice).grid(row=4, column=1)

        Label(self.root, text="최소 평수").grid(row=5, column=0)
        self.minPyeong = StringVar()
        Entry(self.root, textvariable=self.minPyeong).grid(row=5, column=1)

        Label(self.root, text="최대 평수").grid(row=6, column=0)
        self.maxPyeong = StringVar()
        Entry(self.root, textvariable=self.maxPyeong).grid(row=6, column=1)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress.grid(row=7, columnspan=2)

        Button(self.root, text="시작", command=self.start_scraping).grid(row=8, columnspan=2)

    def start_scraping(self):
        trad_tag_cd = find_tag_cd_by_ui_tag_nm(self.tradTp.get(), tradTpCd)
        rlet_tag_cd = find_tag_cd_by_ui_tag_nm(self.rletTp.get(), rletTpCd)
        input_area = self.input_area.get()
        minPrice = int(self.minPrice.get())
        maxPrice = int(self.maxPrice.get())
        minPyeong = int(float(self.minPyeong.get()) * 3.3)
        maxPyeong = int(float(self.maxPyeong.get()) * 3.3)
        
        all_data = get_all_data(trad_tag_cd, rlet_tag_cd, minPrice, maxPrice, minPyeong, maxPyeong, self.update_progress)
        save_to_excel(all_data, input_area)

    def update_progress(self, value):
        self.progress['value'] = value
        self.root.update_idletasks()

# 크롬드라이버 설정
def setup_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # 새로운 헤드리스 모드를 사용
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")  # GPU 렌더링 비활성화
    chrome_options.add_argument("--window-size=1920x1080")  # 윈도우 크기 지정
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--remote-debugging-port=9222")  # 디버깅용 포트 열기
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def get_real_address(latitude, longitude):
    random_uuid = uuid.uuid4()
    geolocator = Nominatim(user_agent=str(random_uuid))
    time.sleep(1)  # 요청 간 1초 대기 추가
    location = geolocator.reverse((latitude, longitude), exactly_one=True)
    if location:
        return location.address
    return ""

# 제곱미터(m^2)를 평수로 변환하는 함수
def sqm_to_pyung(sqm):
    return int(sqm / 3.305785)

def get_all_data(trad_tag_cd, rlet_tag_cd, minPrice, maxPrice, minPyeong, maxPyeong, update_progress_callback):
    driver = setup_chrome_driver()
    all_data = []
    page = 1
    has_more_data = True

    while has_more_data:
        url = f"https://m.land.naver.com/cluster/ajax/articleList?rletTpCd={rlet_tag_cd}&tradTpCd={trad_tag_cd}&z=12&lat=37.5443251&lon=126.9867247&btm=37.4228186&lft=126.7970389&top=37.6656339&rgt=127.1764105&spcMin={minPyeong}&spcMax={maxPyeong}&dprcMin={minPrice}&dprcMax={maxPrice}&tag=PARKINGYN&cortarNo%20=1100000000&page={page}"
        print(url)
        driver.get(url)
        time.sleep(3)  # 페이지 로딩 대기

        response_text = driver.find_element("tag name", 'body').text
        
        if not response_text:
            print(f"Page {page} did not return valid data.")
            break
        
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON on page {page}. Response: {response_text}")
            break
        
        article_list = data.get("body", [])
        all_data.extend(article_list)

        has_more_data = data.get("more", False)
        
        if page == 40:
            has_more_data = False
        
        page += 1

        progress = (page / 10) * 100  # 가정한 페이지 수를 기준으로 프로그레스 설정
        update_progress_callback(progress)

    driver.quit()
    return all_data


def save_to_excel(data_list, input_area):
    parsed_data = []

    for article in data_list:
        parsed_article = {
           "매물번호": article.get("atclNo", ""),
            "매물URL": "https://m.land.naver.com/article/info/" + article.get("atclNo", ""),
            "등록일자": article.get("atclCfmYmd", ""),
            # "주택종류": article.get("realEstateTypeName", ""),
            "건물종류명": article.get("atclNm", ""),
            "매매가격": article.get("hanPrc", ""),
            "동일매물최저가격": article.get("sameAddrMinPrc", ""),
            "동일주소최고가격": article.get("sameAddrMaxPrc", ""),
            "층정보": article.get("flrInfo", ""),
            "매물설명": article.get("atclFetrDesc", ""),
            "대지평수": sqm_to_pyung(float(article.get("spc1", ""))),
            "총평수": sqm_to_pyung(float(article.get("spc2", ""))),
            "대지면적": article.get("spc1", ""),
            "총면적": article.get("spc2", ""),
            # "매물태그": article.get("tagList", ""),
            "실제주소": get_real_address(article.get("lat", "0"), article.get("lng", "0")),
            # "지역번호": article.get("cortarNo", ""),
            # "매물상태코드": article.get("atclStatCd", ""),
            # "거래유형코드": article.get("rletTpCd", ""),
            # "상위거래유형코드": article.get("uprRletTpCd", ""),
            "거래유형명": article.get("rletTpNm", ""),
            # "거래유형상세코드": article.get("tradTpCd", ""),
            "거래유형상세명": article.get("tradTpNm", ""),
            "확인유형코드": article.get("vrfcTpCd", ""),
            "방향정보": article.get("direction", ""),
            # "대표이미지URL": article.get("repImgUrl", ""),
            # "대표이미지유형코드": article.get("repImgTpCd", ""),
            # "대표이미지썸네일": article.get("repImgThumb", ""),
            # "위도": article.get("lat", ""),
            # "경도": article.get("lng", ""),
            "건물명": article.get("bildNm", ""),
            # "분": article.get("minute", ""),
            "동일주소매물수": article.get("sameAddrCnt", ""),
            "동일주소직접매물수": article.get("sameAddrDirectCnt", ""),
            # "동일주소해시": article.get("sameAddrHash", ""),
            # "업소ID": article.get("cpid", ""),
            "업소명": article.get("cpNm", ""),
            "업소매물수": article.get("cpCnt", ""),
            "공인중개사사무소명": article.get("rltrNm", ""),
            # "직거래여부": article.get("directTradYn", ""),
            # "최소중개보수": article.get("minMviFee", ""),
            # "최대중개보수": article.get("maxMviFee", ""),
            # "연립다세대방수": article.get("etRoomCnt", ""),
            # "거래가격한글표기": article.get("tradePriceHan", ""),
            # "거래임대가격": article.get("tradeRentPrice", ""),
            # "거래직접확인여부": article.get("tradeCheckedByOwner", ""),
            # "상세주소여부": article.get("dtlAddrYn", ""),
            # "상세주소": article.get("dtlAddr", "")
        }
        parsed_data.append(parsed_article)

    df = pd.DataFrame(parsed_data)
    today_date = datetime.now().strftime("%Y%m%d")
    file_name = f"[{today_date}] 네이버부동산필터링리스트.xlsx"
    
    if os.path.exists(file_name):
        os.remove(file_name)
    
    seoul_data = df[df["실제주소"].str.contains(input_area)]
    seoul_data.to_excel(file_name, index=False)
    print("Data saved to", file_name)

def find_tag_cd_by_ui_tag_nm(ui_tag_nm, tag_list):
    for item in tag_list:
        if item['uiTagNm'] == ui_tag_nm:
            return item['tagCd']
    return None

if __name__ == '__main__':
    root = Tk()
    app = RealEstateApp(root)
    root.mainloop()
