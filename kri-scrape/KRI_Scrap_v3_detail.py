# %%
### Packages ###
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
import time
from random import uniform
import re
# import regex
import pickle
from tqdm.notebook import tqdm
#from tqdm import tqdm
import numpy as np
import requests
import shutil
from natsort import natsorted
import glob
import os
import sys
import itertools
sys.setrecursionlimit(10000000)

from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains

# %%
### 크롬 열기 ###
chrome_options = webdriver.ChromeOptions()
# print('TouchVPN y?')
# mode = input()
# if mode == 'CLI':
    # chrome_options.add_argument('--headless') #내부 창을 띄울 수 없으므로 설정
# if mode =='y':
#     chrome_options.add_extension('./touchvpn.crx') # openvpn으로 해결
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('window-size=1920x1080')
chrome_options.add_argument('--start-maximized')
chrome_options.add_argument("disable-gpu")
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument("--log-level=3") # 에러만 로그로 남기기
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472 Safari/537.36")

# if os.name=='posix':
#     download_path = r"./raw_data"
# if os.name=='nt':
#     download_path = "G:\\내 드라이브\\박사논문\\KCI_Scraping\\raw_data"

chrome_options.add_experimental_option("prefs", {
#   "download.default_directory": download_path,
  "download.prompt_for_download": False,
  "download.directory_upgrade": True,
  "safebrowsing.enabled": True
})

def enable_download_headless(browser,download_dir):
    browser.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
    params = {'cmd':'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_dir}}
    browser.execute("send_command", params)

# 프록시 설정
# PROXY = "socks5://127.0.0.1:9050" # tor
# chrome_options.add_argument(f'--proxy-server={PROXY}') # tor

# PROXY = "110.77.180.162:8080"
# DesiredCapabilities.CHROME['proxy'] = {
#     "httpProxy": PROXY,
#     "ftpProxy": PROXY,
#     "sslProxy": PROXY,
#     "proxyType": "MANUAL"
# }
# DesiredCapabilities.CHROME['acceptSslCerts'] = True

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=chrome_options)
# driver = webdriver.Chrome(ChromeDriverManager().install())

# enable_download_headless(driver, download_path) #다운로드 경로 설정 및 파일이름 자동 부여

#%% 연구자 번호 로드
# kri_df = pd.read_pickle('./Social_author_KRI.pkl')
kri_df = pd.read_pickle('./Human_author_KRI.pkl')
kri_list = sorted(list(kri_df['KRI_ID'].unique()))
kri_list = list(set(kri_list) - set(df['kri_num'].unique()))

#%% KRI 접속 세팅
driver.get('https://www.kri.go.kr/kri2')

driver.find_element(By.XPATH,"//*[@class='site-btn btn-point ico-user show-login']").click()
# driver.find_element(By.XPATH,'//*[@id="site-header"]/div/ul/li[4]/button').click()

driver.find_element(By.ID,'uid').send_keys('kimkunta') #id
driver.find_element(By.ID,'upw').send_keys('R$Fk@dj23B~6p72') #pw
driver.find_element(By.ID,'upw').send_keys(Keys.ENTER)

time.sleep(7)
try:
    driver.find_element(By.ID,'next_pwd').click()
except:
    print('pass')

# 검색
driver.find_element(By.XPATH,"//*[@class='dep1-item ico-search']").click()
# 성명 검색
driver.find_element(By.XPATH,"//*[@class='MNU_1103']").click()
# 사이드창 닫기
# driver.find_element(By.XPATH,"//*[@class='site-btn close-sidebar ico-close']").click()

# 검색 iframe 활성화
iframes = driver.find_elements(By.TAG_NAME,'iframe')
driver.switch_to.frame(iframes[0])

# 논문 실적 사이트 예시
driver.get('https://www.kri.go.kr/kri/rp/rschachv/PG-RP-108-01jl.jsp?txtRschrRegNo=11507194')

# %%
# https://pgh268400.tistory.com/371
# def hand_scroll(amount):
#     try:
#         scroll = driver.find_element(By.CLASS_NAME,'GMVScroll')
 
#         # ActionChains생성
#         action = ActionChains(driver)
 
#         # 클릭하고 잡기
#         action.click_and_hold(scroll).perform()
 
#         # 마우스 내리기
#         action.move_by_offset(0, amount).perform()
 
