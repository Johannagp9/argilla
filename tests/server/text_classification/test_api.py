#  coding=utf-8
#  Copyright 2021-present, the Recognai S.L. team.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from datetime import datetime

import pytest
from argilla.server.apis.v0.models.commons.model import BulkResponse
from argilla.server.apis.v0.models.text_classification import (
    TextClassificationAnnotation,
    TextClassificationBulkRequest,
    TextClassificationQuery,
    TextClassificationRecord,
    TextClassificationSearchRequest,
    TextClassificationSearchResults,
)
from argilla.server.commons.models import PredictionStatus
from argilla.server.schemas.datasets import Dataset

from tests.client.conftest import SUPPORTED_VECTOR_SEARCH


def test_create_records_for_text_classification_with_multi_label(mocked_client):
    dataset = "test_create_records_for_text_classification_with_multi_label"
    assert mocked_client.delete(f"/api/datasets/{dataset}").status_code == 200

    records = [
        TextClassificationRecord.parse_obj(data)
        for data in [
            {
                "id": 0,
                "inputs": {"data": "my data"},
                "multi_label": True,
                "metadata": {
                    "field_one": "value one",
                    "field_two": "value 2",
                    "one_more": [{"a": 1, "b": 2}],
                },
                "prediction": {
                    "agent": "testA",
                    "labels": [
                        {"class": "Test", "score": 0.6},
                        {"class": "Mocking", "score": 0.7},
                        {"class": "NoClass", "score": 0.2},
                    ],
                },
            },
            {
                "id": 1,
                "inputs": {"data": "my data"},
                "multi_label": True,
                "metadata": {
                    "field_one": "another value one",
                    "field_two": "value 2",
                },
                "prediction": {
                    "agent": "testB",
                    "labels": [
                        {"class": "Test", "score": 0.6},
                        {"class": "Mocking", "score": 0.7},
                        {"class": "NoClass", "score": 0.2},
                    ],
                },
            },
        ]
    ]
    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:bulk",
        json=TextClassificationBulkRequest(
            tags={"env": "test", "class": "text classification"},
            metadata={"config": {"the": "config"}},
            records=records,
        ).dict(by_alias=True),
    )

    assert response.status_code == 200, response.json()
    bulk_response = BulkResponse.parse_obj(response.json())
    assert bulk_response.dataset == dataset
    assert bulk_response.failed == 0
    assert bulk_response.processed == 2

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:bulk",
        json=TextClassificationBulkRequest(
            tags={"new": "tag"},
            metadata={"new": {"metadata": "value"}},
            records=records,
        ).dict(by_alias=True),
    )

    get_dataset = Dataset.parse_obj(mocked_client.get(f"/api/datasets/{dataset}").json())
    assert get_dataset.tags == {
        "env": "test",
        "class": "text classification",
        "new": "tag",
    }
    assert get_dataset.metadata == {
        "config": {"the": "config"},
        "new": {"metadata": "value"},
    }

    assert response.status_code == 200, response.json()

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search",
        json={},
    )

    assert response.status_code == 200
    results = TextClassificationSearchResults.parse_obj(response.json())
    assert results.total == 2
    assert results.aggregations.predicted_as == {"Mocking": 2, "Test": 2}
    assert results.records[0].predicted is None

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search",
        json={"query": {"predicted_by": ["testA"]}},
    )
    assert response.status_code == 200, response.json()
    results = TextClassificationSearchResults.parse_obj(response.json())
    assert results.total == len(results.records) == 1
    assert results.aggregations.predicted_by == {"testA": 1}


