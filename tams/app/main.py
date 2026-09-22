from fastapi import FastAPI, HTTPException, Body, Response
from app.models import Service, ServicePost, Source, Flow, FlowSegmentPost, FlowSegment, StorageBackend, WebhookPost, Webhook, StorageAllocationRequest, StorageAllocationResponse
from typing import List, Union, Optional
from google.cloud import firestore
from google.cloud import storage
import datetime
import uuid
import os
from mediatimestamp.immutable import TimeRange
import re
import base64
from cryptography.fernet import Fernet


app = FastAPI(title="TAMS API on GCP")

# Validation and encryption utilities
SAFE_OBJECT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

def is_safe_object_id(object_id: str) -> bool:
    if not SAFE_OBJECT_ID_REGEX.match(object_id):
        return False
    if ".." in object_id or "/" in object_id or "\\" in object_id:
        return False
    return True

# Retrieve/generate Fernet master key for webhook secret encryption
SECRET_KEY_ENV = os.environ.get("TAMS_SECRET_KEY")
if SECRET_KEY_ENV:
    try:
        import hashlib
        key_bytes = hashlib.sha256(SECRET_KEY_ENV.encode()).digest()
        cipher_suite = Fernet(base64.urlsafe_b64encode(key_bytes))
    except Exception:
        cipher_suite = Fernet(Fernet.generate_key())
else:
    import hashlib
    key_bytes = hashlib.sha256(b"tams-default-dev-secret-key-do-not-use-in-prod").digest()
    cipher_suite = Fernet(base64.urlsafe_b64encode(key_bytes))

def encrypt_val(val: str) -> str:
    if not val:
        return val
    return cipher_suite.encrypt(val.encode()).decode()

def decrypt_val(val: str) -> str:
    if not val:
        return val
    try:
        return cipher_suite.decrypt(val.encode()).decode()
    except Exception:
        return val


db = firestore.Client(database=os.environ.get("FIRESTORE_DB_NAME", "(default)"))

@app.get("/")
def read_root():
    return ["service", "flows", "sources", "flow-delete-requests"]

@app.get("/service", response_model=Service, response_model_exclude_none=True)
def get_service():
    doc_ref = db.collection("service").document("info")
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        # Initialize with default data
        default_info = {
            "name": "TAMS GCP Service",
            "description": "Reference implementation of TAMS on Google Cloud",
            "type": "urn:x-tams:service.gcp",
            "api_version": "8.0",
            "service_version": "0.1.0",
            "event_stream_mechanisms": [{"name": "webhooks"}],
            "min_object_timeout": "300:0",
            "min_presigned_url_timeout": "30:0"
        }
        doc_ref.set(default_info)
        return default_info

@app.post("/service")
def post_service(service_post: ServicePost):
    doc_ref = db.collection("service").document("info")
    update_data = {}
    if service_post.name is not None:
        update_data["name"] = service_post.name
    if service_post.description is not None:
        update_data["description"] = service_post.description
    
    if update_data:
        doc_ref.set(update_data, merge=True)
        return {"message": "Service info updated"}
    else:
        return {"message": "No updates provided"}

@app.get("/sources", response_model=List[Source], response_model_exclude_none=True)
def get_sources(limit: int = 10):
    sources_ref = db.collection("sources")
    docs = sources_ref.limit(limit).stream()
    return [doc.to_dict() for doc in docs]

@app.get("/sources/{sourceId}", response_model=Source, response_model_exclude_none=True)
def get_source(sourceId: str):
    doc_ref = db.collection("sources").document(sourceId)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        raise HTTPException(status_code=404, detail="Source not found")

@app.put("/sources/{sourceId}/label", status_code=204)
def put_source_label(sourceId: str, label: str = Body(...)):
    doc_ref = db.collection("sources").document(sourceId)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Source not found")
    doc_ref.update({"label": label})
    return

@app.delete("/sources/{sourceId}/label", status_code=204)
def delete_source_label(sourceId: str):
    doc_ref = db.collection("sources").document(sourceId)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Source not found")
    doc_ref.update({"label": firestore.DELETE_FIELD})
    return

