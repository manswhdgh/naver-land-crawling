import requests
import json
import pandas as pd
import urllib3
import os
import time
from datetime import datetime
from geopy.geocoders import Nominatim
# from fake_useragent import UserAgent
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem

# Trad and Rlet type dictionaries
tradTpCd = [{'tagCd': 'A1', 'uiTagNm': '매매'}, {'tagCd': 'B1', 'uiTagNm': '전세'}, {'tagCd': 'B2', 'uiTagNm': '월세'}, {'tagCd': 'B3', 'uiTagNm': '단기임대'}]
rletTpCd = [{'tagCd': 'APT', 'uiTagNm': '아파트'}, {'tagCd': 'OPST', 'uiTagNm': '오피스텔'}, {'tagCd': 'VL', 'uiTagNm': '빌라'}, {'tagCd': 'ABYG', 'uiTagNm': '아파트분양권'}, {'tagCd': 'OBYG', 'uiTagNm': '오피스텔분양권'}, {'tagCd': 'JGC', 'uiTagNm': '재건축'}, {'tagCd': 'JWJT', 'uiTagNm': '전원주택'}, {'tagCd': 'DDDGG', 'uiTagNm': '단독/다가구'}, {'tagCd': 'SGJT', 'uiTagNm': '상가주택'}, {'tagCd': 'HOJT', 'uiTagNm': '한옥주택'}, {'tagCd': 'JGB', 'uiTagNm': '재개발'}, {'tagCd': 'OR', 'uiTagNm': '원룸'}, {'tagCd': 'GSW', 'uiTagNm': '고시원'}, {'tagCd': 'SG', 'uiTagNm': '상가'}, {'tagCd': 'SMS', 'uiTagNm': '사무실'}, {'tagCd': 'GJCG', 'uiTagNm': '공장/창고'}, {'tagCd': 'GM', 'uiTagNm': '건물'}, {'tagCd': 'TJ', 'uiTagNm': '토지'}, {'tagCd': 'APTHGJ', 'uiTagNm': '지식산업센터'}]