#         # 마우스 놓아주기
#         action.release(scroll).perform()
#     except:  # 끝 도달시
#         return False

#%% 수집 리스트 자르기 (1부터)
# print('type pnum: ')
# pnum = int(input())
# kris = kri_list[5000*(pnum-1):5000*pnum]
# row_list = []

# %% KRI 수집 시작
for pnum in range(1,2):
    row_list = []
    kris = kri_list[5000*(pnum-1):5000*pnum]
    print(f'KRI ~ {pnum} 수집 시작')
    for idx, kri in enumerate(tqdm(kris)): #idx로 중간에 멈춘 부분 알수 있음
        driver.get(f'https://www.kri.go.kr/kri/rp/rschachv/PG-RP-108-01jl.jsp?txtRschrRegNo={kri}')
        time.sleep(uniform(0.7,0.9))

        # num_paper = driver.find_element(By.XPATH,'//*[@id="sheet1-table"]/tbody/tr[1]/td/div/table/tbody/tr/td[2]/div').text
        # num_paper = int(re.search('\d+',num_paper).group())
        
        # if num_paper==0:
        #     continue

        # if num_paper>20:
        # 목록 펼치기
        driver.find_element(By.XPATH,'//*[@id="open"]').click()
        time.sleep(uniform(0.4, 0.5))

        # if num_paper>40:
        #     print('scroll')
        #     hand_scroll(2000)

        # page_source 수집
        req = driver.page_source
        soup = BeautifulSoup(req,'lxml')
        tbody = soup.find(class_='GMBodyMid')
    
        # 번호
        num = [t.text for t in soup.find_all(class_='GMClassReadOnly GMWrap1 GMAlignCenter GMSeq GMCell IBSheetFont0 HideCol0C1')]

        # 게재년월
        # date = [t.text for t in soup.find_all(class_='GMClassReadOnly GMWrap1 GMAlignCenter GMText GMCell IBSheetFont0 HideCol0C4')]
        
        titles = tbody.find_all(class_='GMClassReadOnly GMWrap1 GMAlignLeft GMText GMCell IBSheetFont0 HideCol0C6')
        # 제목
        title =[t.text for t in titles]
        # 학술지
        journal = [t.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.text for t in titles]
        # 발행처명
        pub = [t.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.text for t in titles]
        # 학술지구분
        jour_cate = [t.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.text for t in titles]
        # 전체저자수
        num_author = [t.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.text for t in titles]

        # res dict
        res = {'kri_num':kri, 'num':num, 'title':title, 'journal':journal, \
        'pub':pub, 'jour_cate':jour_cate, 'num_author':num_author}

        ## merge row
        row_list.append(res)

    df = pd.DataFrame(row_list)
    # df.to_pickle(f'./KRI/Social/KRI_social_{pnum}_.pkl')
    df.to_pickle(f'./KRI/Human/KRI_human_{pnum}_.pkl')

# %%
# df.explode(list(df.columns)[1:],ignore_index=True)

# %% 저장
# df.to_pickle(f'./KRI/Social/KRI_social_{pnum}.pkl')

# %% 수집한 리스트 하나로 합치기(중복제거)
file_list = glob.glob('./KRI/*/*.pkl')
df = pd.DataFrame()
for file in tqdm(file_list):
    res = pd.read_pickle(file)
    df = pd.concat([df,res],ignore_index=True)

# %%
# KRI 번호 중복삭제
df = df.drop_duplicates(subset='kri_num').reset_index(drop=True)
# 논문 없는 연구자 삭제
df = df[df['title'].str.len()!=0].reset_index(drop=True)

# %%
df_explode = df.explode(['title','journal','pub','jour_cate','num_author'],ignore_index=True)
df_explode = df_explode.drop(columns='num')

# %%
# df_explode.to_pickle('./KRI/220502_KRI_Social_Human.pkl')
df_explode = pd.read_pickle('./KRI/220502_KRI_Social_Human.pkl')
df_explode
# %%
df_explode['jour_cate'].value_counts()
# %%
df_explode.loc[df_explode['jour_cate']=='국제전문학술지(SCI급)','kri_num'].value_counts() #21317명
# %%
len(df_explode.loc[df_explode['jour_cate']=='국제전문학술지(SCI급)','kri_num'].unique())
# %%
driver.get('https://www.kri.go.kr/kri/rp/rschachv/PG-RP-102-02jr.jsp?txtRschrRegNo=11092504')
# %%