@app.put("/sources/{sourceId}/description", status_code=204)
def put_source_description(sourceId: str, description: str = Body(...)):
    doc_ref = db.collection("sources").document(sourceId)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Source not found")
    doc_ref.update({"description": description})
    return

@app.delete("/sources/{sourceId}/description", status_code=204)
def delete_source_description(sourceId: str):
    doc_ref = db.collection("sources").document(sourceId)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Source not found")
    doc_ref.update({"description": firestore.DELETE_FIELD})
    return

@app.put("/sources/{sourceId}/tags/{name}", status_code=204)
def put_source_tag(sourceId: str, name: str, value: str | List[str] = Body(...)):
    if "." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Tag name cannot contain dots or slashes.")
    doc_ref = db.collection("sources").document(sourceId)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Source not found")
    doc_ref.update({f"tags.{name}": value})
    return

@app.delete("/sources/{sourceId}/tags/{name}", status_code=204)
def delete_source_tag(sourceId: str, name: str):
    if "." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Tag name cannot contain dots or slashes.")
    doc_ref = db.collection("sources").document(sourceId)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Source not found")
    doc_ref.update({f"tags.{name}": firestore.DELETE_FIELD})
    return

@app.get("/flows", response_model=List[Flow], response_model_exclude_none=True)
def get_flows(limit: int = 10):
    flows_ref = db.collection("flows")
    docs = flows_ref.limit(limit).stream()
    return [doc.to_dict() for doc in docs]

@app.get("/flows/{flowId}", response_model=Flow, response_model_exclude_none=True)
def get_flow(flowId: str):
    doc_ref = db.collection("flows").document(flowId)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        raise HTTPException(status_code=404, detail="Flow not found")

