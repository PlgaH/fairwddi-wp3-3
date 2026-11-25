"""Architectural isolation and fidelity tests for `fairwddi.importer`."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from typer.testing import CliRunner


def test_importer_has_zero_harmonization_or_compare_imports() -> None:
    """Assert via AST that no module inside `fairwddi.importer` touches compare or harmonize."""
    importer_dir = Path(__file__).resolve().parent.parent / "src" / "fairwddi" / "importer"
    forbidden_prefixes = (
        "fairwddi.compare",
        "fairwddi.harmonize",
        "fairwddi.ingest",
        "dartfx.ddi.harmonizer",
    )
    py_files = sorted(importer_dir.rglob("*.py"))
    assert len(py_files) >= 6

    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(forbidden_prefixes), (
                        f"Forbidden import '{alias.name}' in {py_file.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not mod.startswith(forbidden_prefixes), (
                    f"Forbidden from-import '{mod}' in {py_file.name}"
                )


def _write_sample_ddic(path: Path, study_id: str, agency: str = "fr.cdsp") -> Path:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<codeBook xmlns="ddi:codebook:2_5" ID="{study_id}">
  <stdyDscr>
    <citation>
      <titlStmt><titl xml:lang="fr">Enquête Test {study_id}</titl></titlStmt>
      <prodStmt><producer>{agency}</producer></prodStmt>
    </citation>
  </stdyDscr>
  <fileDscr ID="F1"><fileTxt><fileName>{study_id}.csv</fileName></fileTxt></fileDscr>
  <dataDscr>
    <var ID="V1" name="v_intpol" files="F1">
      <labl xml:lang="fr">Intérêt pour la politique</labl>
      <qstn><qstnLit xml:lang="fr">Vous intéressez-vous à la politique ?</qstnLit></qstn>
      <catgry><catValu>1</catValu><labl xml:lang="fr">Beaucoup</labl></catgry>
      <catgry><catValu>2</catValu><labl xml:lang="fr">Assez</labl></catgry>
      <catgry missing="Y"><catValu>9</catValu><labl xml:lang="fr">Ne sait pas</labl></catgry>
    </var>
    <var ID="V2" name="v_trust" files="F1">
      <labl xml:lang="fr">Confiance dans le parlement</labl>
      <qstn><qstnLit xml:lang="fr">Avez-vous confiance dans le parlement ?</qstnLit></qstn>
      <catgry><catValu>1</catValu><labl xml:lang="fr">Oui</labl></catgry>
      <catgry><catValu>2</catValu><labl xml:lang="fr">Non</labl></catgry>
    </var>
  </dataDscr>
</codeBook>
"""
    path.write_text(xml, encoding="utf-8")
    return path


@pytest.mark.django_db
def test_cli_import_direct_file_preserves_missing_flags_and_category_scheme_modes(
    tmp_path: Path,
) -> None:
    """Verify `fairwddi import <file>` preserves per_codelist CategorySchemes & is_missing."""
    from fairwddi.cli import app
    from fairwddi.importer.loader import undo_import
    from fairwddi.models import (
        Category,
        CategoryScheme,
        Code,
        CodeList,
        SemanticRelationship,
        UrnRegistry,
    )

    f1 = _write_sample_ddic(tmp_path / "study_single.xml", "S_SINGLE")
    out1 = tmp_path / "out_single"
    runner = CliRunner()
    res1 = runner.invoke(
        app,
        ["import", str(f1), "--output-dir", str(out1), "--category-scheme-mode", "single"],
    )
    assert res1.exit_code == 0, res1.output
    assert CategoryScheme.objects.count() == 1
    assert CodeList.objects.count() == 2
    assert Category.objects.filter(is_missing=True).count() == 1
    assert Code.objects.filter(is_missing=True).count() == 1
    # Pure import creates zero harmonized/generated objects or derivation edges
    assert UrnRegistry.objects.filter(origin="generated").count() == 0
    assert SemanticRelationship.objects.filter(predicate="prov:wasDerivedFrom").count() == 0

    for cl in CodeList.objects.all():
        assert cl.scheme is not None
    for cat in Category.objects.all():
        assert cat.scheme is not None

    # Clean rollback before testing per_codelist mode
    from fairwddi.models import IngestBatch

    b1 = IngestBatch.objects.order_by("-id").first()
    assert b1 is not None
    undo_import(b1.id)
    assert CategoryScheme.objects.count() == 0

    f2 = _write_sample_ddic(tmp_path / "study_percl.xml", "S_PERCL")
    out2 = tmp_path / "out_percl"
    res2 = runner.invoke(
        app,
        ["import", str(f2), "--output-dir", str(out2), "--category-scheme-mode", "per-codelist"],
    )
    assert res2.exit_code == 0, res2.output
    assert CategoryScheme.objects.count() == 2
    assert CodeList.objects.count() == 2
    scheme_urns = {cl.scheme_id for cl in CodeList.objects.all() if cl.scheme_id}
    assert len(scheme_urns) == 2
    assert Category.objects.filter(is_missing=True).count() == 1
    assert Code.objects.filter(is_missing=True).count() == 1


@pytest.mark.django_db
def test_ddil33_import_preserves_scheme_urns_and_is_missing(tmp_path: Path) -> None:
    """Verify DDI 3.3 XML streaming retains parent CategoryScheme URN and isMissing flags."""
    from fairwddi.importer.pipeline import run_import
    from fairwddi.importer.preflight import upgrade_ddic_to_ddil
    from fairwddi.models import Category, CategoryScheme, Code, CodeList

    ddic = _write_sample_ddic(tmp_path / "study_33.xml", "S33")
    up = upgrade_ddic_to_ddil(
        ddic,
        output_path=tmp_path / "study_33.ddi33.xml",
        output_format="ddi33-xml",
        category_scheme_mode="per_codelist",
    )
    assert up["category_scheme_mode"] == "per_codelist"

    res = run_import(up["output_file"], auto_approve=True)
    assert res["status"] == "completed"
    assert CategoryScheme.objects.count() == 2
    # Ensure schemes kept real URNs (not anonymous fallback)
    for cs in CategoryScheme.objects.all():
        assert ":anonymous:" not in cs.urn
    assert Category.objects.filter(is_missing=True).count() == 1
    assert Code.objects.filter(is_missing=True).count() == 1
    assert CodeList.objects.filter(scheme__isnull=False).count() == 2