def test_create_records_for_text_classification(mocked_client, telemetry_track_data):
    dataset = "test_create_records_for_text_classification"
    assert mocked_client.delete(f"/api/datasets/{dataset}").status_code == 200
    tags = {"env": "test", "class": "text classification"}
    metadata = {"config": {"the": "config"}}
    classification_bulk = TextClassificationBulkRequest(
        tags=tags,
        metadata=metadata,
        records=[
            TextClassificationRecord(
                **{
                    "id": 0,
                    "inputs": {"data": "my data"},
                    "prediction": {
                        "agent": "test",
                        "labels": [
                            {"class": "Test", "score": 0.3},
                            {"class": "Mocking", "score": 0.7},
                        ],
                    },
                }
            )
        ],
    )
    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:bulk",
        json=classification_bulk.dict(by_alias=True),
    )

    assert response.status_code == 200
    bulk_response = BulkResponse.parse_obj(response.json())
    assert bulk_response.dataset == dataset
    assert bulk_response.failed == 0
    assert bulk_response.processed == 1

    response = mocked_client.get(f"/api/datasets/{dataset}")
    assert response.status_code == 200
    created_dataset = Dataset.parse_obj(response.json())
    assert created_dataset.tags == tags
    assert created_dataset.metadata == metadata

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search",
        json={},
    )

    assert response.status_code == 200
    results = TextClassificationSearchResults.parse_obj(response.json())
    assert results.total == 1
    assert results.aggregations.dict(exclude={"score"}) == {
        "annotated_as": {},
        "annotated_by": {},
        "metadata": {},
        "predicted": {},
        "predicted_as": {"Mocking": 1},
        "predicted_by": {"test": 1},
        "status": {"Default": 1},
        "words": {"data": 1},
    }

    telemetry_track_data.assert_called_once()


@pytest.mark.skipif(
    condition=not SUPPORTED_VECTOR_SEARCH,
    reason="Vector search not supported",
)
def test_create_records_for_text_classification_vector_search(mocked_client, telemetry_track_data):
    dataset = "test_create_records_for_text_classification_vector_search"
    assert mocked_client.delete(f"/api/datasets/{dataset}").status_code == 200
    tags = {"env": "test", "class": "text classification"}
    metadata = {"config": {"the": "config"}}
    classification_bulk = TextClassificationBulkRequest(
        tags=tags,
        metadata=metadata,
        records=[
            TextClassificationRecord(**a)
            for a in [
                {
                    "id": 0,
                    "inputs": {"data": "my data"},
                    "prediction": {
                        "agent": "test",
                        "labels": [
                            {"class": "Test", "score": 0.3},
                            {"class": "Mocking", "score": 0.7},
                        ],
                    },
                    "vectors": {"my_bert": {"value": [10, 11, 12, 13]}},
                },
                {
                    "id": 1,
                    "inputs": {"data": "your data"},
                    "prediction": {
                        "agent": "test",
                        "labels": [
                            {"class": "Test", "score": 0.35},
                            {"class": "Mocking", "score": 0.65},
                        ],
                    },
                    "vectors": {"my_bert": {"value": [14, 15, 16, 17]}},
                },
                {
                    "id": 2,
                    "inputs": {"data": "their data"},
                    "prediction": {
                        "agent": "test",
                        "labels": [
                            {"class": "Test", "score": 0.4},
                            {"class": "Mocking", "score": 0.6},
                        ],
                    },
                    "vectors": {"my_bert": {"value": [14, 15, 16, 18]}},
                },
            ]
        ],
    )
    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:bulk",
        json=classification_bulk.dict(by_alias=True),
    )

    assert response.status_code == 200
    bulk_response = BulkResponse.parse_obj(response.json())
    assert bulk_response.dataset == dataset
    assert bulk_response.failed == 0
    assert bulk_response.processed == 3

    response = mocked_client.get(f"/api/datasets/{dataset}")
    assert response.status_code == 200
    created_dataset = Dataset.parse_obj(response.json())
    assert created_dataset.tags == tags
    assert created_dataset.metadata == metadata

    response = mocked_client.post(f"/api/datasets/{dataset}/TextClassification:search", json={})

    assert response.status_code == 200
    results = TextClassificationSearchResults.parse_obj(response.json())
    assert results.total == 3
    assert all(hasattr(record, "vectors") for record in results.records)
    assert results.aggregations.dict(exclude={"score"}) == {
        "annotated_as": {},
        "annotated_by": {},
        "metadata": {},
        "predicted": {},
        "predicted_as": {"Mocking": 3},
        "predicted_by": {"test": 3},
        "status": {"Default": 3},
        "words": {"data": 3},
    }

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search",
        json={
            "query": {
                "vector": {
                    "name": "my_bert",
                    "value": [14, 15, 16, 17],
                },
            }
        },
    )
    assert response.status_code == 200
    results = TextClassificationSearchResults.parse_obj(response.json())
    assert results.total == 3
    assert all(hasattr(record, "vectors") for record in results.records)
    assert [record.id for record in results.records] == [
        1,
        2,
        0,
    ]  ## similarity ordered records


