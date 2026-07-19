# Script to Check Your Quota on the NIG Supercomputer

This script visualizes which files and directories occupy the most disk space in your quota.

## How to Use

1. Edit lines 2–3 of `chkquota.sh` to specify your log directory.
2. Upload `chkquota.sh` and `plot_quota.py` to your home directory.
3. Run this script by
   ```bash
   sbatch chkquota.sh
   ```
4. The script generates `plot_du.html` and `du.log`.
5. Download `plot_du.html` and open it on your local computer. Double-click a pie chart segment to view its breakdown. The generated `.log` files can be deleted after use.

## Note

Your quota also includes files that you own under another user's directory (e.g., `ryohonda`'s directory).

You can check your quota usage with:
```bash
lfs quota -u your_username /lustre10
```

---

# 遺伝研スパコン用ディスク使用量確認スクリプト

遺伝研スパコン上のディスク使用量を確認し、どのファイルやディレクトリが最も多くの容量を使用しているかを可視化するスクリプトです。

## 使い方

1. `chkquota.sh` の2〜3行目を、自分のログディレクトリに合わせて修正します。
2. `chkquota.sh` と `plot_quota.py` をホームディレクトリにアップロードします。
3. 次のコマンドを実行します。
   ```bash
   sbatch chkquota.sh
   ```
4. `plot_du.html` と `du.log` が作成されます。
5. `plot_du.html` をダウンロードしてPCで開きます。円グラフをダブルクリックすると、各ディレクトリ・ファイルの内訳を確認できます。生成された `.log` ファイルは削除して構いません。

## 注

使用量には、`ryohonda` ディレクトリ配下にある、自分が所有するファイルも含まれます。

現在の使用量は次のコマンドで確認できます。

```bash
lfs quota -u your_username /lustre10
```