@app.put("/flows/{flowId}", status_code=200)
def put_flow(flowId: str, flow: Flow, response: Response):
    doc_ref = db.collection("flows").document(flowId)
    doc = doc_ref.get()
    
    # Check source
    source_ref = db.collection("sources").document(flow.source_id)
    source_doc = source_ref.get()
    if not source_doc.exists:
        # Create source
        source_data = {
            "id": flow.source_id,
            "format": flow.format,
            "created": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
            "label": f"Auto-created Source for Flow {flowId}",
            "description": "Source created automatically when flow was created."
        }
        source_ref.set(source_data)
        
    flow_data = flow.model_dump()
    flow_data["id"] = flowId
    
    if doc.exists:
        flow_data["metadata_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        doc_ref.update(flow_data)
        response.status_code = 204
        return
    else:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        flow_data["created"] = now
        flow_data["metadata_updated"] = now
        doc_ref.set(flow_data)
        response.status_code = 201
        return flow_data


@app.delete("/flows/{flowId}", status_code=204)
def delete_flow(flowId: str):
    doc_ref = db.collection("flows").document(flowId)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Flow not found")
    doc_ref.delete()
    return

@app.post("/flows/{flowId}/segments", status_code=201)
def create_flow_segments(flowId: str, segments: Union[FlowSegmentPost, List[FlowSegmentPost]], response: Response):
    # Verify flow exists
    flow_ref = db.collection("flows").document(flowId)
    flow_doc = flow_ref.get()
    if not flow_doc.exists:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    if not isinstance(segments, list):
        segments = [segments]
        
    failed_segments = []
    for seg in segments:
        if not is_safe_object_id(seg.object_id):
            failed_segments.append({
                "object_id": seg.object_id,
                "timerange": seg.timerange,
                "error": "Invalid object_id format. Path traversal or special characters are not allowed."
            })
            continue
            
        try:
            tr = TimeRange.from_str(seg.timerange)
            start_ns = tr.start.to_nanosec() + (0 if tr.includes_start() else 1)
            end_ns = tr.end.to_nanosec() - (0 if tr.includes_end() else 1)
            
            # Check for overlaps in Firestore using optimized range query
            # We fetch segments starting before the new segment ends
            all_segments = db.collection("segments")\
                .where("flow_id", "==", flowId)\
                .where("timerange_start", "<=", end_ns)\
                .get()
            
            is_overlap = False
            for doc in all_segments:
                data = doc.to_dict()
                if data["timerange_end"] >= start_ns:
                    is_overlap = True
                    break

            
            if is_overlap:
                failed_segments.append({
                    "object_id": seg.object_id,
                    "timerange": seg.timerange,
                    "error": "Timerange overlaps with existing segment"
                })
                continue
                
            # Store segment
            seg_data = seg.model_dump()
            seg_data["flow_id"] = flowId
            seg_data["timerange_start"] = start_ns
            seg_data["timerange_end"] = end_ns
            
            db.collection("segments").add(seg_data)
            
        except Exception as e:
            failed_segments.append({
                "object_id": seg.object_id,
                "timerange": seg.timerange,
                "error": str(e)
            })
            
    if failed_segments:
        response.status_code = 200
        return {"failed_segments": failed_segments}
        
    return {"message": "Segments created successfully"}

@app.get("/flows/{flowId}/segments", response_model=List[FlowSegmentPost], response_model_exclude_none=True)
def get_flow_segments(flowId: str, timerange: Optional[str] = None, limit: Optional[int] = 100, presigned: bool = False, reverse_order: bool = False):
    query = db.collection("segments").where("flow_id", "==", flowId)
    
    segments = []
    
    if timerange:
        try:
            tr = TimeRange.from_str(timerange)
            start_ns = tr.start.to_nanosec() + (0 if tr.includes_start() else 1)
            end_ns = tr.end.to_nanosec() - (0 if tr.includes_end() else 1)
            
            # Fetch only segments starting before or at the requested end point
            docs = query.where("timerange_start", "<=", end_ns).get()
            for doc in docs:
                seg = doc.to_dict()
                if seg["timerange_end"] >= start_ns:
                    segments.append(seg)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid timerange parameter: {e}")
    else:
        # Prevent OOM by limiting database-side when listing
        docs = query.limit(limit).get()
        for doc in docs:
            segments.append(doc.to_dict())

    if reverse_order:
        segments.sort(key=lambda seg: seg.get("timerange_start", 0), reverse=True)
    else:
        segments.sort(key=lambda seg: seg.get("timerange_start", 0))
            
    segments = segments[:limit]
    
    if presigned and segments:
        bucket_name = os.environ.get("TAMS_BUCKET_NAME", "tams-objects-bucket")
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        service_account_email = os.environ.get("SERVICE_ACCOUNT_EMAIL")
        
        access_token = None
        if service_account_email:
            import google.auth
            from google.auth.transport import requests as auth_requests
            
            credentials, project_id = google.auth.default()
            auth_request = auth_requests.Request()
            credentials.refresh(auth_request)
            access_token = credentials.token
            
        for seg in segments:
            # Ensure safe name formatting before signed URL generation
            if not is_safe_object_id(seg["object_id"]):
                raise HTTPException(status_code=400, detail="Invalid object_id detected in stored segment metadata.")
                
            blob_name = f"{flowId}/{seg['object_id']}"
            blob = bucket.blob(blob_name)
            
            try:
                kwargs = {
                    "version": "v4",
                    "expiration": datetime.timedelta(minutes=15),
                    "method": "GET"
                }
                if service_account_email:
                    kwargs["service_account_email"] = service_account_email
                    kwargs["access_token"] = access_token
                    
                url = blob.generate_signed_url(**kwargs)
                seg["get_urls"] = [{"url": url}]
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to generate signed URL for GET: {e}")
    
    return segments

@app.delete("/flows/{flowId}/segments", status_code=204)
def delete_flow_segments(flowId: str, timerange: Optional[str] = None):
    query = db.collection("segments").where("flow_id", "==", flowId)
    
    if not timerange:
        docs = query.get()
        for doc in docs:
            doc.reference.delete()
        return
        
    try:
        tr = TimeRange.from_str(timerange)
        start_ns = tr.start.to_nanosec() + (0 if tr.includes_start() else 1)
        end_ns = tr.end.to_nanosec() - (0 if tr.includes_end() else 1)
        
        # Optimize by fetching only segments starting before or at end_ns
        docs = query.where("timerange_start", "<=", end_ns).get()
        for doc in docs:
            data = doc.to_dict()
            if data["timerange_start"] >= start_ns and data["timerange_end"] <= end_ns:
                doc.reference.delete()
                
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid timerange parameter: {e}")
        
    return

@app.get("/service/storage-backends", response_model=List[StorageBackend], response_model_exclude_none=True)
def get_storage_backends():
    docs = db.collection("storage_backends").get()
    backends = []
    for doc in docs:
        backends.append(doc.to_dict())
        
    if not backends:
        # Seed a default GCS backend
        default_backend = {
            "id": "default-gcs-backend",
            "label": "Default GCS Storage",
            "store_type": "http_object_store",
            "provider": "gcp",
            "region": "europe-west1",
            "store_product": "gcs",
            "default_storage": True
        }
        db.collection("storage_backends").document(default_backend["id"]).set(default_backend)
        backends.append(default_backend)
        
    return backends

@app.post("/service/webhooks", response_model=Webhook, status_code=201)
def create_webhook(webhook: WebhookPost):
    webhook_id = str(uuid.uuid4())
    webhook_data = webhook.model_dump()
    webhook_data["id"] = webhook_id
    webhook_data["status"] = "started"
    if webhook.api_key_value:
        webhook_data["api_key_value"] = encrypt_val(webhook.api_key_value)
    
    db.collection("webhooks").document(webhook_id).set(webhook_data)
    
    return Webhook(**webhook_data)

@app.get("/service/webhooks", response_model=List[Webhook], response_model_exclude_none=True)
def get_webhooks():
    docs = db.collection("webhooks").get()
    webhooks_list = []
    for doc in docs:
        webhooks_list.append(doc.to_dict())
    return webhooks_list

@app.get("/service/webhooks/{webhookId}", response_model=Webhook, response_model_exclude_none=True)
def get_webhook(webhookId: str):
    doc_ref = db.collection("webhooks").document(webhookId)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return doc.to_dict()

@app.put("/service/webhooks/{webhookId}", response_model=Webhook)
def update_webhook(webhookId: str, webhook: WebhookPost):
    doc_ref = db.collection("webhooks").document(webhookId)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Webhook not found")
        
    webhook_data = webhook.model_dump()
    webhook_data["id"] = webhookId
    webhook_data["status"] = "started"
    if webhook.api_key_value:
        webhook_data["api_key_value"] = encrypt_val(webhook.api_key_value)
    
    doc_ref.update(webhook_data)
    
    return Webhook(**webhook_data)

@app.delete("/service/webhooks/{webhookId}", status_code=204)
def delete_webhook(webhookId: str):
    doc_ref = db.collection("webhooks").document(webhookId)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Webhook not found")
    doc_ref.delete()
    return

@app.post("/flows/{flowId}/storage", response_model=StorageAllocationResponse, status_code=201)
def allocate_flow_storage(flowId: str, req: StorageAllocationRequest):
    flow_ref = db.collection("flows").document(flowId)
    if not flow_ref.get().exists:
        raise HTTPException(status_code=404, detail="Flow not found")
        
    bucket_name = os.environ.get("TAMS_BUCKET_NAME", "tams-objects-bucket")
    
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize storage client: {e}")

    media_objects = []
    for _ in range(req.limit):
        object_id = str(uuid.uuid4())
        blob_name = f"{flowId}/{object_id}"
        blob = bucket.blob(blob_name)
        
        try:
            service_account_email = os.environ.get("SERVICE_ACCOUNT_EMAIL")
            
            if service_account_email:
                import google.auth
                from google.auth.transport import requests as auth_requests
                
                credentials, project_id = google.auth.default()
                auth_request = auth_requests.Request()
                credentials.refresh(auth_request)
                
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=datetime.timedelta(minutes=15),
                    method="PUT",
                    content_type="video/mp2t",
                    service_account_email=service_account_email,
                    access_token=credentials.token
                )
            else:
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=datetime.timedelta(minutes=15),
                    method="PUT",
                    content_type="video/mp2t"
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate signed URL: {e}")
            
        media_objects.append({
            "object_id": object_id,
            "put_url": {
                "url": url,
                "content-type": "video/mp2t"
            }
        })
        
    return {"media_objects": media_objects}


















