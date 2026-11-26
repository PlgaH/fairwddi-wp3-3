"""Unit and integration tests for FAIRwDDI Ninja API & Web Explorer."""

from __future__ import annotations

from urllib.parse import quote

import pytest
from django.test import RequestFactory
from ninja.testing import TestClient

from fairwddi.api.router import api
from fairwddi.api.views import explorer_view


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(api)


@pytest.mark.django_db
def test_api_overview(api_client: TestClient) -> None:
    resp = api_client.get("/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "survey_count" in data
    assert "question_count" in data
    assert "reused_question_count" in data
    assert "alias_count" in data


@pytest.mark.django_db
def test_api_surveys(api_client: TestClient) -> None:
    resp = api_client.get("/surveys")
    assert resp.status_code == 200
    surveys = resp.json()
    assert isinstance(surveys, list)


@pytest.mark.django_db
def test_api_questions(api_client: TestClient) -> None:
    resp = api_client.get("/questions?limit=10")
    assert resp.status_code == 200
    questions = resp.json()
    assert isinstance(questions, list)
    if questions:
        q = questions[0]
        assert "urn" in q
        assert "text_display" in q
        assert "surveys" in q


@pytest.mark.django_db
def test_api_question_cascade(api_client: TestClient) -> None:
    from fairwddi.models import (
        Category,
        Code,
        CodeList,
        Datafile,
        InstanceVariable,
        QuestionItem,
        QuestionVariable,
        RepresentedVariable,
        StudyUnit,
        URNAlias,
    )

    qi = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_test_trust:1.0.0",
        name="Q1_TRUST",
        question_text={"fr": "Avez-vous confiance?", "en": "Do you trust?"},
    )
    cl = CodeList.objects.create(
        urn="urn:ddi:fr.cdsp:cl_test_trust:1.0.0",
        name="CL_TRUST",
    )
    cat = Category.objects.create(
        urn="urn:ddi:fr.cdsp:cat_yes:1.0.0",
        name="Yes",
        label={"fr": "Oui"},
    )
    Code.objects.create(
        urn="urn:ddi:fr.cdsp:code_yes:1.0.0",
        code_list=cl,
        category=cat,
        code_value="1",
        order=1,
    )
    rv = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_test_trust:1.0.0",
        name="RV_TRUST",
        code_list=cl,
    )
    QuestionVariable.objects.create(question_item=qi, represented_variable=rv, order=1)
    su = StudyUnit.objects.create(
        urn="urn:ddi:fr.cdsp:study_2013:1.0.0",
        name="ELIPSS 2013",
    )
    df = Datafile.objects.create(
        urn="urn:ddi:fr.cdsp:df_2013:1.0.0",
        study_unit=su,
        name="elipss2013.csv",
    )
    InstanceVariable.objects.create(
        urn="urn:ddi:fr.cdsp:iv_2013_q1:1.0.0",
        represented_variable=rv,
        datafile=df,
        name="q1_trust",
    )
    URNAlias.objects.create(
        alias_urn="urn:ddi:fr.cdsp:qi_2014_q1:1.0.0",
        canonical_urn=qi.urn,
        entity_type="QuestionItem",
        hash_strategy="content_hash",
    )

    q_urn = qi.urn
    resp = api_client.get(f"/questions/{quote(q_urn, safe='')}/cascade")
    assert resp.status_code == 200
    data = resp.json()
    assert data["question_urn"] == q_urn
    assert "nodes" in data
    assert "links" in data
    assert len(data["nodes"]) >= 3
    node_types = {n["type"] for n in data["nodes"]}
    assert "QuestionItem" in node_types
    assert "RepresentedVariable" in node_types
    assert "InstanceVariable" in node_types
    assert "URNAlias" in node_types
    assert "CodeList" in node_types
    qi_node = next(n for n in data["nodes"] if n["id"] == q_urn)
    assert qi_node["data"]["origin"] == "instantiated"

    # Verify CodeList node data contains codes & categories
    cl_node = next(n for n in data["nodes"] if n["type"] == "CodeList")
    assert cl_node["sublabel"] == "Code List"
    assert "codes" in cl_node["data"]
    assert len(cl_node["data"]["codes"]) == 1
    assert cl_node["data"]["codes"][0]["value"] == "1"
    assert cl_node["data"]["codes"][0]["label"] == "Oui"


