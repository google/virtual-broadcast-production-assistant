import os
import pytest
from app.models import Service, Source, Flow, FlowSegmentPost, WebhookPost, StorageAllocationRequest

# ----------------- TESTS FOR ROOT ENDPOINT -----------------

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == ["service", "flows", "sources", "flow-delete-requests"]


# ----------------- TESTS FOR SERVICE ENDPOINT -----------------

def test_get_service_default(client, mock_db):
    # Verify starting with an empty database
    info_ref = mock_db.collection("service").document("info")
    assert not info_ref.get().exists

    response = client.get("/service")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TAMS GCP Service"
    assert data["type"] == "urn:x-tams:service.gcp"
    assert data["api_version"] == "8.0"

    # Verify that default data was written to Firestore
    assert info_ref.get().exists
    assert info_ref.get().to_dict()["name"] == "TAMS GCP Service"


def test_get_service_existing(client, mock_db):
    custom_info = {
        "name": "Custom TAMS Service",
        "description": "Custom Description",
        "type": "urn:x-tams:service.custom",
        "api_version": "9.0",
        "service_version": "1.0.0",
        "event_stream_mechanisms": [{"name": "webhooks"}],
        "min_object_timeout": "300:0",
        "min_presigned_url_timeout": "30:0"
    }
    mock_db.collection("service").document("info").set(custom_info)

    response = client.get("/service")
    assert response.status_code == 200
    assert response.json() == custom_info


def test_post_service(client, mock_db):
    # Set initial service data
    initial_info = {
        "name": "Initial Name",
        "description": "Initial Desc",
        "type": "urn:x-tams:service.gcp",
        "api_version": "8.0",
        "min_object_timeout": "300:0"
    }
    info_ref = mock_db.collection("service").document("info")
    info_ref.set(initial_info)

    # Post update
    update_payload = {"name": "Updated Name", "description": "Updated Desc"}
    response = client.post("/service", json=update_payload)
    assert response.status_code == 200
    assert response.json() == {"message": "Service info updated"}

    # Verify update in Firestore
    updated_doc = info_ref.get().to_dict()
    assert updated_doc["name"] == "Updated Name"
    assert updated_doc["description"] == "Updated Desc"
    assert updated_doc["type"] == "urn:x-tams:service.gcp" # Preserved


def test_post_service_no_updates(client, mock_db):
    response = client.post("/service", json={})
    assert response.status_code == 200
    assert response.json() == {"message": "No updates provided"}


# ----------------- TESTS FOR SOURCES ENDPOINTS -----------------

def test_get_sources_empty(client):
    response = client.get("/sources")
    assert response.status_code == 200
    assert response.json() == []


