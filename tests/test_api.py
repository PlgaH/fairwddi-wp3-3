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
    assert "FAIRwDDI Question Bank & Harmonization Explorer" in html
    assert "cascade-canvas" in html
    assert "Code List Explorer" in html
    assert "Category Explorer" in html
    assert "btn-hist-back" in html
    assert "btn-hist-forward" in html
    assert "Code List URN" in html
    assert "Cross-Wave Harmonization Matrix" not in html
    assert "URN Alias Crosswalk" not in html
