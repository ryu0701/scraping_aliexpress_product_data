---
## 【機能】
Aliexpressから商品データを取得
---

## 【準備】

インプットするデータを入力する。

▼ デフォルト設定は csv フォルダ
scraping_aliexpress_product_data\csv

1. 「search_text_list.csv」に検索キーワードをセット
   ・引数をつけない場合に必要
   ・引数「-s」をつける場合に必要
2. 「store_cd_list.csv」にストアコードをセット
   ・引数「-u」をつける場合に必要
3. 「item_url_list.csv」に商品ページ URL をセット
   ・引数「-i」をつける場合に必要

---

## 【実行方法】

1. コマンドプロンプトを開く
   windows ボタンを押して「cmd」と入力して Enter
2. cd コマンドを使ってこのプロジェクトのフォルダへ移動する
   例：「cd C:\temp\get_aliexpress_product_data」
3. 下記【実行コマンド】を入力して実行

---

## 【実行コマンド】

1. 全処理実行
   「python get_aliexpress_product_data.py」「python get_aliexpress_product_data.py -s -u -i」
2. ストアコード取得処理のみ実行
   「python get_aliexpress_product_data.py -s」
3. 商品ページ URL 取得処理のみ実行
   「python get_aliexpress_product_data.py -u」
4. 商品ページ情報取得処理のみ実行
   「python get_aliexpress_product_data.py -i」

---

## 【出力ファイル】

▼ デフォルトは csv フォルダ

1. scraping_store_data.csv
   検索キーワードをもとに抽出したストアコード一覧ファイル。
2. scraping_item_urls.csv
   ストアコードをもとに抽出した商品 URL 一覧ファイル。
3. scraping_item_data.csv
   商品 URL をもとに抽出した商品データ一覧ファイル。
