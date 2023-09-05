class Constant:
    '''
    定数定義クラス
    '''

    # フラグ
    FLAG_ON_BOOL = True
    FLAG_OFF_BOOL = False
    FLAG_ON_INT = 1
    FLAG_OFF_INT = 0
    FLAG_ON = '1'
    FLAG_OFF = '0'

    # 文字コード
    ENCODE_TYPE_UTF8 = 'utf-8'
    ENCODE_TYPE_SJIS = 'shift_jis'
    ENCODE_TYPE_CP932 = 'cp932'

    # 処理要求コード
    REQUEST_CD_STORE = 1
    REQUEST_CD_ITEM_URL = 2
    REQUEST_CD_ITEM = 3

    # CSVヘッダー
    HEADER_STORE_CSV = ['ストアコード']
    HEADER_ITEM_URLS_CSV = ['商品ページURL']
    HEADER_ITEM_CSV = ['商品URL', '配送情報', '商品タイトル']

    # URL
    ITEM_URL_START = r'https://ja.aliexpress.com/item/'
    ITEM_URL_END = r'.html'
