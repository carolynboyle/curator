# pyproject.toml

**Path:** pyproject.toml
**Syntax:** toml
**Generated:** 2026-04-16 11:00:26

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "curator"
version = "0.1.0"
description = "The Curator — web UI and database interface for the Project Crew"
authors = [
    { name = "Carolyn Boyle" }
]
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "jinja2>=3.1.0",
    "python-multipart>=0.0.9",
    "pyyaml>=6.0",
    "dbkit @ git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/dbkit",
    "viewkit @ git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/viewkit",
]

[project.entry-points."projectcrew.plugins"]
curator = "curator:plugin"

[tool.setuptools.packages.find]
where = ["src"]
include = ["curator*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```
