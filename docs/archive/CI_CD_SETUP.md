# CI/CD Setup Documentation

This document describes the CI/CD pipeline configuration for the Ignition Automation Toolkit project.

## 📋 Overview

The project uses a multi-stage CI/CD pipeline that supports both **GitHub Actions** and **GitLab CI/CD**. The pipeline automatically detects and tests:

- **Python backend** (FastAPI, pytest, mypy, black, ruff)
- **React/TypeScript frontend** (Vite, ESLint, TypeScript compiler)
- **Docker containerization**

## 🎯 Detected Project Stack

Based on automated detection:

| Component | Detection | Tools Used |
|-----------|-----------|------------|
| **Python Backend** | `pyproject.toml`, `requirements.txt` | black, ruff, mypy, pytest, bandit, pip-audit |
| **React Frontend** | `frontend/package.json`, `tsconfig.json` | ESLint, TypeScript, Vite |
| **Docker** | `Dockerfile` | docker build, trivy |
| **Tests** | `tests/` directory | pytest, pytest-asyncio, pytest-cov |

## 📁 CI/CD Files Created

### 1. GitHub Actions Workflow
**File**: `.github/workflows/ci.yml`

Multi-job workflow with separate jobs for:
- `python-ci`: Python linting, type checking, testing, security
- `frontend-ci`: Frontend linting, type checking, building, security
- `docker-ci`: Docker build and security scanning
- `integration-test`: Full integration testing
- `ci-summary`: Pipeline result summary

**Triggers**:
- Push to `master`, `main`, or `develop` branches
- Pull requests to `master` or `main`

### 2. GitLab CI Configuration
**File**: `.gitlab-ci.yml`

Multi-stage pipeline with caching:
- `setup`: Install dependencies
- `lint`: Code style and quality checks
- `test`: Unit tests and coverage
- `build`: Production builds
- `security`: Security scans
- `integration`: Integration tests

**Caching**: Separate caches for Python (`pip`) and Node.js (`npm`)

### 3. Local Test Script
**File**: `ci_test_local.sh`

Bash script that mimics the CI/CD pipeline locally without requiring GitHub/GitLab runners.

**Usage (Direct)**:
```bash
# Run entire pipeline
./ci_test_local.sh all

# Run specific stages
./ci_test_local.sh setup
./ci_test_local.sh lint
./ci_test_local.sh test
./ci_test_local.sh build
./ci_test_local.sh security
./ci_test_local.sh integration
```

**Usage (via Makefile - Recommended)**:
```bash
# Run full CI/CD pipeline
make ci

# Run specific stages
make ci-lint        # Lint stage only
make ci-test        # Test stage only
make ci-build       # Build stage only
make ci-security    # Security stage only

# Pre-release workflow (format code + full pipeline)
make pre-release
```

**Features**:
- ✅ Color-coded output (INFO, SUCCESS, WARNING, ERROR)
- ✅ Detailed logging to `ci_test_local.log`
- ✅ Fail-fast for critical stages
- ✅ Non-blocking for optional stages (type checking, security scans)
- ✅ Summary report at the end

## 🚀 Pipeline Stages

### Stage 1: Setup
**Purpose**: Install dependencies and prepare environment

**Python**:
```bash
pip install --upgrade pip
pip install -e .
pip install black ruff mypy pytest pytest-asyncio pip-audit bandit radon
```

**Frontend**:
```bash
cd frontend
npm ci
```

### Stage 2: Lint
**Purpose**: Ensure code quality and style consistency

**Python**:
- **Black**: Code formatting check
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking (non-blocking)
- **Radon**: Complexity analysis (non-blocking)

**Frontend**:
- **ESLint**: JavaScript/TypeScript linting
- **TypeScript**: Type checking with `tsc`

### Stage 3: Test
**Purpose**: Run automated test suites

**Python**:
```bash
pytest tests/ -v --tb=short -x --cov=ignition_toolkit --cov-report=html
```

**Frontend**:
- Build test (ensures frontend compiles)

### Stage 4: Build
**Purpose**: Verify production builds

