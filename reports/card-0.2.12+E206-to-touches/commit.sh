#!/bin/bash
# usage: commit.sh "<msg>" file...   (repo root; 暫時 index，不動共用 index)
set -e
MSG="$1"; shift
P="reports/card-0.2.12+E206-to-touches"
TMP=$(mktemp -u).idx; export GIT_INDEX_FILE=$TMP
git read-tree HEAD
git add -f -- "$@"
TREE=$(git write-tree)
C=$(git commit-tree "$TREE" -p HEAD -m "$MSG

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>")
unset GIT_INDEX_FILE; rm -f $TMP
git update-ref HEAD $C
git reset -q HEAD -- "$P"
echo $C
