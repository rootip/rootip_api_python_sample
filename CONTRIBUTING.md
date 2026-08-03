# コントリビューションガイド

root ipクラウド API Pythonサンプルへの改善提案を歓迎します。

## Issue・Pull Requestへ含めないもの

- APIトークン、パスワード、証明書、秘密鍵
- 実顧客の名称、担当者情報、案件・知財情報
- APIレスポンス本文、実環境のログ、`config/secrets.py`

脆弱性は公開Issueではなく [SECURITY.md](SECURITY.md) の手順で報告してください。

## 変更時の必須事項

1. [AI_DEVELOPMENT_RULES.md](AI_DEVELOPMENT_RULES.md) を確認する。
2. DELETE、`verify=False`、確認なしのPOST/PUTを追加しない。
3. 更新系は変更内容を表示し、人の確認後に実行する。一括更新には件数上限を設ける。
4. APIレスポンス本文や実データをテスト・ログへ含めない。
5. 次の検証をリポジトリルートで実行する。

```bash
python -m unittest discover -s tests
python -m compileall -q app rootip tests
```

## 依存関係の変更

依存パッケージの追加・更新は、メンテナの事前承認が必要です。

- まず標準ライブラリで代替できないか確認する。
- パッケージ名・バージョン・配布元を公式PyPIで確認する。
- `requirements.txt` の直接依存と `requirements-lock.txt` の推移依存・SHA-256ハッシュを同時に更新する。
- `requirements-lock.txt` には、サポート対象OS・CPU向けwheelの公式PyPIハッシュだけを記録する。
- sdist、Git URL、任意URL、`--extra-index-url` は使用しない。
- Windows、macOS、LinuxのCIですべて成功することを確認する。

ロックファイルの生成方法を変更する場合も、レビューとCI確認を必須とします。インストールエラーを回避するためにハッシュや `--only-binary=:all:` を削除してはいけません。

## レビューしやすい変更

- 1つのPull Requestでは1つの目的に集中する。
- セキュリティ上の挙動を変える場合は、対応するテストと文書を同時に更新する。
- 外部通信先を追加する場合は、目的・送信内容・利用条件を説明する。
- 公開APIの互換性に影響する場合は、変更理由と移行方法を記載する。
