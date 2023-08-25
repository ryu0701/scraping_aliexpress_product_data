import re
import yaml
import time
import random
import csv
import json
from tqdm import tqdm
import requests
from requests.exceptions import RequestException, ConnectionError,  HTTPError, RetryError, Timeout
from fake_useragent import UserAgent
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib3.exceptions import MaxRetryError
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchDriverException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import concurrent.futures
import multiprocessing
from constant import Constant
from log import Logger

# カレントディレクトリ
cwd = Path.cwd()

# 設定ファイル読み込み
with open(Path(cwd, 'config', 'config.yml'), encoding=Constant.ENCODE_TYPE_UTF8) as f:
    config = yaml.safe_load(f)

# CSV出力先取得
date_now = datetime.now()
str_yyyymmdd = date_now.strftime('%Y%m%d')
if config['CSV']['path']['output']:
    output_csv_path = config['CSV']['path']['output'] + '\\' + str_yyyymmdd
else:
    output_csv_path = str(Path(cwd, 'csv')) + '\\' + str_yyyymmdd

# max_workers
process_max_workers = config['TASK']['process']['max_workers'] if config['TASK']['process']['max_workers'] else None
thread_max_workers = config['TASK']['thread']['max_workers'] if config['TASK']['thread']['max_workers'] else None

# プロキシ
proxy_ip_list = config['PROXY']['ip_list']
proxy_site_url = config['PROXY']['site_url']

# フリーのプロキシサーバーのリストを取得する


def get_free_proxies(proxy_site_url):
    res = requests.get(proxy_site_url)
    soup = BeautifulSoup(res.text, 'html.parser')
    table = soup.find('table', class_='table table-striped table-bordered')
    proxies = []
    for row in table.tbody.find_all('tr'):
        if row.find_all('td')[6].text == 'yes':
            ip = row.find_all('td')[0].text
            port = row.find_all('td')[1].text
            proxies.append(f'http://{ip}:{port}')
    return proxies


proxy_list = get_free_proxies(proxy_site_url)

# エラーカウンタ
error_count = 0


class CommonFunction:
    '''
    共通関数定義クラス
    '''

    def __init__(self, debug_flg) -> None:
        self.logger = Logger(debug_flg)

    def func_speed(self, func, *args, **kw):
        '''
        関数の処理時間計測
        '''
        start_time = time.time()
        start_time_str = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        self.logger.debug(f'func:{func.__name__}, 処理開始：{start_time_str}')

        result = func(*args, **kw)

        end_time = time.time()
        send_time_str = datetime.now().strftime('%Y/%m/%d %H:%M:%S')

        process_time = end_time-start_time
        self.logger.debug(f'func:{func.__name__}, 処理終了：{send_time_str}, 処理時間：{process_time} [sec]')

        return result

    def func_progress(self, func, iterations, *args, **kw):
        '''
        関数の進行度をプログレスバーで表示
        '''
        start_time = time.time()
        start_time_str = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        self.logger.debug(f'func:{func.__name__}, 処理開始：{start_time_str}')

        # ここでプログレスバーを表示
        pbar = tqdm(total=iterations)
        for _ in range(iterations):
            # 処理
            result = func(*args, **kw)
            # プログレスバーの更新
            pbar.update(1)
        pbar.close()

        end_time = time.time()
        end_time_str = datetime.now().strftime('%Y/%m/%d %H:%M:%S')

        process_time = end_time-start_time
        self.logger.debug(f'func:{func.__name__}, 処理終了：{end_time_str}, 処理時間：{process_time} [sec]')

        return result