def test_partial_record_update(mocked_client):
    name = "test_partial_record_update"
    assert mocked_client.delete(f"/api/datasets/{name}").status_code == 200

    record = TextClassificationRecord(
        **{
            "id": 1,
            "inputs": {"text": "This is a text, oh yeah!"},
            "prediction": {
                "agent": "test",
                "labels": [
                    {"class": "Positive", "score": 0.6},
                    {"class": "Negative", "score": 0.3},
                    {"class": "Other", "score": 0.1},
                ],
            },
        }
    )

    bulk = TextClassificationBulkRequest(
        records=[record],
    )

    response = mocked_client.post(
        f"/api/datasets/{name}/TextClassification:bulk",
        json=bulk.dict(by_alias=True),
    )

    assert response.status_code == 200, response.json()
    bulk_response = BulkResponse.parse_obj(response.json())
    assert bulk_response.failed == 0
    assert bulk_response.processed == 1

    record.annotation = TextClassificationAnnotation.parse_obj(
        {
            "agent": "gold_standard",
            "labels": [{"class": "Positive"}],
        }
    )

    bulk.records = [record]

    mocked_client.post(
        f"/api/datasets/{name}/TextClassification:bulk",
        json=bulk.dict(by_alias=True),
    )

    response = mocked_client.post(
        f"/api/datasets/{name}/TextClassification:search",
        json={
            "query": TextClassificationQuery(predicted=PredictionStatus.OK).dict(by_alias=True),
        },
    )

    assert response.status_code == 200
    results = TextClassificationSearchResults.parse_obj(response.json())
    assert results.total == 1
    first_record = results.records[0]
    assert first_record.last_updated is not None
    first_record.last_updated = None
    assert TextClassificationRecord(**first_record.dict(by_alias=True, exclude_none=True)) == TextClassificationRecord(
        **{
            "id": 1,
            "inputs": {"text": "This is a text, oh yeah!"},
            "prediction": {
                "agent": "test",
                "labels": [
                    {"class": "Positive", "score": 0.6},
                    {"class": "Negative", "score": 0.3},
                    {"class": "Other", "score": 0.1},
                ],
            },
            "annotation": {
                "agent": "gold_standard",
                "labels": [{"class": "Positive"}],
            },
        }
    )


def test_sort_by_last_updated(mocked_client):
    dataset = "test_sort_by_last_updated"
    assert mocked_client.delete(f"/api/datasets/{dataset}").status_code == 200
    for i in range(0, 10):
        mocked_client.post(
            f"/api/datasets/{dataset}/TextClassification:bulk",
            json=TextClassificationBulkRequest(
                records=[
                    TextClassificationRecord(
                        **{
                            "id": i,
                            "inputs": {"data": "my data"},
                            "metadata": {"s": "value"},
                        }
                    )
                ],
            ).dict(by_alias=True),
        )

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search?from=0&limit=10",
        json={"sort": [{"id": "last_updated", "order": "asc"}]},
    )

    assert [r["id"] for r in response.json()["records"]] == list(range(0, 10))


