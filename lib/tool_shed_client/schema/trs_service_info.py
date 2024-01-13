# generated by datamodel-codegen:
#   filename:  https://raw.githubusercontent.com/ga4gh-discovery/ga4gh-service-info/v1.0.0/service-info.yaml#/paths/~1service-info
#   timestamp: 2022-12-20T21:01:57+00:00

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import AnyUrl, BaseModel, Field


class Organization(BaseModel):
    name: str = Field(
        ..., description="Name of the organization responsible for the service", example="My organization"
    )
    url: AnyUrl = Field(
        ..., description="URL of the website of the organization (RFC 3986 format)", example="https://example.com"
    )


class ServiceType(BaseModel):
    group: str = Field(
        ...,
        description="Namespace in reverse domain name format. Use `org.ga4gh` for implementations compliant with official GA4GH specifications. For services with custom APIs not standardized by GA4GH, or implementations diverging from official GA4GH specifications, use a different namespace (e.g. your organization's reverse domain name).",
        example="org.ga4gh",
    )
    artifact: str = Field(
        ...,
        description="Name of the API or GA4GH specification implemented. Official GA4GH types should be assigned as part of standards approval process. Custom artifacts are supported.",
        example="beacon",
    )
    version: str = Field(
        ...,
        description="Version of the API or specification. GA4GH specifications use semantic versioning.",
        example="1.0.0",
    )


class Service(BaseModel):
    id: str = Field(
        ...,
        description="Unique ID of this service. Reverse domain name notation is recommended, though not required. The identifier should attempt to be globally unique so it can be used in downstream aggregator services e.g. Service Registry.",
        example="org.ga4gh.myservice",
    )
    name: str = Field(..., description="Name of this service. Should be human readable.", example="My project")
    type: ServiceType
    description: Optional[str] = Field(
        None,
        description="Description of the service. Should be human readable and provide information about the service.",
        example="This service provides...",
    )
    organization: Organization = Field(..., description="Organization providing the service")
    contactUrl: Optional[AnyUrl] = Field(
        None,
        description="URL of the contact for the provider of this service, e.g. a link to a contact form (RFC 3986 format), or an email (RFC 2368 format).",
        example="mailto:support@example.com",
    )
    documentationUrl: Optional[AnyUrl] = Field(
        None,
        description="URL of the documentation of this service (RFC 3986 format). This should help someone learn how to use your service, including any specifics required to access data, e.g. authentication.",
        example="https://docs.myservice.example.com",
    )
    createdAt: Optional[datetime] = Field(
        None,
        description="Timestamp describing when the service was first deployed and available (RFC 3339 format)",
        example="2019-06-04T12:58:19Z",
    )
    updatedAt: Optional[datetime] = Field(
        None,
        description="Timestamp describing when the service was last updated (RFC 3339 format)",
        example="2019-06-04T12:58:19Z",
    )
    environment: Optional[str] = Field(
        None,
        description="Environment the service is running in. Use this to distinguish between production, development and testing/staging deployments. Suggested values are prod, test, dev, staging. However this is advised and not enforced.",
        example="test",
    )
    version: str = Field(
        ...,
        description="Version of the service being described. Semantic versioning is recommended, but other identifiers, such as dates or commit hashes, are also allowed. The version should be changed whenever the service is updated.",
        example="1.0.0",
    )
