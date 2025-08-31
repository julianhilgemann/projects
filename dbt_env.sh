# dbt_env.sh — for Git Bash when venv is already active

# sanity: fail fast if no venv (optional)
: "${VIRTUAL_ENV:?Activate your venv first (source .venv/Scripts/activate)}"

# make dbt use THIS repo's profiles.yml
export DBT_PROFILES_DIR="$(pwd)"
unset DBT_PROJECT_DIR DBT_TARGET

# shortcuts (pass extra args like --select, --full-refresh, etc.)
dbr()   { dbt run   --project-dir ./portfolio --profiles-dir . "$@"; }
dbtst() { dbt test  --project-dir ./portfolio --profiles-dir . "$@"; }
dbdbg() { dbt debug --project-dir ./portfolio --profiles-dir .; }