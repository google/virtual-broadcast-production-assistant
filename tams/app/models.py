from pydantic import BaseModel, Field
from typing import Optional, List

class EventStreamMechanism(BaseModel):
    name: str

class Service(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: str
    api_version: str
    service_version: Optional[str] = None
    event_stream_mechanisms: Optional[List[EventStreamMechanism]] = None
    min_object_timeout: str
    min_presigned_url_timeout: Optional[str] = None

class ServicePost(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Source(BaseModel):
    id: str
    format: str
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    tags: Optional[dict] = None
    source_collection: Optional[List[dict]] = None
    collected_by: Optional[List[str]] = None

class Flow(BaseModel):
    id: str
    source_id: str
    label: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created: Optional[str] = None
    metadata_updated: Optional[str] = None
    segments_updated: Optional[str] = None
    tags: Optional[dict] = None
    format: str
    essence_parameters: Optional[dict] = None
    codec: Optional[str] = None
    container: Optional[str] = None
    avg_bit_rate: Optional[int] = None
    max_bit_rate: Optional[int] = None
    segment_duration: Optional[dict] = None
    timerange: Optional[str] = None
    flow_collection: Optional[List[dict]] = None
    collected_by: Optional[List[str]] = None
    container_mapping: Optional[dict] = None

class FlowSegmentPost(BaseModel):
    object_id: str
    ts_offset: Optional[str] = None
    timerange: str
    object_timerange: Optional[str] = None
    last_duration: Optional[str] = None
    sample_offset: Optional[int] = None
    sample_count: Optional[int] = None
    get_urls: Optional[List[dict]] = None
    key_frame_count: Optional[int] = None

class FlowSegment(FlowSegmentPost):
    flow_id: str
    timerange_start: int
    timerange_end: int


class StorageBackend(BaseModel):
    id: str
    label: str
    store_type: str
    provider: str
    region: str
    availability_zone: Optional[str] = None
    store_product: str
    default_storage: Optional[bool] = None


class WebhookPost(BaseModel):
    url: str
    api_key_name: Optional[str] = None
    api_key_value: Optional[str] = None
    events: List[str]

class Webhook(BaseModel):
    id: str
    url: str
    api_key_name: Optional[str] = None
    events: List[str]
    status: str


class StorageAllocationRequest(BaseModel):
    limit: int

class PutUrl(BaseModel):
    url: str
    content_type: str = Field(alias="content-type")

    class Config:
        populate_by_name = True

class MediaObjectAllocation(BaseModel):
    object_id: str
    put_url: PutUrl

class StorageAllocationResponse(BaseModel):
    media_objects: List[MediaObjectAllocation]






