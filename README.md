---
## 【準備】

1. 「search_text_list.csv」に検索キーワードをセット
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
   「python get_aliexpress_product_data.py」「python get_aliexpress_product_data.py -s -i」
2. ストアコード取得処理のみ実行
   「python get_aliexpress_product_data.py -s」
3. 商品ページ情報取得処理のみ実行
   「python get_aliexpress_product_data.py -i」
   ※この場合「scraping_store_data.csv」ファイルにストアコードが入力されている必要があります。

---

## 【各種ファイル】

▼csv フォルダ

1. search_text_list.csv
   検索キーワードをセットするファイル。2 行目以降に値を入力してください。
2. scraping_store_data.csv
   検索キーワードをもとに抽出したストアコード一覧ファイル。
3. scraping_store_data.csv
   ストアコードをもとに抽出した商品 URL と配達日一覧ファイル。