class AppFunction:
    '''
    関数定義クラス
    '''

    def __init__(self, debug_flg=False) -> None:
        # ディレクトリ
        self.cwd = Path.cwd()

        # インスタンス化
        self.debug_flg = debug_flg
        self.logger = Logger(debug_flg)
        self.pool_func = PoolFucntion(debug_flg)

    def get_search_top_result_datas(self, search_texts: list) -> list:
        '''
        機能:
            seleniumにてキーワード検索結果の情報取得
        Args:
            serch_text(list): 検索キーワードリスト
        Rturns:
            store_cds(list): ストアーコード[store_cd]
        '''

        def get_store_cd(driver):
            '''
            selenium操作中コールバック関数
            '''
            continue_flg = True
            # html取得・解析
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'lxml')

            # 商品情報取得
            products = soup.find_all(class_='manhattan--container--1lP57Ag cards--gallery--2o6yJVt search-card-item')

            # 次へボタン
            btn_next = driver.find_elements(By.CLASS_NAME, 'next-next')

            # 次へボタンが押せない場合はcontinue_flgをOFF
            if len(btn_next) > 0:
                btn_next_class_name = driver.find_element(By.CLASS_NAME, 'next-next').get_attribute('class')

                if 'pagination--notAllowed' in btn_next_class_name:
                    continue_flg = False
                else:
                    driver.execute_script('arguments[0].click();', btn_next[0])
                    continue_flg = True
            else:
                continue_flg = False

            # ストアコード抽出
            store_cds = []
            for product in products:
                store_link = product.find(
                    'a', class_=re.compile('cards--storeLink'))
                regexp = r'(?<=store/).*?\d(?=\D|$)'
                store_cd = int(re.search(regexp, store_link['href']).group(0)) if store_link else None
                store_cds.append(store_cd)

            time.sleep(1.5)

            return store_cds, continue_flg

        def get_product_data_with_driver(driver_path, search_text, debug_flg):
            '''
            selenium操作
            '''
            # selenium起動
            options = Options()
            options.add_argument('--log-level=3')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            options.add_argument('--proxy-server=%s' % random.choice(proxy_list))
            if not debug_flg:
                options.add_argument('--headless')

            driver = webdriver.Chrome(service=Service(executable_path=driver_path), options=options)

            # URL生成
            base_url = f'https://ja.aliexpress.com/w/wholesale-{search_text}.html'
            params = {
                'SearchText': search_text,
                'catId': '0',
                'g': 'y',
                # 'initiative_id': 'SB_20230818230341',
                # 'initiative_id': f'SB_{str_yyyymmdd}',
                'isFavorite': 'y',
                'isFreeShip': 'y',
                'page': 1,
                # 'spm': 'a2g0o.home.1000002.0',
                'trafficChannel': 'main',
            }
            query = urlencode(params)
            url = base_url + '?' + query

            # 検索トップ表示
            driver.get(url)
            driver.refresh()    # ヒットしない場合があるので１回更新してからスクレイピング開始
            time.sleep(5)

            # 最初だけページの下部までスクロール
            doc_height = driver.execute_script(
                "return document.body.scrollHeight")
            win_height = driver.execute_script("return window.innerHeight")
            num_pages = int(doc_height / win_height)
            for page in range(1, num_pages+1):
                driver.execute_script("window.scrollTo(0, arguments[0]);", win_height * (page))
                # print(f'scrolling to=>{win_height * (page)}')
                time.sleep(1)

            # 返り値
            store_cd_list = []

            # 最終ページまでループ
            while True:
                store_cds, continue_flg = get_store_cd(driver)
                store_cd_list.extend(store_cds)
                if not continue_flg:
                    break

            # selenium終了
            driver.close()
            driver.quit()

            time.sleep(1)

            return store_cd_list

        # 並列実行するexecutorを用意する。
        store_cd_list = []

        output_store_csv = config['CSV']['output']['store']
        with open(Path(output_csv_path, output_store_csv), 'w', encoding=Constant.ENCODE_TYPE_SJIS, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(Constant.HEADER_STORE_CSV)

        # selleniumバージョン更新
        driver_path = ChromeDriverManager().install()

        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_max_workers) as executor:   # max_workers で調整可能
            futures = [executor.submit(get_product_data_with_driver, driver_path, search_text, self.debug_flg) for search_text in search_texts]

            pbar = tqdm(total=len(futures))
            for future in concurrent.futures.as_completed(futures):
                # 重複削除
                if not any(element in store_cd_list for element in future.result()):
                    # リスト追加
                    store_cd_list += future.result()
                    # csv追記
                    with open(Path(output_csv_path, output_store_csv), 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerows([[str(element)] for element in future.result()])
                # プログレスバーの更新
                pbar.update()
            pbar.close()

        self.logger.info('-----------ストアコード取得完了-----------')

        return store_cd_list
        # return {key: value.result() for key, value in future_list.items()}

    def get_ordered_item_datas(self, store_cds: list):
        '''
        機能:
            ストアコードからそのストア全商品URLを取得する（注文がついていないものは除く）
        Args:
            store_cds(list): ストアコードリスト [store_cd, ...]
        Returns:
            result(list): [[商品URL, ...], [商品URL, ...], ...] ※ストアコード単位で分かれる
        '''
        # 出力ファイル初期化
        output_item_urls_csv = config['CSV']['output']['item_urls']
        with open(Path(output_csv_path, output_item_urls_csv), 'w', encoding=Constant.ENCODE_TYPE_SJIS, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(Constant.HEADER_ITEM_URLS_CSV)

        # 商品URLリスト取得
        return self.pool_func.execute_process_in_store_cd(store_cds)

    def get_item_delivery_datas(self, urls: list) -> dict:
        '''
        機能:
            商品URLから商品ページ配送情報を取得
        Args:
            urls(list): 商品ページURLリスト [url, ...]
        Returns:
            delivery_data_dict(dict): 配送情報 {商品URL: 配送情報}
        '''
        # 出力ファイル初期化
        output_item_csv = config['CSV']['output']['item']
        with open(Path(output_csv_path, output_item_csv), 'w', encoding=Constant.ENCODE_TYPE_SJIS, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(Constant.HEADER_ITEM_CSV)

        # 配送情報を取得
        return self.pool_func.execute_get_thread_in_list(self.get_delivery_datas, urls)

    @classmethod
    def get_delivery_datas(cls, url: str, driver_path,  params: dict = None, retries=2, timeout=10) -> list:
        '''
        コールバック関数（商品の配達情報取得）
        '''
        global error_count

        if error_count > 10:
            print(f'アクセスブロックを受けているため30秒間処理を停止します')
            time.sleep(30)
            print('処理再開')

        def authorization(driver_path, url):
            try:
                global error_count
                script = None
                # 画面表示してみる
                # driver_path = ChromeDriverManager().install()
                options = Options()
                options.add_argument('--log-level=3')
                options.add_experimental_option('excludeSwitches', ['enable-logging'])
                if not config['FLAG']['debug']:
                    options.add_argument('--headless')
                driver = webdriver.Chrome(service=Service(executable_path=driver_path), options=options)
                driver.set_page_load_timeout(60)

                driver.get(url)
                driver.implicitly_wait(1)

                slider = driver.find_element(By.ID, 'nc_1_n1z')

                action = ActionChains(driver)
                action.click_and_hold(slider).move_by_offset(300, 0).release().perform()  # x方向に100ピクセル動かす

                time.sleep(5)
                driver.close()
                driver.quit()

                html_content = driver.page_source
                soup = BeautifulSoup(html_content, 'lxml')
                script = soup.find('script', text=re.compile('window.runParams', re.DOTALL))

            except NoSuchDriverException:
                print("lost selenium path")
                driver_path = ChromeDriverManager().install()
                error_count = + 1
                time.sleep(1)
                return False
            except PermissionError as e:
                print("PermissionError: ファイルアクセス権限の問題が発生しました。")
                error_count = + 1
                time.sleep(1)
                return False
            except NoSuchElementException:
                # print("get by selenium")
                error_count = + 1
                time.sleep(1)
            except MaxRetryError as e:
                # TODO:エラーーハンドルをもっとしっかりしたい
                print("MaxRetryError: HTTP接続のリトライ回数が上限に達しました。")
                error_count = + 1
                time.sleep(1)
            except Exception as e:
                # その他の例外が発生した場合の処理
                print("その他の例外が発生しました:", str(e))
                error_count = + 1
                time.sleep(1)

            return script

        # 検索条件設定
        search_str = '配達予定'

        # うまく行かない場合はretries回まで繰り返す
        for _ in range(retries):
            # GET
            try:
                # ヘッダーにUser-Agentを設定
                headers = {
                    'User-Agent': UserAgent().random,
                }
                # プロキシ設定
                proxies = {
                    'http': random.choice(proxy_list)
                }

                # リクエスト
                res = requests.get(url, params=params, headers=headers, proxies=proxies, timeout=timeout)
                res.raise_for_status()
                time.sleep(2)

                # リクエストに成功したら解析
                soup = BeautifulSoup(res.content, 'lxml')

                # scriptタグ内の情報取得
                script = soup.find('script', text=re.compile('window.runParams', re.DOTALL))

                if script:
                    if search_str in script.string:
                        break
                else:
                    # selenium処理
                    script = authorization(driver_path, url)
                    if script:
                        break

            except (ConnectionError, HTTPError, Timeout, RequestException) as e:
                print("Error:", e)
                print("Retrying...")
                error_count = + 1
                # selenium処理
                # authorization(driver_path, url)

        # 結果格納用リスト
        data_list = []

        if script:
            script_str = script.string
            # ダブルクォートで囲われた文字列を切り分け
            regex = r'(?<=").*?(?=[^\\]")'
            # double_quoted_str = re.findall(regex, script_str)

            seoTitle = re.search(r'(?:"subject":")(.*?)(?:",)', script_str)
            title = seoTitle.group(1) if seoTitle else ''

            # 配達情報の取得
            delivery_data_dict = {}
            deliveryDate = re.finditer(r'(?:"deliveryDate":")(.*?)(?:",)', script_str)
            if deliveryDate:
                delivery_data_dict[url] = [date.group(1) for date in deliveryDate]
            # delivery_data_dict[url] = [_str for _str in double_quoted_str if re.search(r'(配送|配達)', _str)]
            # delivery_data_dict[url] = [_str for _str in double_quoted_str if re.search(r'(?:deliveryDate":")(.*?)(?:",)', _str)]
            # TODO:ループ処理を1回に
            # delivery_data_dict[url] = [str for str in double_quoted_str if search_str in str]

            for val in delivery_data_dict[url]:
                month = re.search(r'(\d|\d{2})月', val)
                day = re.search(r'(\d|\d{2})日', val)

                if month or day:
                    data_list.append(f'配達予定：{month.group(0) + day.group(0)}')

            # 情報取得できてない場合
            if len(data_list) == 0:
                # print(url)
                # selenium処理
                authorization(driver_path, url)
                # time.sleep(15)
            # else:
            #     print(f'商品情報取得：{url}')

        return [url, ' '.join(data_list), title]


class PoolFucntion:
    '''
    並行・並列処理関数クラス
    '''

    def __init__(self, debug_flg=False):
        # ディレクトリ
        self.cwd = Path.cwd()

        # インスタンス化
        self.logger = Logger(debug_flg)
        self.comm_func = CommonFunction(debug_flg)

    def execute_process_in_store_cd(self, store_cds: list) -> list:
        '''
        ストアコードから商品URLを取得（重複削除処理含む）
        '''
        # 結果格納用変数
        item_url_list = []
        # 結果出力CSV
        output_csv_name = config['CSV']['output']['item_urls']

        # マルチプロセスの並列処理数
        max_workers = process_max_workers if process_max_workers else multiprocessing.cpu_count()

        # マルチプロセスで商品URLを取得
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # ストアコード単位で並列処理
            futures = [executor.submit(self.execute_get_thread,  store_cd, self.logger) for store_cd in store_cds]

            # self.logger.debug(f'len(futures): {len(futures)}')

            # プロセスの終了を待つ
            # self.comm_func.func_progress(self.result_append, len(futures), futures, item_url_list)
            self.result_extend(futures, item_url_list, str(Path(output_csv_path, output_csv_name)))

            # print(f'len(future.result()): {len(future.result())}')

        return item_url_list

    @classmethod
    def execute_get_thread(cls, store_cd: int,  logger) -> list:
        '''
        コールバック関数（プロセス）
        '''
        # ページ数取得
        store_top_url = f'https://ja.aliexpress.com/store/{store_cd}/search'
        params = {
            # 'spm': 'a2g0o.store_pc_allProduct.8148362.6.4b401342BfkT2a',
            'origin': 'n',
            'SortType': 'orders_desc'
        }

        # GETリクエスト
        top_html = cls.get_request(store_top_url, params=params, logger=logger)

        # 解析
        soup = BeautifulSoup(top_html, 'lxml')
        count_element = soup.select('#shop-refine .result-info')

        # 検索ヒット件数からページ数取得
        if count_element:
            count_str = count_element[0].string
            regex = r'(\d*\d)(?:件)'
            count_all = int(re.search(regex, count_str).group(1))
            item_count = len(soup.select('.items-list.util-clearfix .item'))
            page_count = (count_all + item_count-1) // item_count
        else:
            page_count = 1

        logger.debug(f'store_cd: {store_cd}, page_count: {page_count}')

        # 全ページのURL
        urls = [f'https://ja.aliexpress.com/store/{store_cd}/search/{page}.html' for page in range(1, page_count+1)]

        item_urls = []

        # マルチスレッドで全ページをスクレイピング
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_max_workers) as executor:
            # GETリクエストを並行処理
            futures = [executor.submit(cls.get_request, url, logger) for url in urls]
            # print(f'thread_count: {len(futures)}')

            # 結果を解析
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    # 注文の表示があるページのみURL取得
                    if ('recent-order' in result):
                        soup = BeautifulSoup(result, 'lxml')
                        items = soup.select('.items-list.util-clearfix .item .detail')
                        item_urls += ['https:' + item.find('a')['href'] for item in items if item.select('.recent-order')]
                        # item_urls += [['https:' + item.find('a')['href']] for item in items if item.select('.recent-order')]

                        # print(f'item_urls[5]: {item_urls[5]}')
                        # print(f'len(item_urls): {len(item_urls)}')

                except Exception as e:
                    cls.logger.error(f'[ThreadError]{e}, store_cd: {store_cd}')

            # logger.debug(f'thread_finish')

        return item_urls

    def execute_get_thread_in_list(self, func, _list: list) -> list:
        '''
        機能:
            マルチスレッドで関数を実行
        Args:
            func: 実行関数
            _list(list): マルチスレッドで実行するリスト
        Returns:
            result_dict(dict): {list_value: result, ...}
        '''
        # 結果格納用変数
        result_list = []
        # 結果出力CSV
        output_csv_name = config['CSV']['output']['item']

        # selenium起動
        # selleniumバージョン更新
        driver_path = ChromeDriverManager().install()

        # マルチスレッドで関数を実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_max_workers) as executor:
            futures = [executor.submit(func, val, driver_path) for val in _list]

            # プロセスの終了を待って辞書へ格納
            # self.comm_func.func_progress(self.result_update, futures, result_dict)
            self.result_append(futures, result_list, str(Path(output_csv_path, output_csv_name)))

        return result_list

    @classmethod
    def get_request(cls, url: str,  logger, params: dict = None, retries=2, timeout=10):
        '''
        コールバック関数（GETリクエスト）
        '''
        for _ in range(retries):
            # 失敗した場合retries回までリクエスト
            try:
                # ヘッダーにUser-Agentを設定
                headers = {
                    'User-Agent': UserAgent().random,
                }
                # プロキシ設定
                proxies = {
                    'http': random.choice(proxy_list)
                }

                # リクエスト
                res = requests.get(url, params=params, headers=headers, proxies=proxies, timeout=timeout)
                res.raise_for_status()
                time.sleep(2)

                return res.text

            except (ConnectionError, HTTPError, Timeout, RequestException) as e:
                logger.error("Error:", e)
                logger.error("Retrying...")

    def result_append(self, futures, _list: list, csv_path):
        pbar = tqdm(total=len(futures))
        # 処理
        for future in concurrent.futures.as_completed(futures):
            # リスト追加
            _list.append(future.result())
            # csv追記
            with open(csv_path, 'a', encoding=Constant.ENCODE_TYPE_SJIS, newline='') as f:
                writer = csv.writer(f)
                # writer.writerows([element for element in future.result()])
                writer.writerows([future.result()])
            # プログレスバーの更新
            pbar.update()
        pbar.close()

    def result_extend(self, futures, _list: list, csv_path):
        pbar = tqdm(total=len(futures))
        # 処理
        for future in concurrent.futures.as_completed(futures):
            # 重複削除
            if not any(element in _list for element in future.result()):
                # リスト追加
                _list += future.result()
                # csv追記
                with open(csv_path, 'a', encoding=Constant.ENCODE_TYPE_SJIS, newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows([[element] for element in future.result()])
            # プログレスバーの更新
            pbar.update()
        pbar.close()
