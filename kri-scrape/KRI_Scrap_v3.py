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
# from tqdm.notebook import tqdm
from tqdm import tqdm
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
from webdriver_manager.chrome import ChromeDriverManager

# %%
### 크롬 열기 ###
chrome_options = webdriver.ChromeOptions()
# print('TouchVPN y?')
# mode = input()
# if mode == 'CLI':
#     chrome_options.add_argument('--headless') #내부 창을 띄울 수 없으므로 설정
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

driver = webdriver.Chrome(ChromeDriverManager().install(),options=chrome_options)
# driver = webdriver.Chrome(ChromeDriverManager().install())

# enable_download_headless(driver, download_path) #다운로드 경로 설정 및 파일이름 자동 부여

#%% 연구자 번호 로드
kri_dict_files = natsorted(glob.glob('./kri_num/kri_dict/kri_dict_*.pkl'))
# kri_dict_files = natsorted(glob.glob('./ref_kri_num/kri_dict/kri_dict_*.pkl'))
kri_dict = {}
for file in tqdm(kri_dict_files):
    with open(file,'rb') as f:
        res = pickle.load(f)
        kri_dict.update(res)

kri_df = pd.DataFrame.from_dict(kri_dict,orient='index',columns=['kri_num'])
del kri_dict
kri_df['crtId'] = kri_df.index
kri_df = kri_df.reset_index(drop=True)

kri_list = kri_df['kri_num'].tolist()
kri_list = [x for x in kri_list if x]
del kri_df
# 중복 삭제
kri_list = sorted(list(set(kri_list)))

#%%
# duplicatd_kri = kri_df[kri_df['kri_num'].map(lambda x:x!=None)]
# duplicatd_kri = duplicatd_kri[kri_df['kri_num'].duplicated(keep=False)].sort_values('kri_num')

#%% KRI 접속 세팅
driver.get('https://www.kri.go.kr/kri2')

driver.find_element(By.XPATH,"//*[@class='site-btn btn-point ico-user show-login']").click()
# driver.find_element(By.XPATH,'//*[@id="site-header"]/div/ul/li[4]/button').click()

driver.find_element(By.ID,'uid').send_keys('kimkunta')
driver.find_element(By.ID,'upw').send_keys('') #비밀번호
driver.find_element(By.ID,'upw').send_keys(Keys.ENTER)

time.sleep(7)
driver.find_element(By.ID,'next_pwd').click()

# 검색
driver.find_element(By.XPATH,"//*[@class='dep1-item ico-search']").click()
# 성명 검색
driver.find_element(By.XPATH,"//*[@class='MNU_1103']").click()
# 사이드창 닫기
# driver.find_element(By.XPATH,"//*[@class='site-btn close-sidebar ico-close']").click()

# 검색 iframe 활성화
iframes = driver.find_elements(By.TAG_NAME,'iframe')
driver.switch_to.frame(iframes[0])

#%% 수집 리스트 자르기
print('type pnum: ')
pnum = int(input())
urls = kri_list[5000*(pnum-1):5000*pnum]

#%%
urls = ['10038092','10117685','10141094','10145525','10173924','11502333','11918138',
 '11927712','12517917','12799393']

# %% KRI 수집 시작
row_list = []
print(f'KRI ~ {pnum} 수집 시작')

