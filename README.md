# 📂 FolderDumpApp

フォルダ構成を **テキスト／JSON／CSV／DOT** などに出力できる GUI アプリケーションです。  
ドラッグ＆ドロップや参照ダイアログで複数のフォルダを指定し、簡単に構造を可視化・保存できます。

---

## ✨ 主な機能

- フォルダを **ドラッグ＆ドロップ／参照ダイアログ** で追加  
- 複数フォルダの一覧管理（順序入替・削除・全削除）  
- 出力フォーマット選択  
  - `plain`（テキスト）  
  - `tree`（ツリー表記）  
  - `json`  
  - `csv`  
  - `dot`（Graphviz 用）  
- `.gitignore` の簡易対応（除外パターン／否定パターン）  
- **シンボリックリンクの追跡切替**  
- **進捗バー／キャンセルボタン／統計表示**  
- 結果プレビューの **コピー／検索**（全文・部分）  
- **保存ダイアログ**から各形式でエクスポート  
- メニューバー／ツールバー（Open / Save / Copy / Search）  
- Windows 用アイコン設定済み（タスクバー／ウィンドウ）

---

## 🖥️ 動作環境

- Windows 10 / 11  
- Python 不要（exe 版を利用する場合）  
- Python 3.10+（ソースから実行する場合）

---

## 📥 インストール方法（ユーザー向け）

1. [Releases ページ](https://github.com/totsuka0405/folderdump/releases) から最新の `FolderDumpApp.exe` をダウンロード  
2. 任意のフォルダに配置して実行  
   - インストール不要、単体 exe で動作します  
3. フォルダをドラッグ＆ドロップ、または「参照」ボタンから追加してご利用ください  

---

## 🚀 開発者向け（ソースから実行）

```bash
git clone https://github.com/totsuka0405/folderdump.git
cd folderdump
pip install -r requirements.txt
python main.py