def test_sort_by_id_as_default(mocked_client):
    dataset = "test_sort_by_id_as_default"
    assert mocked_client.delete(f"/api/datasets/{dataset}").status_code == 200
    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:bulk",
        json=TextClassificationBulkRequest(
            records=[
                TextClassificationRecord(
                    **{
                        "id": i,
                        "inputs": {"data": "my data"},
                        "metadata": {"s": "value"},
                    }
                )
                for i in range(0, 100)
            ],
        ).dict(by_alias=True),
    )
    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search?from=0&limit=10",
        json={},
    )

    results = TextClassificationSearchResults.parse_obj(response.json())
    assert results.total == 100
    assert list(map(lambda r: r.id, results.records)) == [
        0,
        1,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
    ]


def test_some_sort_by(mocked_client):
    dataset = "test_some_sort_by"

    expected_records_length = 50
    assert mocked_client.delete(f"/api/datasets/{dataset}").status_code == 200
    mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:bulk",
        json=TextClassificationBulkRequest(
            records=[
                TextClassificationRecord(
                    **{
                        "id": i,
                        "inputs": {"data": "my data"},
                        "prediction": {"agent": f"agent_{i%5}", "labels": []},
                        "metadata": {
                            "s": f"{i} value",
                        },
                    }
                )
                for i in range(0, expected_records_length)
            ],
        ).dict(by_alias=True),
    )
    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search?from=0&limit=10",
        json={
            "sort": [
                {"id": "wrong_field"},
            ]
        },
    )

    assert response.status_code == 400
    expected_response_property_name_2_value = {
        "detail": {
            "code": "argilla.api.errors::BadRequestError",
            "params": {
                "message": "Wrong sort id wrong_field. Valid values "
                "are: ['id', 'metadata', 'score', "
                "'predicted', 'predicted_as', "
                "'predicted_by', 'annotated_as', "
                "'annotated_by', 'status', 'last_updated', "
                "'event_timestamp']"
            },
        }
    }
    assert response.json()["detail"]["code"] == expected_response_property_name_2_value["detail"]["code"]
    assert (
        response.json()["detail"]["params"]["message"]
        == expected_response_property_name_2_value["detail"]["params"]["message"]
    )
    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search?from=0&limit=10",
        json={
            "sort": [
                {"id": "predicted_by", "order": "desc"},
                {"id": "metadata.s", "order": "asc"},
            ]
        },
    )

    results = TextClassificationSearchResults.parse_obj(response.json())
    assert results.total == expected_records_length
    assert list(map(lambda r: r.id, results.records)) == [
        14,
        19,
        24,
        29,
        34,
        39,
        4,
        44,
        49,
        9,
    ]


def test_disable_aggregations_when_scroll(mocked_client):
    dataset = "test_disable_aggregations_when_scroll"
    assert mocked_client.delete(f"/api/datasets/{dataset}").status_code == 200

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:bulk",
        json=TextClassificationBulkRequest(
            tags={"env": "test", "class": "text classification"},
            metadata={"config": {"the": "config"}},
            records=[
                TextClassificationRecord(
                    **{
                        "id": i,
                        "inputs": {"data": "my data"},
                        "prediction": {
                            "agent": "test",
                            "labels": [
                                {"class": "Test", "score": 0.3},
                                {"class": "Mocking", "score": 0.7},
                            ],
                        },
                    }
                )
                for i in range(0, 100)
            ],
        ).dict(by_alias=True),
    )
    bulk_response = BulkResponse.parse_obj(response.json())
    assert bulk_response.processed == 100

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search?from=10",
        json={},
    )

    results = TextClassificationSearchResults.parse_obj(response.json())
    assert results.total == 100
    assert results.aggregations is None


def test_include_event_timestamp(mocked_client):
    dataset = "test_include_event_timestamp"
    assert mocked_client.delete(f"/api/datasets/{dataset}").status_code == 200

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:bulk",
        data=TextClassificationBulkRequest(
            tags={"env": "test", "class": "text classification"},
            metadata={"config": {"the": "config"}},
            records=[
                TextClassificationRecord(
                    **{
                        "id": i,
                        "inputs": {"data": "my data"},
                        "event_timestamp": datetime.utcnow(),
                        "prediction": {
                            "agent": "test",
                            "labels": [
                                {"class": "Test", "score": 0.3},
                                {"class": "Mocking", "score": 0.7},
                            ],
                        },
                    }
                )
                for i in range(0, 100)
            ],
        ).json(by_alias=True),
    )
    bulk_response = BulkResponse.parse_obj(response.json())
    assert bulk_response.processed == 100

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search?from=10",
        json={},
    )

    results = TextClassificationSearchResults.parse_obj(response.json())
    assert results.total == 100
    assert all(map(lambda record: record.event_timestamp is not None, results.records))


