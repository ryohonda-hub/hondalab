#!/bin/bash
#SBATCH --output=/home/ryohonda/log/%x_%j.out.log
#SBATCH --error=/home/ryohonda/log/%x_%j.err.log

USER_NAME="$(id -un)"
DIR_HOME="/home/${USER_NAME}/"
DIR_EXTRA="/home/ryohonda/"   # もう一つの検索先

FILE_LIST="${DIR_HOME}/owned_files.list.log"
DU_LOG="${DIR_HOME}/du.log"
OUTPUT_HTML="${DIR_HOME}/plot_du.html"

find "${DIR_HOME}" "${DIR_EXTRA}" -type f -user "${USER_NAME}" -print0 > "${FILE_LIST}"

du -k --files0-from="${FILE_LIST}" > "${DU_LOG}"
rm -f ${FILE_LIST}
python plot_quota.py "${DU_LOG}" --target /home/ --max-depth 6 --output "${OUTPUT_HTML}"