@pytest.mark.django_db
def test_api_harmonization_matrix(api_client: TestClient) -> None:
    resp = api_client.get("/harmonization/matrix?limit=10")
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)


@pytest.mark.django_db
def test_api_aliases(api_client: TestClient) -> None:
    resp = api_client.get("/aliases?limit=10")
    assert resp.status_code == 200
    aliases = resp.json()
    assert isinstance(aliases, list)


@pytest.mark.django_db
def test_api_codelists(api_client: TestClient) -> None:
    from fairwddi.models import (
        Category,
        Code,
        CodeList,
        InstanceVariable,
        QuestionItem,
        QuestionVariable,
        RepresentedVariable,
    )

    cl = CodeList.objects.create(urn="urn:ddi:fr.cdsp:cl_test_unique:1.0.0", name="CL_Unique")
    cat = Category.objects.create(
        urn="urn:ddi:fr.cdsp:cat_test_unique:1.0.0",
        name="CatU",
        label={"fr": "Unique"},
    )
    Code.objects.create(
        urn="urn:ddi:fr.cdsp:code_test_unique:1.0.0",
        code_list=cl,
        category=cat,
        code_value="99",
    )
    rv = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_test_unique:1.0.0",
        name="RV_Unique",
        label={"fr": "Label RV"},
        code_list=cl,
    )
    qi = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_test_unique:1.0.0",
        name="QI_Unique",
        question_text={"fr": "Question texte ?"},
    )
    QuestionVariable.objects.create(
        question_item=qi,
        represented_variable=rv,
    )
    InstanceVariable.objects.create(
        urn="urn:ddi:fr.cdsp:iv_test_unique:1.0.0",
        name="VAR_COL_1",
        represented_variable=rv,
    )

    resp = api_client.get("/codelists?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["urn"] == cl.urn for item in data)

    # Test single-item retrieval
    single_resp = api_client.get(f"/codelists/{cl.urn}")
    assert single_resp.status_code == 200
    single_data = single_resp.json()
    assert single_data["urn"] == cl.urn
    assert single_data["code_count"] == 1
    assert single_data["codes"][0]["code_value"] == "99"
    assert len(single_data["represented_variables"]) == 1
    rv_item = single_data["represented_variables"][0]
    assert rv_item["urn"] == rv.urn
    assert rv_item["name"] == "RV_Unique"
    assert rv_item["question_urn"] == qi.urn
    assert rv_item["question_text"] == "Question texte ?"
    assert "VAR_COL_1" in rv_item["instance_variables"]


@pytest.mark.django_db
def test_api_categories(api_client: TestClient) -> None:
    from fairwddi.models import Category, Code, CodeList

    cat = Category.objects.create(
        urn="urn:ddi:fr.cdsp:cat_agree:1.0.0",
        name="CatAgree",
        label={"fr": "D'accord"},
    )
    cl = CodeList.objects.create(urn="urn:ddi:fr.cdsp:cl_agree:1.0.0", name="CL_Agree")
    Code.objects.create(
        urn="urn:ddi:fr.cdsp:code_agree:1.0.0",
        code_list=cl,
        category=cat,
        code_value="1",
    )

    resp = api_client.get("/categories?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["urn"] == cat.urn for item in data)

    # Test single-item retrieval
    single_resp = api_client.get(f"/categories/{cat.urn}")
    assert single_resp.status_code == 200
    single_data = single_resp.json()
    assert single_data["urn"] == cat.urn
    assert single_data["codelist_count"] == 1
    assert single_data["codelists"][0]["code_value"] == "1"


def test_explorer_html_view() -> None:
    rf = RequestFactory()
    req = rf.get("/explorer")
    resp = explorer_view(req)
    html = resp.content.decode("utf-8")
    assert resp.status_code == 200
    assert "FAIRwDDI Explorer" in html
    assert "cascade-canvas" in html
    assert ">Questions</button>" in html
    assert ">Variables</button>" in html
    assert ">Code Lists</button>" in html
    assert ">Categories</button>" in html
    assert "var-relation-svg" in html
    assert "setVariableTier" in html
    assert "Resources" in html
    assert "res-type-select" in html
    assert "Groups" in html
    assert "Import Batches" in html
    assert "Quarantine" in html
    assert "global-study-filter" in html
    assert "global-origin-filter" in html
    assert "global-batch-filter" not in html
    assert "btn-hist-back" in html
    assert "btn-hist-forward" in html
    assert "Code List URN" in html
    assert "Cross-Wave Harmonization Matrix" not in html
    assert "URN Alias Crosswalk" not in html


@pytest.mark.django_db
def test_api_groups_batches_and_quarantine(api_client: TestClient) -> None:
    from fairwddi.models import Group, IngestBatch, MetadataQuarantine

    Group.objects.create(
        urn="urn:ddi:fr.cdsp:grp_enef2024:1.0.0",
        slug="enef-2024",
        name={"en": "ENEF 2024"},
        group_type="series",
        references=[{"resource_type": "StudyUnit", "urn": "urn:ddi:fr.cdsp:study_1:1.0.0"}],
    )
    IngestBatch.objects.create(
        source_format="ddi-l:4.0:json",
        file_name="enef2024_v1.ddi40.json",
        file_sha256="a" * 64,
        status="completed",
        created_urns=["urn:ddi:fr.cdsp:study_1:1.0.0"],
        reused_urns=[],
    )
    MetadataQuarantine.objects.create(
        incoming_urn="urn:ddi:fr.cdsp:qi_1:1.0.0",
        existing_urn="urn:ddi:fr.cdsp:qi_1:1.0.0",
        entity_type="QuestionItem",
        existing_content_hash="b" * 64,
        incoming_content_hash="c" * 64,
        incoming_content={"urn": "urn:ddi:fr.cdsp:qi_1:1.0.0"},
        conflict_type="hash_mismatch",
        resolution=None,
        source_file="enef2024_v2.ddi40.json",
    )

    g_resp = api_client.get("/groups?q=enef-2024")
    assert g_resp.status_code == 200
    g_data = g_resp.json()
    assert len(g_data) == 1
    assert g_data[0]["slug"] == "enef-2024"
    assert g_data[0]["member_count"] == 1

    b_resp = api_client.get("/batches")
    assert b_resp.status_code == 200
    b_data = b_resp.json()
    assert any(
        b["file_name"] == "enef2024_v1.ddi40.json" and b["created_count"] == 1 for b in b_data
    )

    q_resp = api_client.get("/quarantine")
    assert q_resp.status_code == 200
    q_data = q_resp.json()
    assert len(q_data) == 1
    assert q_data[0]["incoming_urn"] == "urn:ddi:fr.cdsp:qi_1:1.0.0"


@pytest.mark.django_db
def test_api_global_study_and_batch_filters(api_client: TestClient) -> None:
    from fairwddi.models import (
        Category,
        CodeItem,
        CodeList,
        Datafile,
        DatafileVariable,
        IngestBatch,
        InstanceVariable,
        QuestionItem,
        QuestionVariable,
        RepresentedVariable,
        StudyUnit,
    )

    su1 = StudyUnit.objects.create(urn="urn:ddi:fr.cdsp:su_1:1.0.0", name={"en": "Study 1"})
    su2 = StudyUnit.objects.create(urn="urn:ddi:fr.cdsp:su_2:1.0.0", name={"en": "Study 2"})
    df1 = Datafile.objects.create(urn="urn:ddi:fr.cdsp:df_1:1.0.0", name="F1", study_unit=su1)
    df2 = Datafile.objects.create(urn="urn:ddi:fr.cdsp:df_2:1.0.0", name="F2", study_unit=su2)

    cat1 = Category.objects.create(urn="urn:ddi:fr.cdsp:cat_1:1.0.0", name={"en": "Yes"})
    cl1 = CodeList.objects.create(urn="urn:ddi:fr.cdsp:cl_1:1.0.0", name={"en": "YN"})
    CodeItem.objects.create(code_list=cl1, category=cat1, code_value="1")

    q1 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_1:1.0.0",
        name={"en": "Q1"},
        question_text={"en": "Vote?"},
    )
    rv1 = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_1:1.0.0",
        name={"en": "RV1"},
        code_list=cl1,
    )
    QuestionVariable.objects.create(question_item=q1, represented_variable=rv1)
    iv1 = InstanceVariable.objects.create(
        urn="urn:ddi:fr.cdsp:iv_1:1.0.0",
        name={"en": "V1"},
        represented_variable=rv1,
    )
    DatafileVariable.objects.create(datafile=df1, instance_variable=iv1)

    q2 = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_2:1.0.0",
        name={"en": "Q2"},
        question_text={"en": "Age?"},
    )
    rv2 = RepresentedVariable.objects.create(urn="urn:ddi:fr.cdsp:rv_2:1.0.0", name={"en": "RV2"})
    QuestionVariable.objects.create(question_item=q2, represented_variable=rv2)
    iv2 = InstanceVariable.objects.create(
        urn="urn:ddi:fr.cdsp:iv_2:1.0.0",
        name={"en": "V2"},
        represented_variable=rv2,
    )
    DatafileVariable.objects.create(datafile=df2, instance_variable=iv2)

    b1 = IngestBatch.objects.create(
        source_format="ddi-l:4.0:json",
        file_name="s1.json",
        file_sha256="1" * 64,
        status="completed",
        created_urns=[su1.urn, q1.urn, cl1.urn, cat1.urn, iv1.urn],
    )

    ov_su1 = api_client.get(f"/overview?study_urn={su1.urn}").json()
    assert ov_su1["survey_count"] == 1
    assert ov_su1["question_count"] == 1
    assert ov_su1["codelist_count"] == 1
    assert ov_su1["category_count"] == 1

    q_su1 = api_client.get(f"/questions?study_urn={su1.urn}").json()
    assert [item["urn"] for item in q_su1] == [q1.urn]

    q_b1 = api_client.get(f"/questions?batch_id={b1.id}").json()
    assert [item["urn"] for item in q_b1] == [q1.urn]

    cl_b1 = api_client.get(f"/codelists?batch_id={b1.id}").json()
    assert [item["urn"] for item in cl_b1] == [cl1.urn]

    cat_su1 = api_client.get(f"/categories?study_urn={su1.urn}").json()
    assert [item["urn"] for item in cat_su1] == [cat1.urn]