def test_words_cloud(mocked_client):
    dataset = "test_language_detection"
    assert mocked_client.delete(f"/api/datasets/{dataset}").status_code == 200

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:bulk",
        data=TextClassificationBulkRequest(
            records=[
                TextClassificationRecord(
                    **{
                        "id": 0,
                        "inputs": {"text": "Esto es un ejemplo de texto"},
                    }
                ),
                TextClassificationRecord(
                    **{
                        "id": 1,
                        "inputs": {"text": "This is an simple text example"},
                    }
                ),
                TextClassificationRecord(
                    **{
                        "id": 2,
                        "inputs": {"text": "C'est nes pas une pipe"},
                    }
                ),
            ],
        ).json(by_alias=True),
    )
    BulkResponse.parse_obj(response.json())

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search",
        json={},
    )

    results = TextClassificationSearchResults.parse_obj(response.json())
    assert results.aggregations.words is not None


def test_metadata_with_point_in_field_name(mocked_client):
    dataset = "test_metadata_with_point_in_field_name"
    assert mocked_client.delete(f"/api/datasets/{dataset}").status_code == 200

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:bulk",
        data=TextClassificationBulkRequest(
            records=[
                TextClassificationRecord(
                    **{
                        "id": 0,
                        "inputs": {"text": "Esto es un ejemplo de texto"},
                        "metadata": {"field.one": 1, "field.two": 2},
                    }
                ),
                TextClassificationRecord(
                    **{
                        "id": 1,
                        "inputs": {"text": "This is an simple text example"},
                        "metadata": {"field.one": 1, "field.two": 2},
                    }
                ),
            ],
        ).json(by_alias=True),
    )

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search?limit=0",
        json={},
    )

    results = TextClassificationSearchResults.parse_obj(response.json())
    assert "field.one" in results.aggregations.metadata
    assert results.aggregations.metadata.get("field.one", {})["1"] == 2
    assert results.aggregations.metadata.get("field.two", {})["2"] == 2


def test_wrong_text_query(mocked_client):
    dataset = "test_wrong_text_query"
    assert mocked_client.delete(f"/api/datasets/{dataset}").status_code == 200

    mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:bulk",
        data=TextClassificationBulkRequest(
            records=[
                TextClassificationRecord(
                    **{
                        "id": 0,
                        "inputs": {"text": "Esto es un ejemplo de texto"},
                        "metadata": {"field.one": 1, "field.two": 2},
                    }
                ),
            ],
        ).json(by_alias=True),
    )

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search",
        json=TextClassificationSearchRequest(query=TextClassificationQuery(query_text="!")).dict(),
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": {
            "code": "argilla.api.errors::InvalidTextSearchError",
            "params": {"message": "Failed to parse query [!]"},
        }
    }


def test_search_using_text(mocked_client):
    dataset = "test_search_using_text"
    assert mocked_client.delete(f"/api/datasets/{dataset}").status_code == 200

    mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:bulk",
        data=TextClassificationBulkRequest(
            records=[
                TextClassificationRecord(
                    **{
                        "id": 0,
                        "inputs": {"data": "Esto es un ejemplo de Texto"},
                        "metadata": {"field.one": 1, "field.two": 2},
                    }
                ),
            ],
        ).json(by_alias=True),
    )

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search",
        json=TextClassificationSearchRequest(query=TextClassificationQuery(query_text="text: texto")).dict(),
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = mocked_client.post(
        f"/api/datasets/{dataset}/TextClassification:search",
        json=TextClassificationSearchRequest(query=TextClassificationQuery(query_text="text.exact: texto")).dict(),
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0