# Function to get data from Naver
def get_all_data(trad_tag_cd, rlet_tag_cd, minPrice, maxPrice, minPyeong, maxPyeong):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    all_data = []
    page = 1
    has_more_data = True
    max_retries = 5
    backoff_factor = 1

    while has_more_data:
        url = f"https://m.land.naver.com/cluster/ajax/articleList?rletTpCd={rlet_tag_cd}&tradTpCd={trad_tag_cd}&z=12&lat=37.5443251&lon=126.9867247&btm=37.4228186&lft=126.7970389&top=37.6656339&rgt=127.1764105&spcMin={minPyeong}&spcMax={maxPyeong}&dprcMin={minPrice}&dprcMax={maxPrice}&tag=PARKINGYN&cortarNo=1100000000&page={page}"
        # ua = UserAgent(verify_ssl=False, use_cache_server=True)
        # user_agent = ua.random  
        
        # 소프트웨어 및 운영체제 설정 (선택 사항)
        software_names = [SoftwareName.CHROME.value]
        operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value]

        # UserAgent 객체 생성
        user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)

        # 무작위 User-Agent 가져오기
        user_agent = user_agent_rotator.get_random_user_agent()

        headers = {
            # "Accept": "application/json, text/javascript, */*; q=0.01",
            # "Accept-Encoding": "gzip, deflate, br",
            # "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            # "Host": "m.land.naver.com",
            # "Referer": "https://m.land.naver.com/",
            # "Sec-Fetch-Dest": "empty",
            # "Sec-Fetch-Mode": "cors",
            # "Sec-Fetch-Site": "same-origin",
            # "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": user_agent
        }

        for retry in range(max_retries):
            try:
                response = requests.get(url, headers=headers)
                # response.encoding = "utf-8-sig"
                
                if response.status_code == 200:
                    data = json.loads(response.text)
                    article_list = data.get("body", [])
                    all_data.extend(article_list)
                    has_more_data = data.get("more", False)
                    page += 1
                    break
                else:
                    print(f"Error: Received status code {response.status_code}")
                    raise requests.RequestException(f"Status code: {response.status_code}")
            
            except (requests.RequestException, json.JSONDecodeError) as e:
                if retry < max_retries - 1:
                    backoff_time = backoff_factor * (2 ** retry)
                    print(f"Request failed (attempt {retry+1}/{max_retries}). Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                else:
                    print("Max retries reached. Exiting...")
                    return all_data

    return all_data

# Convert sqm to pyung
def sqm_to_pyung(sqm):
    return int(sqm / 3.305785)

# Save to Excel
def save_to_excel(data_list, input_area):
    df = pd.DataFrame(data_list)
    today_date = datetime.now().strftime("%Y%m%d")
    file_name = f"[{today_date}] 네이버부동산필터링리스트.xlsx"
    if os.path.exists(file_name):
        os.remove(file_name)        
    seoul_data = df[df["실제주소"].str.contains(input_area)]
    seoul_data.to_excel(file_name, index=False)
    print(f"Data saved to {file_name}")

# GUI Application
class RealEstateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Naver Real Estate Filter")

        # Trad type combobox
        self.trad_label = tk.Label(root, text="매매유형")
        self.trad_label.grid(row=0, column=0, padx=10, pady=10)
        self.trad_type = ttk.Combobox(root, values=[item['uiTagNm'] for item in tradTpCd])
        self.trad_type.grid(row=0, column=1, padx=10, pady=10)

        # Rlet type combobox
        self.rlet_label = tk.Label(root, text="주택유형")
        self.rlet_label.grid(row=1, column=0, padx=10, pady=10)
        self.rlet_type = ttk.Combobox(root, values=[item['uiTagNm'] for item in rletTpCd])
        self.rlet_type.grid(row=1, column=1, padx=10, pady=10)

        # Input area
        self.area_label = tk.Label(root, text="검색 지역")
        self.area_label.grid(row=2, column=0, padx=10, pady=10)
        self.input_area = tk.Entry(root)
        self.input_area.grid(row=2, column=1, padx=10, pady=10)

        # Price range
        self.min_price_label = tk.Label(root, text="최소 가격 (억)")
        self.min_price_label.grid(row=3, column=0, padx=10, pady=10)
        self.min_price = tk.Entry(root)
        self.min_price.grid(row=3, column=1, padx=10, pady=10)

        self.max_price_label = tk.Label(root, text="최대 가격 (억)")
        self.max_price_label.grid(row=4, column=0, padx=10, pady=10)
        self.max_price = tk.Entry(root)
        self.max_price.grid(row=4, column=1, padx=10, pady=10)

        # Pyeong range
        self.min_pyeong_label = tk.Label(root, text="최소 평수")
        self.min_pyeong_label.grid(row=5, column=0, padx=10, pady=10)
        self.min_pyeong = tk.Entry(root)
        self.min_pyeong.grid(row=5, column=1, padx=10, pady=10)

        self.max_pyeong_label = tk.Label(root, text="최대 평수")
        self.max_pyeong_label.grid(row=6, column=0, padx=10, pady=10)
        self.max_pyeong = tk.Entry(root)
        self.max_pyeong.grid(row=6, column=1, padx=10, pady=10)

        # Search button
        self.search_button = tk.Button(root, text="검색 시작", command=self.start_search)
        self.search_button.grid(row=7, columnspan=2, pady=20)

    def start_search(self):
        trad_tag_cd = find_tag_cd_by_ui_tag_nm(self.trad_type.get(), tradTpCd)
        rlet_tag_cd = find_tag_cd_by_ui_tag_nm(self.rlet_type.get(), rletTpCd)
        input_area = self.input_area.get()
        min_price = int(self.min_price.get()) * 10000
        max_price = int(self.max_price.get()) * 10000
        min_pyeong = int(float(self.min_pyeong.get()) * 3.3)
        max_pyeong = int(float(self.max_pyeong.get()) * 3.3)

        if not trad_tag_cd or not rlet_tag_cd:
            messagebox.showerror("Error", "매매유형 또는 주택유형을 선택해주세요.")
            return

        print("입력된 매매유형 tagCd 값:", trad_tag_cd)
        print("입력된 주택유형 tagCd 값:", rlet_tag_cd)

        article_list = get_all_data(trad_tag_cd, rlet_tag_cd, min_price, max_price, min_pyeong, max_pyeong)
        if len(article_list) > 0:
            save_to_excel(article_list, input_area)
        else:
            messagebox.showinfo("정보", "검색된 데이터가 없습니다.")

# Utility functions
def find_tag_cd_by_ui_tag_nm(ui_tag_nm, tag_list):
    for item in tag_list:
        if item['uiTagNm'] == ui_tag_nm:
            return item['tagCd']
    return None

if __name__ == "__main__":
    root = tk.Tk()
    app = RealEstateApp(root)
    root.mainloop()