@pytest.mark.django_db
def test_api_variable_explorer_endpoints(api_client: TestClient) -> None:
    from fairwddi.models import (
        Category,
        CodeItem,
        CodeList,
        Concept,
        ConceptualVariable,
        Datafile,
        DatafileVariable,
        DatafileVariableFrequency,
        InstanceVariable,
        QuestionItem,
        QuestionVariable,
        RepresentedVariable,
        SemanticRelationship,
        StudyUnit,
    )

    concept = Concept.objects.create(
        urn="urn:ddi:elsst:pol_interest:1.0.0",
        label={"en": "POLITICAL INTEREST"},
        uri="https://elsst.cessda.eu/id/4/pol_interest",
        vocabulary="ELSST",
    )
    cv = ConceptualVariable.objects.create(
        urn="urn:ddi:fr.cdsp:cv_pol:1.0.0",
        name={"en": "Political Interest"},
        concept=concept,
    )
    cat = Category.objects.create(urn="urn:ddi:fr.cdsp:cat_high:1.0.0", name={"en": "High"})
    cl = CodeList.objects.create(urn="urn:ddi:fr.cdsp:cl_pol:1.0.0", name={"en": "Interest Scale"})
    CodeItem.objects.create(code_list=cl, category=cat, code_value="1")

    rv = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_pol:1.0.0",
        name={"en": "RV_PolInterest"},
        conceptual_variable=cv,
        code_list=cl,
    )
    qi = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:qi_pol:1.0.0",
        name={"en": "Q_Pol"},
        question_text={"en": "How interested are you in politics?"},
    )
    QuestionVariable.objects.create(question_item=qi, represented_variable=rv)

    su = StudyUnit.objects.create(urn="urn:ddi:fr.cdsp:su_pol:1.0.0", name={"en": "ENEF 2024"})
    df = Datafile.objects.create(urn="urn:ddi:fr.cdsp:df_pol:1.0.0", name="enef.csv", study_unit=su)
    iv = InstanceVariable.objects.create(
        urn="urn:ddi:fr.cdsp:iv_pol:1.0.0",
        name={"en": "Y1INTPOL"},
        represented_variable=rv,
    )
    DatafileVariable.objects.create(
        datafile=df,
        instance_variable=iv,
        order=1,
        statistics={"mean": 2.4, "valid_cases": 500},
    )
    DatafileVariableFrequency.objects.create(
        datafile=df,
        instance_variable=iv,
        code_value="1",
        frequency=250.0,
    )
    rv_other = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_other:1.0.0",
        name={"en": "RV_Other"},
    )
    SemanticRelationship.objects.create(
        subject_urn=rv.urn,
        subject_type="RepresentedVariable",
        predicate="skos:closeMatch",
        object_urn=rv_other.urn,
        object_type="RepresentedVariable",
        extended_attributes=[{"type": "correspondence_level", "value": "semantic"}],
    )

    rv_list = api_client.get(f"/variables/represented?study_urn={su.urn}").json()
    assert len(rv_list) == 1
    assert rv_list[0]["urn"] == rv.urn
    assert rv_list[0]["conceptual_variable_urn"] == cv.urn
    assert len(rv_list[0]["semantic_links"]) == 1

    iv_detail = api_client.get(f"/variables/instance/{iv.urn}").json()
    assert iv_detail["urn"] == iv.urn
    assert iv_detail["has_statistics"] is True
    assert iv_detail["occurrences"][0]["statistics"]["mean"] == 2.4
    assert iv_detail["occurrences"][0]["frequencies"][0]["category_label"] == "High"

    cv_detail = api_client.get(f"/variables/conceptual/{cv.urn}").json()
    assert cv_detail["urn"] == cv.urn
    assert cv_detail["concept_uri"] == "https://elsst.cessda.eu/id/4/pol_interest"
    assert cv_detail["represented_count"] == 1

    types_resp = api_client.get("/resources/types").json()
    assert any(t["resource_type"] == "StudyUnit" and t["count"] >= 1 for t in types_resp)

    su_list = api_client.get("/resources?resource_type=StudyUnit").json()
    assert any(r["urn"] == su.urn for r in su_list)

    su_detail = api_client.get(f"/resources/{su.urn}").json()
    assert su_detail["urn"] == su.urn
    assert su_detail["resource_type"] == "StudyUnit"
    assert su_detail["name"] == "ENEF 2024"

    gen_res = api_client.get("/resources?origin=instantiated&resource_type=StudyUnit").json()
    assert any(r["urn"] == su.urn for r in gen_res)
    imp_res = api_client.get("/resources?origin=imported&resource_type=StudyUnit").json()
    assert imp_res == []


@pytest.mark.django_db
def test_api_question_reuse_any_level(api_client: TestClient) -> None:
    """QuestionItem linked to >1 RepresentedVariable is treated as reused even within one study."""
    from fairwddi.models import QuestionItem, QuestionVariable, RepresentedVariable

    qi = QuestionItem.objects.create(
        urn="urn:ddi:fr.cdsp:q_shared:1.0.0",
        name="q_shared",
        question_text={"fr": "Question partagée"},
    )
    rv1 = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_1:1.0.0",
        name="rv_1",
    )
    rv2 = RepresentedVariable.objects.create(
        urn="urn:ddi:fr.cdsp:rv_2:1.0.0",
        name="rv_2",
    )
    QuestionVariable.objects.create(question_item=qi, represented_variable=rv1)
    QuestionVariable.objects.create(question_item=qi, represented_variable=rv2)

    resp = api_client.get("/questions?reused_only=true")
    assert resp.status_code == 200
    items = resp.json()
    match = [x for x in items if x["urn"] == qi.urn]
    assert len(match) == 1
    assert match[0]["is_reused"] is True
