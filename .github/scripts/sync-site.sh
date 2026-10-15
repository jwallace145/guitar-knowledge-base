#!/usr/bin/env bash
# Sync a Zensical build to an S3 prefix with per-file-type Cache-Control.
#
#   sync-site.sh <source-dir> <s3-uri> <default-max-age-seconds> [extra aws args]
#
# Four passes, each with --delete so removed pages disappear from the bucket:
#   1. everything else (images, LICENSE, unhashed CSS)      max-age=<default>
#   2. hashed bundles (*.min.js, *.min.css)                   immutable, one year
#   3. search.json and sitemap.xml                            always revalidate
#   4. HTML, with an explicit UTF-8 content type              always revalidate
#
# Extra arguments (for example --dryrun) are passed to every aws s3 sync call.
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "usage: $0 <source-dir> <s3-uri> <default-max-age-seconds> [extra aws args]" >&2
  exit 2
fi

src="${1%/}/"
dest="${2%/}/"
default_max_age="$3"
shift 3

sync() {
  aws s3 sync "$src" "$dest" --delete --no-progress "$@"
}

sync \
  --exclude "*.html" \
  --exclude "*.min.js" \
  --exclude "*.min.css" \
  --exclude "search.json" \
  --exclude "sitemap.xml" \
  --cache-control "public, max-age=${default_max_age}"

sync \
  --exclude "*" \
  --include "*.min.js" \
  --include "*.min.css" \
  --cache-control "public, max-age=31536000, immutable"

sync \
  --exclude "*" \
  --include "search.json" \
  --include "sitemap.xml" \
  --cache-control "public, max-age=0, must-revalidate"

sync \
  --exclude "*" \
  --include "*.html" \
  --cache-control "public, max-age=0, must-revalidate" \
  --content-type "text/html; charset=utf-8"