def test_get_sources_and_get_source(client, mock_db):
    source_data_1 = {
        "id": "source-1",
        "format": "urn:x-tams:format.video",
        "label": "Source One",
        "description": "First test source"
    }
    source_data_2 = {
        "id": "source-2",
        "format": "urn:x-tams:format.audio",
        "label": "Source Two",
        "description": "Second test source"
    }
    mock_db.collection("sources").document("source-1").set(source_data_1)
    mock_db.collection("sources").document("source-2").set(source_data_2)

    # Get sources list
    response = client.get("/sources?limit=1")
    assert response.status_code == 200
    # Since map order might differ, just verify length 1
    assert len(response.json()) == 1

    # Get specific source
    response = client.get("/sources/source-1")
    assert response.status_code == 200
    assert response.json() == source_data_1

    # Non-existent source
    response = client.get("/sources/source-nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "Source not found"}


def test_put_and_delete_source_label(client, mock_db):
    source_id = "src-label-test"
    mock_db.collection("sources").document(source_id).set({
        "id": source_id,
        "format": "urn:x-tams:format.video",
        "label": "Old Label"
    })

    # Put new label
    response = client.put(f"/sources/{source_id}/label", json="Brand New Label")
    assert response.status_code == 204
    assert mock_db.collection("sources").document(source_id).get().to_dict()["label"] == "Brand New Label"

    # Put label for non-existent source
    response = client.put("/sources/nonexistent/label", json="Label")
    assert response.status_code == 404

    # Delete label
    response = client.delete(f"/sources/{source_id}/label")
    assert response.status_code == 204
    assert "label" not in mock_db.collection("sources").document(source_id).get().to_dict()

    # Delete label for non-existent source
    response = client.delete("/sources/nonexistent/label")
    assert response.status_code == 404


def test_put_and_delete_source_description(client, mock_db):
    source_id = "src-desc-test"
    mock_db.collection("sources").document(source_id).set({
        "id": source_id,
        "format": "urn:x-tams:format.video",
        "description": "Old Description"
    })

    # Put description
    response = client.put(f"/sources/{source_id}/description", json="New Description")
    assert response.status_code == 204
    assert mock_db.collection("sources").document(source_id).get().to_dict()["description"] == "New Description"

    # Put for non-existent
    response = client.put("/sources/nonexistent/description", json="Description")
    assert response.status_code == 404

    # Delete description
    response = client.delete(f"/sources/{source_id}/description")
    assert response.status_code == 204
    assert "description" not in mock_db.collection("sources").document(source_id).get().to_dict()

    # Delete for non-existent
    response = client.delete("/sources/nonexistent/description")
    assert response.status_code == 404


def test_put_and_delete_source_tags(client, mock_db):
    source_id = "src-tags-test"
    mock_db.collection("sources").document(source_id).set({
        "id": source_id,
        "format": "urn:x-tams:format.video",
        "tags": {"existing_tag": "existing_val"}
    })

    # Put tag
    response = client.put(f"/sources/{source_id}/tags/custom_tag", json="custom_val")
    assert response.status_code == 204
    updated_doc = mock_db.collection("sources").document(source_id).get().to_dict()
    assert updated_doc["tags"]["custom_tag"] == "custom_val"
    assert updated_doc["tags"]["existing_tag"] == "existing_val"

    # Put tag on non-existent source
    response = client.put("/sources/nonexistent/tags/tag", json="val")
    assert response.status_code == 404

    # Delete tag
    response = client.delete(f"/sources/{source_id}/tags/custom_tag")
    assert response.status_code == 204
    updated_doc_2 = mock_db.collection("sources").document(source_id).get().to_dict()
    assert "custom_tag" not in updated_doc_2["tags"]
    assert updated_doc_2["tags"]["existing_tag"] == "existing_val"

    # Delete tag on non-existent source
    response = client.delete("/sources/nonexistent/tags/tag")
    assert response.status_code == 404


# ----------------- TESTS FOR FLOWS ENDPOINTS -----------------

def test_get_flows_empty(client):
    response = client.get("/flows")
    assert response.status_code == 200
    assert response.json() == []


def test_get_flows_and_get_flow(client, mock_db):
    flow_data = {
        "id": "flow-1",
        "source_id": "source-1",
        "format": "urn:x-tams:format.video",
        "label": "Flow One"
    }
    mock_db.collection("flows").document("flow-1").set(flow_data)

    response = client.get("/flows")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get("/flows/flow-1")
    assert response.status_code == 200
    assert response.json() == flow_data

    response = client.get("/flows/flow-nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "Flow not found"}


def test_put_flow_create_and_update(client, mock_db):
    # Ensure source does not exist
    source_ref = mock_db.collection("sources").document("source-auto")
    assert not source_ref.get().exists

    flow_payload = {
        "id": "flow-auto",
        "source_id": "source-auto",
        "format": "urn:x-tams:format.video",
        "label": "Auto Flow"
    }

    # PUT to create a flow (where its source doesn't exist)
    response = client.put("/flows/flow-auto", json=flow_payload)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["id"] == "flow-auto"
    assert "created" in res_data
    assert "metadata_updated" in res_data

    # Verify that the parent source was automatically created
    assert source_ref.get().exists
    created_source = source_ref.get().to_dict()
    assert created_source["id"] == "source-auto"
    assert created_source["format"] == "urn:x-tams:format.video"
    assert created_source["label"] == "Auto-created Source for Flow flow-auto"

    # PUT again to update the flow
    update_payload = {
        "id": "flow-auto",
        "source_id": "source-auto",
        "format": "urn:x-tams:format.video",
        "label": "Auto Flow Updated"
    }
    response = client.put("/flows/flow-auto", json=update_payload)
    assert response.status_code == 204

    # Verify flow updated in Firestore
    flow_doc = mock_db.collection("flows").document("flow-auto").get().to_dict()
    assert flow_doc["label"] == "Auto Flow Updated"
    assert flow_doc["metadata_updated"] is not None


def test_delete_flow(client, mock_db):
    mock_db.collection("flows").document("flow-1").set({
        "id": "flow-1",
        "source_id": "source-1",
        "format": "urn:x-tams:format.video"
    })

    # Delete existing flow
    response = client.delete("/flows/flow-1")
    assert response.status_code == 204
    assert not mock_db.collection("flows").document("flow-1").get().exists

    # Delete non-existent flow
    response = client.delete("/flows/flow-nonexistent")
    assert response.status_code == 404


# ----------------- TESTS FOR FLOW SEGMENTS ENDPOINTS -----------------

def test_create_flow_segments_basic(client, mock_db):
    # Setup flow
    mock_db.collection("flows").document("flow-seg").set({
        "id": "flow-seg",
        "source_id": "source-1",
        "format": "urn:x-tams:format.video"
    })

    segment_payload = {
        "object_id": "obj-1",
        "timerange": "100_200"
    }

    # Post single segment (as dict)
    response = client.post("/flows/flow-seg/segments", json=segment_payload)
    assert response.status_code == 201
    assert response.json() == {"message": "Segments created successfully"}

    # Verify added to database
    segs = mock_db.collection("segments").get()
    assert len(segs) == 1
    assert segs[0].to_dict()["object_id"] == "obj-1"
    assert segs[0].to_dict()["flow_id"] == "flow-seg"


def test_create_flow_segments_list_and_overlaps(client, mock_db):
    mock_db.collection("flows").document("flow-seg").set({
        "id": "flow-seg",
        "source_id": "source-1",
        "format": "urn:x-tams:format.video"
    })

    # Pre-populate a segment at timerange 100_200
    # and we represent the Nanoseconds start/end corresponding to TimeRange
    # (tr.start = 100s -> 100,000,000,000 ns, tr.end = 200s -> 200,000,000,000 ns)
    # Inside conftest.py or test code, we can let main.py calculate it, or seed manually:
    from mediatimestamp.immutable import TimeRange
    tr = TimeRange.from_str("100_200")
    start_ns = tr.start.to_nanosec()
    end_ns = tr.end.to_nanosec()

    mock_db.collection("segments").document("seg-seeded").set({
        "object_id": "obj-seeded",
        "flow_id": "flow-seg",
        "timerange": "100_200",
        "timerange_start": start_ns,
        "timerange_end": end_ns
    })

    # Attempt to post a list of segments where one is normal and one overlaps
    segments_payload = [
        {"object_id": "obj-good", "timerange": "300_400"},
        {"object_id": "obj-overlapping", "timerange": "150_250"}
    ]

    response = client.post("/flows/flow-seg/segments", json=segments_payload)
    assert response.status_code == 200
    res_data = response.json()
    assert "failed_segments" in res_data
    assert len(res_data["failed_segments"]) == 1
    assert res_data["failed_segments"][0]["object_id"] == "obj-overlapping"
    assert "overlaps" in res_data["failed_segments"][0]["error"]

    # Verify that the good segment was still added
    all_segs = mock_db.collection("segments").get()
    object_ids = [s.to_dict()["object_id"] for s in all_segs]
    assert "obj-good" in object_ids
    assert "obj-overlapping" not in object_ids


def test_create_flow_segments_nonexistent_flow(client):
    response = client.post("/flows/flow-nonexistent/segments", json={"object_id": "obj-1", "timerange": "100:200"})
    assert response.status_code == 404


def test_create_flow_segments_invalid_timerange_format(client, mock_db):
    mock_db.collection("flows").document("flow-seg").set({
        "id": "flow-seg",
        "source_id": "source-1",
        "format": "urn:x-tams:format.video"
    })
    # Post segment with bad timerange string
    response = client.post("/flows/flow-seg/segments", json={"object_id": "obj-1", "timerange": "invalid_timerange"})
    # It catches exception and registers in failed_segments
    assert response.status_code == 200
    assert len(response.json()["failed_segments"]) == 1
    assert "invalid" in response.json()["failed_segments"][0]["error"].lower()


def test_get_flow_segments_basic(client, mock_db):
    mock_db.collection("segments").document("s1").set({
        "object_id": "obj-1",
        "flow_id": "flow-1",
        "timerange": "100:200",
        "timerange_start": 100000000,
        "timerange_end": 200000000
    })
    mock_db.collection("segments").document("s2").set({
        "object_id": "obj-2",
        "flow_id": "flow-1",
        "timerange": "300:400",
        "timerange_start": 300000000,
        "timerange_end": 400000000
    })

    # Get all segments for flow-1
    response = client.get("/flows/flow-1/segments")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_flow_segments_filter_and_invalid_timerange(client, mock_db):
    # Seed segments (with standard timestamps, e.g. 100s -> 100_000_000_000 ns)
    from mediatimestamp.immutable import TimeRange
    t1 = TimeRange.from_str("100_200")
    t2 = TimeRange.from_str("300_400")

    mock_db.collection("segments").document("s1").set({
        "object_id": "obj-1",
        "flow_id": "flow-1",
        "timerange": "100_200",
        "timerange_start": t1.start.to_nanosec(),
        "timerange_end": t1.end.to_nanosec()
    })
    mock_db.collection("segments").document("s2").set({
        "object_id": "obj-2",
        "flow_id": "flow-1",
        "timerange": "300_400",
        "timerange_start": t2.start.to_nanosec(),
        "timerange_end": t2.end.to_nanosec()
    })

    # Filter with overlapping timerange
    response = client.get("/flows/flow-1/segments?timerange=150_250")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["object_id"] == "obj-1"

    # Filter with invalid timerange
    response = client.get("/flows/flow-1/segments?timerange=invalid_format")
    assert response.status_code == 400
    assert "Invalid timerange parameter" in response.json()["detail"]


def test_get_flow_segments_presigned_with_service_account(client, mock_db):
    mock_db.collection("segments").document("s1").set({
        "object_id": "obj-1",
        "flow_id": "flow-1",
        "timerange": "100:200",
        "timerange_start": 100,
        "timerange_end": 200
    })

    # Test WITH SERVICE_ACCOUNT_EMAIL set to trigger that code branch
    os.environ["SERVICE_ACCOUNT_EMAIL"] = "test-sa@gcp.com"
    try:
        response = client.get("/flows/flow-1/segments?presigned=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "get_urls" in data[0]
        assert "mock_signed=true" in data[0]["get_urls"][0]["url"]
    finally:
        del os.environ["SERVICE_ACCOUNT_EMAIL"]


def test_get_flow_segments_presigned_no_service_account(client, mock_db):
    mock_db.collection("segments").document("s1").set({
        "object_id": "obj-1",
        "flow_id": "flow-1",
        "timerange": "100:200",
        "timerange_start": 100,
        "timerange_end": 200
    })

    # Test WITHOUT SERVICE_ACCOUNT_EMAIL
    if "SERVICE_ACCOUNT_EMAIL" in os.environ:
        del os.environ["SERVICE_ACCOUNT_EMAIL"]

    response = client.get("/flows/flow-1/segments?presigned=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "get_urls" in data[0]
    assert "mock_signed=true" in data[0]["get_urls"][0]["url"]


def test_delete_flow_segments_all(client, mock_db):
    mock_db.collection("segments").document("s1").set({
        "object_id": "obj-1",
        "flow_id": "flow-1",
        "timerange": "100:200",
        "timerange_start": 100,
        "timerange_end": 200
    })
    mock_db.collection("segments").document("s2").set({
        "object_id": "obj-2",
        "flow_id": "flow-1",
        "timerange": "300:400",
        "timerange_start": 300,
        "timerange_end": 400
    })

    # Delete all segments for flow-1
    response = client.delete("/flows/flow-1/segments")
    assert response.status_code == 204
    assert len(mock_db.collection("segments").get()) == 0


def test_delete_flow_segments_filtered(client, mock_db):
    from mediatimestamp.immutable import TimeRange
    t1 = TimeRange.from_str("100_200")
    t2 = TimeRange.from_str("300_400")

    mock_db.collection("segments").document("s1").set({
        "object_id": "obj-1",
        "flow_id": "flow-1",
        "timerange": "100_200",
        "timerange_start": t1.start.to_nanosec(),
        "timerange_end": t1.end.to_nanosec()
    })
    mock_db.collection("segments").document("s2").set({
        "object_id": "obj-2",
        "flow_id": "flow-1",
        "timerange": "300_400",
        "timerange_start": t2.start.to_nanosec(),
        "timerange_end": t2.end.to_nanosec()
    })

    # Delete filtered by timerange 100_200
    # Must completely contain the segment since line 326:
    # if data["timerange_start"] >= start_ns and data["timerange_end"] <= end_ns:
    response = client.delete("/flows/flow-1/segments?timerange=50_250")
    assert response.status_code == 204

    # Verify s1 deleted, s2 preserved
    remaining = mock_db.collection("segments").get()
    assert len(remaining) == 1
    assert remaining[0].to_dict()["object_id"] == "obj-2"


def test_delete_flow_segments_invalid_timerange(client):
    response = client.delete("/flows/flow-1/segments?timerange=invalid_format")
    assert response.status_code == 400
    assert "Invalid timerange" in response.json()["detail"]


# ----------------- TESTS FOR STORAGE BACKENDS ENDPOINT -----------------

def test_get_storage_backends_default_seeding(client, mock_db):
    # Verify starting empty
    assert len(mock_db.collection("storage_backends").get()) == 0

    response = client.get("/service/storage-backends")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "default-gcs-backend"
    assert data[0]["default_storage"] is True

    # Verify written to database
    assert len(mock_db.collection("storage_backends").get()) == 1


def test_get_storage_backends_existing(client, mock_db):
    custom_backend = {
        "id": "custom-backend",
        "label": "Custom Label",
        "store_type": "http_object_store",
        "provider": "gcp",
        "region": "us-central1",
        "store_product": "gcs",
        "default_storage": False
    }
    mock_db.collection("storage_backends").document("custom-backend").set(custom_backend)

    response = client.get("/service/storage-backends")
    assert response.status_code == 200
    assert response.json() == [custom_backend]


# ----------------- TESTS FOR WEBHOOKS ENDPOINTS -----------------

def test_webhooks_crud(client, mock_db):
    webhook_payload = {
        "url": "https://example.com/webhook",
        "events": ["flow.created", "flow.deleted"]
    }

    # CREATE
    response = client.post("/service/webhooks", json=webhook_payload)
    assert response.status_code == 201
    created_wh = response.json()
    assert created_wh["id"] is not None
    assert created_wh["url"] == "https://example.com/webhook"
    assert created_wh["status"] == "started"

    webhook_id = created_wh["id"]

    # LIST
    response = client.get("/service/webhooks")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == webhook_id

    # GET BY ID
    response = client.get(f"/service/webhooks/{webhook_id}")
    assert response.status_code == 200
    assert response.json()["url"] == "https://example.com/webhook"

    # GET NON-EXISTENT
    response = client.get("/service/webhooks/nonexistent")
    assert response.status_code == 404

    # UPDATE
    update_payload = {
        "url": "https://example.com/updated-webhook",
        "events": ["flow.created"]
    }
    response = client.put(f"/service/webhooks/{webhook_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["url"] == "https://example.com/updated-webhook"

    # UPDATE NON-EXISTENT
    response = client.put("/service/webhooks/nonexistent", json=update_payload)
    assert response.status_code == 404

    # DELETE
    response = client.delete(f"/service/webhooks/{webhook_id}")
    assert response.status_code == 204
    assert not mock_db.collection("webhooks").document(webhook_id).get().exists

    # DELETE NON-EXISTENT
    response = client.delete("/service/webhooks/nonexistent")
    assert response.status_code == 404


# ----------------- TESTS FOR FLOW STORAGE ALLOCATION ENDPOINT -----------------

def test_allocate_flow_storage_basic(client, mock_db):
    mock_db.collection("flows").document("flow-alloc").set({
        "id": "flow-alloc",
        "source_id": "source-1",
        "format": "urn:x-tams:format.video"
    })

    # Test with SERVICE_ACCOUNT_EMAIL set
    os.environ["SERVICE_ACCOUNT_EMAIL"] = "test-sa@gcp.com"
    try:
        response = client.post("/flows/flow-alloc/storage", json={"limit": 2})
        assert response.status_code == 201
        data = response.json()
        assert "media_objects" in data
        assert len(data["media_objects"]) == 2
        for item in data["media_objects"]:
            assert item["object_id"] is not None
            assert "mock_signed=true" in item["put_url"]["url"]
            assert "method=PUT" in item["put_url"]["url"]
            assert item["put_url"]["content-type"] == "video/mp2t"
    finally:
        del os.environ["SERVICE_ACCOUNT_EMAIL"]


def test_allocate_flow_storage_no_service_account(client, mock_db):
    mock_db.collection("flows").document("flow-alloc").set({
        "id": "flow-alloc",
        "source_id": "source-1",
        "format": "urn:x-tams:format.video"
    })

    # Test WITHOUT SERVICE_ACCOUNT_EMAIL
    if "SERVICE_ACCOUNT_EMAIL" in os.environ:
        del os.environ["SERVICE_ACCOUNT_EMAIL"]

    response = client.post("/flows/flow-alloc/storage", json={"limit": 1})
    assert response.status_code == 201
    data = response.json()
    assert len(data["media_objects"]) == 1
    assert "mock_signed=true" in data["media_objects"][0]["put_url"]["url"]


def test_allocate_flow_storage_nonexistent_flow(client):
    response = client.post("/flows/flow-nonexistent/storage", json={"limit": 1})
    assert response.status_code == 404


# ----------------- SECURITY REMEDIATION TESTS -----------------

def test_create_flow_segments_path_traversal_rejection(client, mock_db):
    mock_db.collection("flows").document("flow-secure").set({
        "id": "flow-secure",
        "source_id": "source-1",
        "format": "urn:x-tams:format.video"
    })

    unsafe_payloads = [
        {"object_id": "../traversal", "timerange": "100:200"},
        {"object_id": "sub/folder", "timerange": "100:200"},
        {"object_id": "some_file\\with\\slash", "timerange": "100:200"},
    ]

    for payload in unsafe_payloads:
        response = client.post("/flows/flow-secure/segments", json=payload)
        assert response.status_code == 200
        res_data = response.json()
        assert "failed_segments" in res_data
        assert len(res_data["failed_segments"]) == 1
        assert res_data["failed_segments"][0]["object_id"] == payload["object_id"]
        assert "Invalid object_id" in res_data["failed_segments"][0]["error"]


def test_put_source_tag_path_injection_rejection(client, mock_db):
    source_id = "src-secure"
    mock_db.collection("sources").document(source_id).set({
        "id": source_id,
        "format": "urn:x-tams:format.video"
    })

    # PUT tag name with dots
    response = client.put(f"/sources/{source_id}/tags/auth_classes.some_group", json="value")
    assert response.status_code == 400
    assert "cannot contain dots" in response.json()["detail"]

    # DELETE tag name with dots
    response = client.delete(f"/sources/{source_id}/tags/auth_classes.some_group")
    assert response.status_code == 400
    assert "cannot contain dots" in response.json()["detail"]


def test_webhooks_key_encryption_in_firestore(client, mock_db):
    webhook_payload = {
        "url": "https://example.com/webhook",
        "api_key_name": "X-Auth-Key",
        "api_key_value": "secret-plaintext-key-value-12345",
        "events": ["flow.created"]
    }

    # Create webhook
    response = client.post("/service/webhooks", json=webhook_payload)
    assert response.status_code == 201
    created_wh = response.json()
    webhook_id = created_wh["id"]

    # Verify response schema does NOT contain api_key_value
    assert "api_key_value" not in created_wh

    # Retrieve from Firestore and assert that value is encrypted (not plaintext)
    firestore_data = mock_db.collection("webhooks").document(webhook_id).get().to_dict()
    assert firestore_data["api_key_value"] != "secret-plaintext-key-value-12345"
    assert "secret-plaintext-key" not in firestore_data["api_key_value"]

    # Ensure it decrypts correctly back to original plaintext using the same algorithm
    from app.main import decrypt_val
    decrypted = decrypt_val(firestore_data["api_key_value"])
    assert decrypted == "secret-plaintext-key-value-12345"
