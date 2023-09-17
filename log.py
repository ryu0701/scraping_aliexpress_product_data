import logzero
from logzero import logger
from pathlib import Path
import yaml
from datetime import datetime


class Logger:
    '''
    ロガークラス
    '''

    def __init__(self, debug_flg):

        # ディレクトリ
        cwd = Path.cwd()

        # 設定ファイル読み込み
        with open(Path(cwd, 'config', 'config.yml'), encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 日付取得
        dt_now = datetime.now()
        exec_ymd = dt_now.strftime('%Y%m%d')

        # 出力レベルの設定
        if config['FLAG']['debug'] or debug_flg:
            logzero.loglevel(10)
        else:
            logzero.loglevel(20)

        # ファイル出力
        if config['LOG']['path']:
            log_file_path = config['LOG']['path']
        else:
            log_file_path = str(Path(cwd, 'logs'))

        log_file_name = config['LOG']['name']

        # ファイル作成
        with open(str(Path(log_file_path, exec_ymd))+'_'+log_file_name, 'w', encoding='shift-jis'):
            pass

        logzero.logfile(Path(log_file_path, exec_ymd+'_'+log_file_name))

    # debug
    def debug(self, msg, *args, **kwargs):
        logger.debug(msg, *args, **kwargs)

    # info
    def info(self, msg, *args, **kwargs):
        logger.info(msg, *args, **kwargs)

    # warning
    def warning(self, msg, *args, **kwargs):
        logger.warning(msg, *args, **kwargs)

    # error
    def error(self, msg, *args, **kwargs):
        logger.error(msg, *args, **kwargs)
