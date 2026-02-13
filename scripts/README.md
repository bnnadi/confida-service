# Scripts

Utility scripts for development, deployment, and database management. Scripts are grouped by purpose.

## Directory Structure

```
scripts/
├── seed/           # Database seeding scripts
├── setup/          # Database and environment setup
├── deploy/         # Deployment scripts (future)
└── ...             # Migration, validation, and other utilities
```

## Seed Scripts (`scripts/seed/`)

Populate the database with demo and test data.

| Script | Description |
|--------|-------------|
| `seed_data.py` | Main seed script – demo users, interview sessions, sample data |
| `run_seed.py` | Convenience wrapper – runs `seed_data.py` |
| `seed_question_bank.py` | Seeds the global question bank from `data/sample_questions.json` |
| `seed_question_database.py` | Seeds the question database with curated questions |
| `seed_scenarios.py` | Seeds practice scenarios for dual-mode interviews |

**Usage** (run from project root):
```bash
python scripts/seed/seed_data.py
# or
python scripts/seed/run_seed.py
```

See `docs/SEED_DATA_README.md` for full documentation.

## Setup Scripts (`scripts/setup/`)

Database and development environment setup.

| Script | Description |
|--------|-------------|
| `setup_database.py` | Creates database and runs initial migrations |
| `setup_dev_database.py` | Automated PostgreSQL development setup |
| `setup-database.sh` | Shell script for Docker-based database setup |

**Usage** (run from project root):
```bash
python scripts/setup/setup_dev_database.py
# or for Docker
bash scripts/setup/setup-database.sh development
```

## Other Scripts

| Script | Description |
|--------|-------------|
| `run_tests.py` | Test runner with coverage and filtering |
| `deploy_migrations.py` | Deploy database migrations |
| `validate_migration.py` | Validate migration files |
| `question_bank_cli.py` | Question bank management CLI |
