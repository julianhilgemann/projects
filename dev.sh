# dev.sh — source this (do NOT run it) at the start of a repo session

# 1) activate venv (Windows Git Bash path)
if [ -f .venv/Scripts/activate ]; then
  . .venv/Scripts/activate
else
  echo "❌ .venv not found. Create it:  py -3.9 -m venv .venv"
  return 1 2>/dev/null || exit 1
fi

# 2) make dbt use the local profiles.yml (this repo)
export DBT_PROFILES_DIR="$(pwd)"
unset DBT_PROJECT_DIR DBT_TARGET

# 3) handy shortcuts (functions accept extra args)
dbr()   { dbt run  --project-dir ./portfolio --profiles-dir . "$@"; }
dbtst() { dbt test --project-dir ./portfolio --profiles-dir . "$@"; }
dbdbg() { dbt debug --project-dir ./portfolio --profiles-dir .; }
