# 3. Tractus-X SDK individual repository

Date: 2025-02-12

## Status

Accepted

## Context

We need to have a stable way of maintaining the Eclipse Dataspace Connector "API specifications" and "data models" in a separate repo so it can be reused by multiple applications and do not depend on the "Release" status from the Industry Core Hub.

Therefore is required to have a new repository for externalizing this logic which is currently being implemented in the Industry Core Hub.

The objective is to automate the creation of data models using git actions for every tractus-x edc release. So we can be able to use several target versions of the EDC.

The industry core hub will be the first "lighthouse" on how to use the Tractus-X SDK.

## Decision

Separate the tractusx-sdk into another repository.

![Plug and Play Architecture](media/sdk-context.png)

and here is the actual repository separation with the Modular Microservices Architecture

![Diagram Architecture Repos](media/modular-microservices-architecture.svg)


## Consequences

- We need to create a mechanism for publishing the package into Pypi. 
- maybe it can be published in github.
- Duplication of Documentation can happen (make sure to align the decisions in each repo)
- Creating more work for the developers

## Benefits

- Have a stable release "connected" to the specific EDC version.
- Organize multiple EDC version targets in an agnostic way.
- EDC selection can be enabled
- Code separated for stable releases and no confusion when the EDC changes, that nothing strange will happen.
- Logic separeated from the Industry Core Hub, and better reusabilty for other producst .

## NOTICE

This work is licensed under the [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/legalcode).

- SPDX-License-Identifier: CC-BY-4.0
- SPDX-FileCopyrightText: 2025 Contributors to the Eclipse Foundation
- Source URL: https://github.com/eclipse-tractusx/industry-core-hub
