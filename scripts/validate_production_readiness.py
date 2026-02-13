#!/usr/bin/env python3
"""
Production Readiness Validation Script

Validates confida-service before production deployment. Run locally or against
a remote URL. Exit code 0 = all pass, non-zero = failures.

Usage:
  python scripts/validate_production_readiness.py
  python scripts/validate_production_readiness.py --url https://staging.example.com
  python scripts/validate_production_readiness.py --url-only  # Skip local checks
  python scripts/validate_production_readiness.py --skip-remote  # Skip HTTP checks
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Optional: requests for HTTP checks (avoid hard dependency if not installed)
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def print_header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_success(message: str) -> None:
    print(f"  ✅ {message}")


def print_error(message: str) -> None:
    print(f"  ❌ {message}")


def print_warning(message: str) -> None:
    print(f"  ⚠️  {message}")


def check_env_vars() -> bool:
    """Check required environment variables for production."""
    print_header("Environment Variables")
    all_pass = True

    # SECRET_KEY must not be default
    secret = os.getenv("SECRET_KEY", "")
    default_secret = "your-secret-key-change-this-in-production"
    if not secret or secret == default_secret:
        print_error(f"SECRET_KEY must be set and not the default value")
        all_pass = False
    else:
        print_success("SECRET_KEY is set and not default")

    # DATABASE_URL required
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print_error("DATABASE_URL is not set")
        all_pass = False
    else:
        # Don't log the URL (contains credentials)
        if "localhost" in db_url and "prod" in os.getenv("ENVIRONMENT", "").lower():
            print_warning("DATABASE_URL points to localhost in production environment")
        print_success("DATABASE_URL is set")

    return all_pass


def check_config_validation() -> bool:
    """Run settings.validate_configuration() and ensure no errors."""
    print_header("Configuration Validation")
    try:
        from app.config import get_settings
        settings = get_settings()
        result = settings.validate_configuration_with_warnings()
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])

        if errors:
            for err in errors:
                print_error(err)
            return False
        if warnings:
            for w in warnings:
                print_warning(w)
        print_success("Configuration validation passed (no errors)")
        return True
    except Exception as e:
        print_error(f"Configuration validation failed: {e}")
        return False


def check_migrations() -> bool:
    """Check that alembic current matches head."""
    print_header("Database Migrations")
    try:
        import subprocess
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        current = result.stdout.strip() if result.returncode == 0 else ""

        result_head = subprocess.run(
            ["alembic", "heads"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        heads = result_head.stdout.strip() if result_head.returncode == 0 else ""

        if not current:
            print_warning("No current migration (database may be empty)")
            return True  # Allow empty DB for fresh deploy
        if not heads:
            print_error("Could not get alembic heads")
            return False

        # Extract revision IDs (format: "abc123 (head)" or "abc123")
        current_rev = current.split()[0] if current else ""
        head_revs = [h.split()[0] for h in heads.splitlines() if h.strip()]

        if current_rev in head_revs:
            print_success(f"Migrations up to date (current: {current_rev})")
            return True
        else:
            print_error(f"Migrations out of date. Current: {current_rev}, Heads: {head_revs}")
            return False
    except FileNotFoundError:
        print_warning("alembic not found in PATH, skipping migration check")
        return True
    except Exception as e:
        print_error(f"Migration check failed: {e}")
        return False


def check_health(url: str, timeout: int = 10) -> bool:
    """Check /health returns 200 and status is healthy or degraded."""
    print_header("Health Check")
    if not REQUESTS_AVAILABLE:
        print_error("requests library not installed. pip install requests")
        return False
    try:
        r = requests.get(f"{url.rstrip('/')}/health", timeout=timeout)
        if r.status_code != 200:
            print_error(f"GET /health returned {r.status_code}")
            return False
        data = r.json()
        status = data.get("status", "")
        if status not in ("healthy", "degraded"):
            print_error(f"Health status is '{status}' (expected healthy or degraded)")
            return False
        print_success(f"Health check passed (status: {status})")
        return True
    except requests.RequestException as e:
        print_error(f"Health check request failed: {e}")
        return False
    except ValueError as e:
        print_error(f"Invalid JSON response: {e}")
        return False


def check_consent_auth(url: str, timeout: int = 10) -> bool:
    """Check that GET /api/v1/consent/ requires auth (returns 401 when unauthenticated)."""
    print_header("Privacy: Consent Endpoint Auth")
    if not REQUESTS_AVAILABLE:
        print_error("requests library not installed. pip install requests")
        return False
    try:
        r = requests.get(
            f"{url.rstrip('/')}/api/v1/consent/",
            timeout=timeout,
        )
        # Should return 401 Unauthorized when not authenticated
        if r.status_code == 401:
            print_success("Consent endpoint requires authentication (401)")
            return True
        if r.status_code == 200:
            print_error("Consent endpoint returned 200 without auth (should require auth)")
            return False
        print_warning(f"Consent endpoint returned {r.status_code} (expected 401)")
        return True  # Allow other auth-related codes
    except requests.RequestException as e:
        print_error(f"Consent check failed: {e}")
        return False


def check_security_headers(url: str, timeout: int = 10) -> bool:
    """Check that response includes security headers."""
    print_header("Security Headers")
    if not REQUESTS_AVAILABLE:
        print_error("requests library not installed. pip install requests")
        return False
    required_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
    ]
    try:
        r = requests.get(f"{url.rstrip('/')}/health", timeout=timeout)
        missing = [h for h in required_headers if h not in r.headers]
        if missing:
            print_error(f"Missing security headers: {missing}")
            return False
        print_success(f"Security headers present: {required_headers}")
        return True
    except requests.RequestException as e:
        print_error(f"Security headers check failed: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate confida-service production readiness"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL to validate (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--url-only",
        action="store_true",
        help="Skip local checks (env, config, migrations); only run HTTP checks",
    )
    parser.add_argument(
        "--skip-remote",
        action="store_true",
        help="Skip HTTP checks; only run local checks",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )
    args = parser.parse_args()

    results = []

    # Local checks
    if not args.url_only:
        results.append(("Environment variables", check_env_vars()))
        results.append(("Configuration validation", check_config_validation()))
        results.append(("Database migrations", check_migrations()))

    # Remote (HTTP) checks
    if not args.skip_remote:
        results.append(("Health check", check_health(args.url, args.timeout)))
        results.append(("Consent auth", check_consent_auth(args.url, args.timeout)))
        results.append(("Security headers", check_security_headers(args.url, args.timeout)))

    # Summary
    print_header("Summary")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
    print(f"\n  Passed: {passed}/{total}")

    if passed == total:
        print("\n  All checks passed. Ready for production deployment.\n")
        return 0
    else:
        print("\n  Some checks failed. Fix issues before deploying.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
