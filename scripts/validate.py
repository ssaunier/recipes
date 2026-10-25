"""Validate recipes/<slug>/recipe.md (RecipeMD) and optional meta.yml.

Usage: python scripts/validate.py [recipes_dir]
Format and meta.yml problems are errors (exit 1). Project conventions
(short description, no parenthetical in ingredients) are warnings only,
since older recipes predate them.
"""
import re
import sys
from pathlib import Path

import yaml
from recipemd.data import RecipeParser

MAX_DESCRIPTION_WORDS = 6
META_KEYS = {"to_test": bool}


def check_recipe(path):
    try:
        recipe = RecipeParser().parse(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"Invalid RecipeMD ({exc})"], []

    errors, warnings = [], []
    description = (recipe.description or "").strip()
    words = len(description.split())
    if words > MAX_DESCRIPTION_WORDS:
        warnings.append(f"Description has {words} words, maximum is {MAX_DESCRIPTION_WORDS}")

    for ingredient in recipe.leaf_ingredients:
        # An amount that is not in italics (e.g. **200 g** or a bare 200 g)
        # still parses, but lands in the ingredient name with no amount.
        if ingredient.amount is None and re.match(r"[*_\d]", ingredient.name):
            errors.append(
                f"Amount not in italics in ingredient {ingredient.name!r} (write it as *200 g* name)"
            )
        if "(" in ingredient.name:
            warnings.append(f"Parenthetical mention in ingredient {ingredient.name!r}")
    return errors, warnings


def check_meta(path):
    try:
        meta = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return [f"Invalid YAML ({exc})"], []
    if not isinstance(meta, dict):
        return ["meta.yml must be a mapping"], []

    errors = [f"Unknown key {key!r}" for key in meta if key not in META_KEYS]
    errors += [
        f"{key!r} must be {kind.__name__}"
        for key, kind in META_KEYS.items()
        if key in meta and not isinstance(meta[key], kind)
    ]
    return errors, []


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "recipes")
    failed = warned = 0
    for path in sorted(root.glob("*/recipe.md")):
        checks = [(path, check_recipe(path))]
        meta = path.with_name("meta.yml")
        if meta.exists():
            checks.append((meta, check_meta(meta)))
        for file, (errors, warnings) in checks:
            for error in errors:
                print(f"::error file={file}::{error}")
                failed += 1
            for warning in warnings:
                print(f"::warning file={file}::{warning}")
                warned += 1
    print(f"{failed} error(s), {warned} warning(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