**Frontend**:
```bash
npm run build
```

**Docker**:
```bash
docker build -t ignition-toolkit:test .
```

### Stage 5: Security
**Purpose**: Scan for vulnerabilities

**Python**:
- **Bandit**: Security issue scanner
- **pip-audit**: Dependency vulnerability check

**Frontend**:
- **npm audit**: Dependency vulnerability check

**Docker**:
- **Trivy**: Container image vulnerability scanner

### Stage 6: Integration (Optional)
**Purpose**: Run integration tests

```bash
pytest tests/test_integration.py -v -m integration
```

## 🧪 Local Testing Instructions

### Quick Start
1. Make the script executable (already done):
   ```bash
   chmod +x ci_test_local.sh
   ```

2. Run the full pipeline:
   ```bash
   ./ci_test_local.sh all
   ```

3. Check the results:
   ```bash
   cat ci_test_local.log
   ```

### Running Individual Stages

**Setup only**:
```bash
./ci_test_local.sh setup
```

**Linting only**:
```bash
./ci_test_local.sh lint
```

**Tests only**:
```bash
./ci_test_local.sh test
```

**Build only**:
```bash
./ci_test_local.sh build
```

**Security scans only**:
```bash
./ci_test_local.sh security
```

### Expected Output

**Successful run**:
```
[INFO] ========================================
[INFO] Running stage: Python Setup
[INFO] ========================================
[SUCCESS] Python Setup completed successfully
...
[INFO] ========================================
[INFO] CI/CD Pipeline Summary
[INFO] ========================================
[SUCCESS] All critical stages passed!
Full log: ci_test_local.log
```

**Failed run**:
```
[ERROR] Python Lint failed
...
[INFO] ========================================
[INFO] CI/CD Pipeline Summary
[INFO] ========================================
[ERROR] 1 critical stage(s) failed
Full log: ci_test_local.log
```

## 🔧 Configuration

### Python Tools Configuration
Configured in `pyproject.toml`:

```toml
[tool.black]
line-length = 100
target-version = ['py310', 'py311']

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
asyncio_mode = "auto"
```

### Frontend Tools Configuration
- **ESLint**: `frontend/eslint.config.js` (auto-detected)
- **TypeScript**: `frontend/tsconfig.json`
- **Vite**: `frontend/vite.config.ts`

## 📊 Test Coverage

The pipeline generates test coverage reports:

**HTML Report**:
```bash
# After running tests
open htmlcov/index.html
```

**Terminal Report**:
```bash
pytest tests/ --cov=ignition_toolkit --cov-report=term
```

## 🔐 Security Scanning Tools

### Python Security
1. **Bandit**: Scans Python code for common security issues
   ```bash
   bandit -r ignition_toolkit/ -ll
   ```

2. **pip-audit**: Checks installed packages for known vulnerabilities
   ```bash
   pip-audit
   ```

### Frontend Security
1. **npm audit**: Checks npm packages for vulnerabilities
   ```bash
   cd frontend && npm audit --audit-level=high
   ```

### Docker Security
1. **Trivy**: Scans Docker images for OS and library vulnerabilities
   ```bash
   trivy image ignition-toolkit:test
   ```

**Install Trivy**:
```bash
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
```

## ⚙️ Environment Variables

### Python
- `PYTHONPATH`: Set to project root
- `PLAYWRIGHT_BROWSERS_PATH`: Custom path for Playwright browsers

### Frontend
- `NODE_VERSION`: Node.js version (18)
- `npm_config_cache`: npm cache directory

## 🐛 Troubleshooting

### Issue: "Black formatting issues found"
**Solution**:
```bash
black ignition_toolkit/ tests/
```

### Issue: "Ruff linting issues found"
**Solution**:
```bash
ruff check ignition_toolkit/ tests/ --fix
```

### Issue: "Docker not installed"
**Solution**: Docker build and security scans are non-blocking. Install Docker if needed:
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install docker.io

