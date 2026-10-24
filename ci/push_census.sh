#!/bin/sh
# Push census/latest.json to the afterlife/census branch (never to main).
set -eu
REMOTE="https://oauth2:${AFTERLIFE_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git"
WORK=$(mktemp -d)
git config --global user.name "AFTERLIFE census"
git config --global user.email "afterlife-census@noreply.${CI_SERVER_HOST}"
if git ls-remote --exit-code --heads "$REMOTE" afterlife/census >/dev/null 2>&1; then
  git clone --quiet --depth 1 --branch afterlife/census "$REMOTE" "$WORK"
else
  git init --quiet "$WORK"
  git -C "$WORK" checkout --quiet --orphan afterlife/census
  git -C "$WORK" remote add origin "$REMOTE"
fi
mkdir -p "$WORK/census"
cp census/latest.json "$WORK/census/latest.json"
cp census/latest.json "$WORK/census/$(date -u +%Y-%m-%d).json"
git -C "$WORK" add census
if git -C "$WORK" diff --cached --quiet; then
  echo "census unchanged"; exit 0
fi
git -C "$WORK" commit --quiet -m "census: $(date -u +%Y-%m-%dT%H:%MZ) from pipeline ${CI_PIPELINE_ID}"
git -C "$WORK" push --quiet -o ci.skip origin HEAD:afterlife/census
echo "census pushed to afterlife/census"
