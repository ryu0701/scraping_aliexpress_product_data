import os
import yaml
from pathlib import Path
from datetime import datetime
import csv
from functions import AppFunction, CommonFunction
from constant import Constant
from log import Logger
import argparse


# ディレクトリ
cwd = Path.cwd()

# 設定ファイル読み込み
with open(Path(cwd, 'config', 'config.yml'), encoding=Constant.ENCODE_TYPE_UTF8) as f:
    config = yaml.safe_load(f)

# コマンドライン引数操作
parser = argparse.ArgumentParser(
    prog='get_aliexpress_product_data.py',  # プログラム名
    usage='Aliexpressスクレイピング',  # プログラムの利用方法
    description='操作をコマンドライン引数で指定',  # 引数のヘルプの前に表示
    epilog='※引数指定が無い場合は全データ抽出が実行されます',  # 引数のヘルプの後で表示
    add_help=True,  # -h/–help オプションの追加
)

# 引数を設定
parser.add_argument('-s', '--store', action='store_true', required=False, help='ストアコード出力(input: 検索キーワードリスト)')
parser.add_argument('-u', '--urls', action='store_true', required=False, help='商品ページURL出力(input: ストアコードリスト)')
parser.add_argument('-i', '--item', action='store_true', required=False, help='商品データ出力(input: 商品ページURLリスト)')
parser.add_argument('-d', '--debug', action='store_true', required=False, help='デバッグモードで実行')
# 引数を解析
args = parser.parse_args()

# 処理要求コードを設定
request_cd_list = []

if args.store:
    request_cd_list.append(Constant.REQUEST_CD_STORE)
if args.urls:
    request_cd_list.append(Constant.REQUEST_CD_ITEM_URL)
if args.item:
    request_cd_list.append(Constant.REQUEST_CD_ITEM)

if len(request_cd_list) == 0:
    request_cd_list.append(Constant.REQUEST_CD_STORE)
    request_cd_list.append(Constant.REQUEST_CD_ITEM_URL)
    request_cd_list.append(Constant.REQUEST_CD_ITEM)

# デバッグフラグ取得
debug_flg = Constant.FLAG_ON_BOOL if args.debug else config['FLAG']['debug']

# インスタンス化
comm_func = CommonFunction(debug_flg)
app_func = AppFunction(debug_flg)
logger = Logger(debug_flg)


def main():
    '''
    メイン処理
    '''
    # 処理開始
    date_now = datetime.now()
    str_yyyymmdd = date_now.strftime('%Y%m%d')

    start_time = date_now.strftime('%Y/%m/%d %H:%M:%S')
    logger.info(f'▼---------------処理開始: {start_time}---------------▼')

    # CSV出力先取得
    if config['CSV']['path']['input']:
        input_csv_path = config['CSV']['path']['input']
    else:
        input_csv_path = str(Path(cwd, 'csv'))
    if config['CSV']['path']['output']:
        output_csv_path = config['CSV']['path']['output']
    else:
        output_csv_path = str(Path(cwd, 'csv'))

    # 出力日ディレクトリ作成
    output_csv_path = output_csv_path + '\\' + str_yyyymmdd
    # ディレクトリが存在しなければ作成
    if not os.path.exists(output_csv_path):
        os.makedirs(output_csv_path)

    # 変数宣言
    search_text_list = []
    store_cd_list = []

    try:
        # 【処理①】検索キーワードからストアコード取得
        if Constant.REQUEST_CD_STORE in request_cd_list:
            # 検索キーワードリスト取得
            iuput_csv = config['CSV']['input']
            with open(Path(cwd, 'csv', iuput_csv), 'r', encoding=Constant.ENCODE_TYPE_SJIS) as f:
                reader = csv.reader(f)
                search_text_list = [reader_list[0] for reader_list in reader]
            search_text_list.pop(0)  # ヘッダー分削除

            if len(search_text_list) == 0:
                logger.error('検索キーワードが正しく取得できませでした。処理を終了します。')
                return False

            logger.info('▼検索キーワードからストアコードリストを取得開始')

            # データ取得
            if debug_flg:
                store_cd_list: list = comm_func.func_speed(app_func.get_search_top_result_datas, search_text_list)  # 処理時間計測時
            else:
                store_cd_list: list = app_func.get_search_top_result_datas(search_text_list)

        # 【処理②】抽出したストアコードから注文表示のある商品ページURLを取得
        if Constant.REQUEST_CD_ITEM in request_cd_list:
            # store_cd_listが空の場合CSVからストアコード取得
            if len(store_cd_list) == 0:
                input_store_csv = config['CSV']['input']['store']
                with open(Path(input_csv_path, input_store_csv), 'r', encoding=Constant.ENCODE_TYPE_SJIS) as f:
                    store_cd_list: list = f.read().split('\n')
                store_cd_list.pop(0)  # ヘッダー分削除

            if len(store_cd_list) == 0:
                logger.error('ストアコードが正しく取得できませでした。処理を終了します。')
                return False

            logger.info('▼ストアコードから注文表示のある商品ページURLを取得開始')

            # データ取得（商品ページURL）
            if debug_flg:
                ordered_item_url_list: list = comm_func.func_speed(app_func.get_ordered_item_datas, store_cd_list)  # 処理時間計測時
            else:
                ordered_item_url_list = app_func.get_ordered_item_datas(store_cd_list)

        # 【処理③】商品ページURLから配送情報を取得
        if Constant.REQUEST_CD_ITEM in request_cd_list:
            # ordered_item_url_listが空の場合CSVからストアコード取得
            if len(ordered_item_url_list) == 0:
                item_urls_csv = config['CSV']['input']['item_urls']
                with open(Path(input_csv_path, item_urls_csv), 'r', encoding=Constant.ENCODE_TYPE_SJIS) as f:
                    ordered_item_url_list: list = f.read().split('\n')
                ordered_item_url_list.pop(0)  # ヘッダー分削除

            if len(ordered_item_url_list) == 0:
                logger.error('商品ページURLが正しく取得できませでした。処理を終了します。')
                return False

            logger.info('▼商品ページURLから情報を取得開始')

            # データ取得（配送情報）
            if debug_flg:
                item_data_list: list = comm_func.func_speed(app_func.get_item_delivery_datas, ordered_item_url_list)  # 処理時間計測時
            else:
                item_data_lsit: list = app_func.get_item_delivery_datas(ordered_item_url_list)

    except FileNotFoundError:
        logger.error("存在しないファイルを参照しようとしています。csvが指定フォルダに格納されているか確認してください。")

    except Exception as e:
        logger.error(e)

    finally:
        end_time = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        logger.info(f'▲---------------処理終了: {end_time}---------------▲')


if __name__ == '__main__':
    main()