for i, kri in enumerate(tqdm(urls)):
    # time.sleep(0.3)
    try:
        driver.find_element(By.XPATH,'//*[@id="txtSearchRschrRegNo"]').clear()
        driver.find_element(By.XPATH,'//*[@id="txtSearchRschrRegNo"]').send_keys(f'{kri}')
        time.sleep(0.2)
        # driver.find_element(By.XPATH,'//*[@id="txtSearchRschrRegNo"]').send_keys(Keys.ENTER)

        driver.execute_script("doAction('SEARCH');")
        # wait = WebDriverWait(driver,2)
        # element = wait.until(EC.presence_of_element_located((By.CLASS_NAME,'GMSection')))
        time.sleep(uniform(4,5))

        req = driver.page_source
        soup = BeautifulSoup(req,'html.parser')
    except UnexpectedAlertPresentException:
        print('재시도')
        driver.find_element(By.XPATH,'//*[@id="txtSearchRschrRegNo"]').clear()
        driver.find_element(By.XPATH,'//*[@id="txtSearchRschrRegNo"]').send_keys(f'{kri}')
        time.sleep(0.5)

        driver.execute_script("doAction('SEARCH');")
        # wait = WebDriverWait(driver,2)
        # element = wait.until(EC.presence_of_element_located((By.CLASS_NAME,'GMSection')))
        time.sleep(uniform(2.5,3))

        req = driver.page_source
        soup = BeautifulSoup(req,'html.parser')

    # 생년
    if soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignCenter GMText GMCell IBSheetFont0 HideCol0C3'):
        birth = soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignCenter GMText GMCell IBSheetFont0 HideCol0C3').string
    else:
        birth = None

    # 성명
    if soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignLeft GMText GMCell IBSheetFont0 HideCol0C6'):
        name = soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignLeft GMText GMCell IBSheetFont0 HideCol0C6').string
    else:
        name = None

    # 성별
    if soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignCenter GMText GMCell IBSheetFont0 HideCol0C7'):
        gender = soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignCenter GMText GMCell IBSheetFont0 HideCol0C7').string
    else:
        gender = None

    # 소속대학/기관
    if soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignLeft GMText GMCell IBSheetFont0 HideCol0C8'):
        univ = soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignLeft GMText GMCell IBSheetFont0 HideCol0C8').string
    else:
        univ = None
    
    # 직급
    if soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignLeft GMText GMCell IBSheetFont0 HideCol0C10'):
        job = soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignLeft GMText GMCell IBSheetFont0 HideCol0C10').string
    else:
        job = None

    # 전공분야
    if soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignLeft GMText GMCell IBSheetFont0 HideCol0C11'):
        major = soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignLeft GMText GMCell IBSheetFont0 HideCol0C11').string
    else:
        major = None

    # 출신학교
    if soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignLeft GMText GMCell IBSheetFont0 HideCol0C12'):
        grad = soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignLeft GMText GMCell IBSheetFont0 HideCol0C12').string
    else:
        grad = None

    # 취득학위
    if soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignCenter GMText GMCell IBSheetFont0 HideCol0C13'):
        diploma = soup.find('td',class_='GMClassReadOnly GMWrap0 GMAlignCenter GMText GMCell IBSheetFont0 HideCol0C13').string
    else:
        diploma = None

    # res dict
    res = {'kri_num':kri, 'birth' : birth, 'name':name, 'gender':gender, 'univ':univ, \
        'job':job, 'major':major, 'grad':grad, 'diploma':diploma}

    ## merge row
    row_list.append(res)

df = pd.DataFrame(row_list)

# df.to_pickle(f'./kri_num/kri_table_{pnum}.pkl')
df.to_parquet(f'./ref_kri_num/kri_table_{pnum}.parquet.gzip',compression='gzip')

# del row_list, df

#%% KRI 수집결과 확인
# kri_table_files = natsorted(glob.glob('./kri_num/*.parquet.gzip'))
kri_table_files = natsorted(glob.glob('./ref_kri_num/*.parquet.gzip'))
df_kri = pd.DataFrame()
for file in tqdm(kri_table_files):
    res = pd.read_parquet(file)
    df_kri = df_kri.append(res,ignore_index=True)

#%% KRI 누락 및 중복 확인
# KRI 누락 (수집대상 이었는데 table에 없음)
missing_list = list(set(kri_list) - set(df_kri['kri_num'].tolist()))

# kri_num 중복 확인
df_kri[df_kri.duplicated(subset=['kri_num'])]

# kri_num 이외 중복 확인
duplicated_list = df_kri[df_kri.drop(columns=['kri_num']).duplicated(keep=False)]['kri_num'].tolist()

# 수집할 kri_num 확보
kri_list_add = missing_list + duplicated_list

# urls에 부여
pnum = 'add'
urls = kri_list_add

#%% KRI 누락 및 중복 확인 2
# 추가 수집본 중복 확인
df_kri[df_kri.duplicated(subset=['kri_num'],keep=False)].sort_values('kri_num')
# 중복 제거 (last를 살려서 추가 모집본으로 대체)
df_kri_drop = df_kri.drop_duplicates(subset=['kri_num'],keep='last')

# last_duplic = df_kri_drop[df_kri_drop.duplicated(subset=df_kri_drop.columns.tolist()[1:],keep=False)].sort_values('kri_num')
# last_duplic[last_duplic['birth'].map(lambda x:x!=None)]

#%% KRI 최종 저장(중복 삭제)
df_kri_drop.to_pickle('./ref_kri_num/ref_kri_table.pkl')