# Or use Docker Desktop
```

### Issue: "Trivy not installed"
**Solution**: Trivy scans are non-blocking. Install if needed:
```bash
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
```

### Issue: "Frontend dependencies missing"
**Solution**:
```bash
cd frontend && npm ci
```

## 📈 Adding New Checks

### Add a new Python linter
1. Edit `.github/workflows/ci.yml`:
   ```yaml
   - name: New Linter
     run: |
       pip install new-linter
       new-linter check .
   ```

2. Edit `.gitlab-ci.yml`:
   ```yaml
   python:lint:newlinter:
     stage: lint
     script:
       - pip install new-linter
       - new-linter check .
   ```

3. Edit `ci_test_local.sh`:
   ```bash
   stage_python_lint() {
       # ... existing linters ...
       log_info "  → Running New Linter..."
       new-linter check . || return 1
   }
   ```

## 🚫 Files Excluded from Git

The following CI/CD related files are tracked but NOT pushed to remote:

- `.github/workflows/ci.yml` (local only - add to .gitignore to prevent pushing)
- `.gitlab-ci.yml` (local only - add to .gitignore to prevent pushing)
- `ci_test_local.sh` (local only - can commit this)
- `ci_test_local.log` (ignored)
- `ci_summary.log` (ignored)
- `htmlcov/` (test coverage reports)
- `bandit-report.json` (security reports)

### Prevent Pushing to GitHub

Add to `.gitignore`:
```
# CI/CD workflows (local testing only)
.github/workflows/
.gitlab-ci.yml
ci_test_local.log
ci_summary.log
```

## 📚 References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/)
- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)

## 🔄 Periodic Quality Checks (Pre-Release Workflow)

### When to Run CI/CD Checks

Run the full CI/CD pipeline periodically to maintain code quality:

**Before Every Release**:
```bash
# Recommended: Use the pre-release target
make pre-release
```

This will:
1. Auto-format all code with Black and Ruff
2. Run the full CI/CD pipeline (all 13 stages)
3. Report any issues that need fixing
4. Provide next steps for versioning and tagging

**During Development** (optional but recommended):
- Before committing significant changes: `make ci-lint`
- After adding new features: `make ci-test`
- Before creating pull requests: `make ci`

### Pre-Release Workflow

**Complete workflow for creating a new release**:

```bash
# 1. Ensure all code is formatted and tests pass
make pre-release

# 2. If all passed, bump the version
make bump-patch    # For bug fixes (x.x.X)
make bump-minor    # For new features (x.X.0)
make bump-major    # For breaking changes (X.0.0)

# 3. Commit version bump and changes
git add .
git commit -m "Release vX.X.X - Brief description"

# 4. Tag the release
git tag v$(cat VERSION)

# 5. Push to remote (optional - not required if local only)
git push origin master
git push --tags
```

### Quick Reference: Release Checklist

- [ ] Run `make pre-release` (formats code + runs full CI/CD)
- [ ] Fix any errors reported by the pipeline
- [ ] Bump version with `make bump-patch/minor/major`
- [ ] Update CHANGELOG.md with changes
- [ ] Commit with descriptive message
- [ ] Tag release: `git tag v$(cat VERSION)`
- [ ] Push changes and tags (optional)

## ✅ Development Checklist

Before committing changes, run:

```bash
# Option 1: Quick check (lint only)
make ci-lint

# Option 2: Full pipeline
make ci

# Option 3: Pre-release workflow (includes formatting)
make pre-release

# Fix any formatting issues (if not using pre-release)
make format

# Ensure tests pass
make test
```

## 📝 Notes

- The CI/CD configuration follows the Universal CI/CD Setup Instruction specification
- All stages are designed to be platform-agnostic (GitHub Actions, GitLab CI, local)
- Security scans are non-blocking to avoid false positives from breaking the build
- Type checking is non-blocking to allow gradual adoption
- The pipeline is optimized for Python 3.10+ and Node.js 18+

---

**Last Updated**: 2025-10-28
**Maintainer**: Nigel G
**Status**: Ready for local testing (DO NOT PUSH TO GITHUB)
