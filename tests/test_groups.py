"""Tests for DDI Group curation (`fairwddi.groups.manager`) and Unified Resource Set Resolver."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from fairwddi.groups import (
    add_group_members,
    create_group,
    delete_group,
    get_group_details,
    list_groups,
    remove_group_members,
    rename_group,
    resolve_group,
    resolve_resource_set,
)


@pytest.mark.django_db
def test_group_crud_slug_lookup_and_sync() -> None:
    """Verify Group CRUD, unique case-insensitive slug lookup, and dcterms:isPartOf sync."""
    from fairwddi.models import Group, SemanticRelationship, StudyUnit

    s1 = StudyUnit.objects.create(
        urn="urn:ddi:fr.cdsp:su_ess1:1.0.0", name="ESS Wave 1", origin="imported"
    )
    s2 = StudyUnit.objects.create(
        urn="urn:ddi:fr.cdsp:su_ess2:1.0.0", name="ESS Wave 2", origin="imported"
    )

    g = create_group(
        "ESS France Series",
        slug="ess-fr",
        group_type="longitudinal_series",
        description="French waves of the European Social Survey",
        member_urns=[s1.urn],
    )
    assert g["slug"] == "ess-fr"
    assert g["member_count"] == 1
    assert (
        SemanticRelationship.objects.filter(
            subject_urn=s1.urn, predicate="dcterms:isPartOf", object_urn=g["urn"]
        ).count()
        == 1
    )

    # Case-insensitive resolution by slug & URN
    assert resolve_group("ESS-FR").urn == g["urn"]
    assert resolve_group(g["urn"]).slug == "ess-fr"

    # Unique slug collision guard
    with pytest.raises(ValueError, match="already exists"):
        create_group("Duplicate Slug Group", slug="ess-fr")

    # Add and remove members stay synchronized across Group.references and SemanticRelationship
    add_res = add_group_members("ess-fr", [s2.urn])
    assert add_res["added_count"] == 1
    assert add_res["member_count"] == 2
    assert (
        SemanticRelationship.objects.filter(
            predicate="dcterms:isPartOf", object_urn=g["urn"]
        ).count()
        == 2
    )

    rem_res = remove_group_members("ess-fr", [s1.urn])
    assert rem_res["removed_count"] == 1
    assert rem_res["member_count"] == 1
    assert (
        SemanticRelationship.objects.filter(
            subject_urn=s1.urn, predicate="dcterms:isPartOf", object_urn=g["urn"]
        ).count()
        == 0
    )

    renamed = rename_group("ess-fr", name="ESS France Longitudinal", slug="ess-france")
    assert renamed["slug"] == "ess-france"
    assert renamed["name"] == "ESS France Longitudinal"
    assert len(list_groups(group_type="longitudinal_series")) == 1

    del_res = delete_group("ess-france")
    assert del_res["deleted"] is True
    assert Group.objects.filter(urn=g["urn"]).count() == 0
    assert (
        SemanticRelationship.objects.filter(
            predicate="dcterms:isPartOf", object_urn=g["urn"]
        ).count()
        == 0
    )


@pytest.mark.django_db
def test_unified_resource_set_resolver_cascade_and_nested_group_cycle_safety() -> None:
    """Verify StudyUnit cascade expansion and cycle-protected nested group resolution."""
    from fairwddi.models import (
        Category,
        Code,
        CodeList,
        ConceptualVariable,
        Datafile,
        DatafileVariable,
        Group,
        IngestBatch,
        InstanceVariable,
        QuestionItem,
        QuestionVariable,
        RepresentedVariable,
        StudyUnit,
    )

    cv = ConceptualVariable.objects.create(
        urn="urn:ddi:fr.cdsp:cv_trust:1.0.0",
        name="CV_TRUST",
        label={"en": "Trust"},
        origin="generated",
    )
    cat = Category.objects.create(
        urn="urn:ddi:fr.cdsp:cat_yes:1.0.0", name="YES", label={"en": "Yes"}, origin="imported"
    )
    cl = CodeList.objects.create(
        urn="urn:ddi:fr.cdsp:cl_yes:1.0.0", name="CL_YES", origin="imported"
    )
    Code.objects.create(
        urn="urn:ddi:fr.cdsp:code_yes_1:1.0.0",
        code_list=cl,
        category=cat,
        code_value="1",
        origin="imported",
    )
    qi = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_trust:1.0.0",
        name="Q_TRUST",
        question_text={"en": "Do you trust parliament?"},
        origin="imported",
    )
    rv = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_trust:1.0.0",
        name="RV_TRUST",
        conceptual_variable=cv,
        code_list=cl,
        origin="imported",
    )
    QuestionVariable.objects.create(question_item=qi, represented_variable=rv, order=1)
    su = StudyUnit.objects.create(
        urn="urn:ddi:fr.cdsp:su_wave1:1.0.0", name="Wave 1", origin="imported"
    )
    df = Datafile.objects.create(
        urn="urn:ddi:fr.cdsp:df_wave1:1.0.0", name="df1.csv", study_unit=su, origin="imported"
    )
    iv = InstanceVariable.objects.create(
        urn="urn:ddi:fr.cdsp:iv_trust:1.0.0",
        name="v1",
        represented_variable=rv,
        origin="imported",
    )
    DatafileVariable.objects.create(datafile=df, instance_variable=iv, order=1)

    batch = IngestBatch.objects.create(
        source_format="ddi-l-4.0-json",
        file_name="wave1.json",
        file_sha256="a" * 64,
        status="completed",
        created_urns=[su.urn, df.urn, iv.urn, rv.urn, qi.urn, cl.urn, cat.urn],
    )

    g_child = create_group("Child Series", slug="child-series", member_urns=[su.urn])
    g_parent = create_group("Parent Series", slug="parent-series", member_urns=[g_child["urn"]])
    # Introduce a deliberate cycle between Group references to test cycle guard
    parent_obj = Group.objects.get(urn=g_parent["urn"])
    child_obj = Group.objects.get(urn=g_child["urn"])
    child_obj.references = [
        *list(child_obj.references or []),
        {"resource_type": "Group", "urn": parent_obj.urn},
    ]
    child_obj.save()

    res_group = resolve_resource_set("group:parent-series")
    assert res_group.urns_for("StudyUnit") == {su.urn}
    assert res_group.urns_for("QuestionItem") == {qi.urn}
    assert res_group.urns_for("RepresentedVariable") == {rv.urn}
    assert res_group.urns_for("CodeList") == {cl.urn}
    assert res_group.urns_for("Category") == {cat.urn}
    assert res_group.urns_for("ConceptualVariable") == {cv.urn}

    # Resource-type filtering
    filtered = resolve_resource_set("study:" + su.urn, resource_types=["QuestionItem"])
    assert set(filtered.urns_by_type.keys()) == {"QuestionItem"}
    assert filtered.urns_for("QuestionItem") == {qi.urn}

    # batch:, bank:imported, bank:harmonized, urn:
    assert resolve_resource_set(f"batch:{batch.id}").urns_for("QuestionItem") == {qi.urn}
    assert cv.urn in resolve_resource_set("bank:harmonized").all_urns
    assert qi.urn in resolve_resource_set("bank:imported").all_urns
    assert resolve_resource_set(f"urn:{qi.urn},{rv.urn}").all_urns == {qi.urn, rv.urn}


@pytest.mark.django_db
def test_cli_group_lifecycle() -> None:
    """Verify `fairwddi group` CLI create/list/show/add/remove/rename/delete workflow."""
    from fairwddi.cli import app
    from fairwddi.models import QuestionItem

    q = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_cli:1.0.0",
        name="Q_CLI",
        question_text={"fr": "Question test CLI"},
        origin="imported",
    )
    runner = CliRunner()
    c_res = runner.invoke(
        app, ["group", "create", "My CLI Group", "--slug", "cli-grp", "-m", q.urn]
    )
    assert c_res.exit_code == 0, c_res.output
    assert "cli-grp" in c_res.output

    l_res = runner.invoke(app, ["group", "list"])
    assert l_res.exit_code == 0
    assert "cli-grp" in l_res.output

    s_res = runner.invoke(app, ["group", "show", "cli-grp"])
    assert s_res.exit_code == 0
    assert q.urn in s_res.output

    d_res = runner.invoke(app, ["group", "delete", "cli-grp"])
    assert d_res.exit_code == 0
    with pytest.raises(ValueError):
        get_group_details("cli-grp")
