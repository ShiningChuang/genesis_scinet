# What Network Information Can the SENSE-O Intent API 2.0.4 Provide?

## Scope and evidence

This note summarizes what network information is demonstrably available through the SENSE-O Northbound Intent API 2.0.4 and related mechanisms implemented by the official SENSE Python client.

The main sources are:

- [SENSE-O Intent API 2.0.4 on SwaggerHub](https://app.swaggerhub.com/apis/xi-yang/SENSE-O-Intent-API/2.0.4)
- [Raw OpenAPI 2.0.4 definition](https://api.swaggerhub.com/apis/xi-yang/SENSE-O-Intent-API/2.0.4)
- [Official SENSE Python client](https://github.com/sdn-sense/sense-o-py-client)
- [Interactive workflow example](https://github.com/sdn-sense/sense-o-py-client/blob/f306b49342fd812e866c438ca353e99dee34f95a/util/workflow_interact.py)
- [SENSE utility and path-bandwidth troubleshooting code](https://github.com/sdn-sense/sense-o-py-client/blob/f306b49342fd812e866c438ca353e99dee34f95a/util/sense_util.py)
- [Workflow design documentation](https://github.com/sdn-sense/sense-o-py-client/blob/f306b49342fd812e866c438ca353e99dee34f95a/workflow_examples/docs/workflow_design.md)

There are two important evidence limitations:

1. The public OpenAPI document was last modified on January 19, 2023, and SwaggerHub marks it as `X-Published=false`.
2. The official Python client contains capabilities and endpoint variants that are not fully represented in the 2.0.4 OpenAPI document.

Consequently, this note distinguishes between capabilities demonstrated by the public specification or official code and capabilities verified against a particular deployed SENSE instance. Deployment-specific authorization, response formats, and supported operations still require live testing.

## Executive summary

SENSE-O provides useful network discovery, intent submission, reservation-aware path computation, service-resource readback, and provisioning-state information.

In particular, the available evidence confirms that an application can:

- discover network domains, service edge points, and inter-domain peer points;
- resolve human-facing resource information to SENSE/NML URIs;
- request L2 or L3 connectivity with endpoint, VLAN, IP, MAC, bandwidth, QoS, schedule, and path constraints;
- ask whether a feasible path exists for specified endpoints and a time window;
- query the maximum bandwidth reservable on that computed path during the requested time window;
- inspect service-instance resources such as terminals, VLANs, addresses, switching subnets, modeled path ports, capacity metadata, and schedule through manifests;
- inspect orchestration, provisioning, verification, and configuration state.

The available evidence does **not** establish that the Northbound Intent API provides:

- a complete node-and-link graph for every domain;
- a complete, ordered, hop-by-hop selected route;
- the physical underlay of an abstract or logical path;
- real-time link utilization or queue occupancy;
- continuous RTT, one-way latency, loss, jitter, or throughput telemetry;
- actual application throughput.

SENSE should therefore be viewed primarily as an intent, orchestration, reservation, and service-model interface. Additional topology and telemetry sources would still be required for closed-loop, measurement-driven network adaptation.

## 1. Information explicitly exposed by the Discovery API



### 1.1 Domains

`GET /discover` returns the globally known domains and their exposed boundary information. `GET /discover/domains` can also list known domains.

A domain description includes:

- `domain_uri`: the machine-readable SENSE/NML identifier of the domain;
- `domain_name`: a human-readable name;
- `edge_points[]`: service endpoints exposed by the domain;
- `peer_points[]`: connections from the domain to neighboring domains.



### 1.2 Edge points

An edge point is a domain boundary endpoint at which a network service can begin or terminate. Depending on the deployment, it may represent a DTN or server interface, a campus or data-center handoff, or a logical service termination point for an L2VPN or L3VPN.

For example, a domain may expose the following object:

```json
{
  "edge_points": [
    {
      "vlan_pool": "3600-3619",
      "ep_uri": "urn:ogf:network:maxgigapop.net:2013:s0:1_3:180-134.research.maxgigapop.net:eth1",
      "ipv4_pool": "172.16.2.0/30,172.17.2.0/30,172.18.2.0/30",
      "ep_name": "n/a",
      "capacity": "100000"
    }
  ]
}
```



#### `ep_uri`

`ep_uri` is the endpoint's unique identifier in the SENSE/NML model. It is the machine-readable value used in API requests and semantic-model relationships.

Although a URI may appear to encode a domain, device, port, and host interface, software should treat the full value as an opaque identifier. Parsing the string and relying on its apparent components would create a fragile dependency on a naming convention rather than on the API contract.

#### `ep_name`

`ep_name` is a human-readable label for display, logs, and operator selection. It may be `n/a`, may not be globally unique, and may change. An application should use `ep_uri`, rather than the name, as the stable reference.

#### `vlan_pool`

`vlan_pool` advertises the VLAN tags that may be used for services terminating at the edge point. For example:

```text
3600-3619
```

This field describes a candidate resource range. It does not prove that every VLAN in the range is free at the requested time. Availability may also depend on:

- existing reservations;
- the requested service interval;
- local SiteRM policy;
- VLAN support on other ports along the selected path;
- whether VLAN translation is available.



#### `ipv4_pool`

`ipv4_pool` lists IPv4 addresses or prefixes associated with the edge point, for example:

```text
172.16.2.0/30,172.17.2.0/30
```

These are candidate address resources. They are not evidence that an address has already been allocated to a service instance. The actual assignment must be read from the compiled intent or service manifest.

#### `capacity`

`capacity` is a capacity value advertised for the edge point. Its precise meaning is not documented in the discovery schema. The field is a string, and the schema provides no accompanying:

- unit;
- direction;
- timestamp;
- update cadence;
- physical, reservable, or available classification.

The intent schema explicitly defines `bandwidth.capacity` in Mbps, but that definition cannot automatically be transferred to the discovery field. `edge_points[].capacity` must not be treated as current utilization, instantaneous remaining bandwidth, or measured throughput without deployment-specific confirmation.

### 1.3 Inter-domain peer points

A peer point describes how the current domain connects to a neighboring domain. Here, “peer” denotes a topology adjacency and does not necessarily mean a BGP peer.

From the current domain's perspective:

```text
Current domain                         Neighboring domain
port_uri  ===== inter-domain edge =====  peer_uri
```

An example object is:

```json
{
  "peer_points": [
    {
      "peer_vlan_pool": "3600-3619",
      "port_vlan_pool": "3610-3629",
      "peer_uri": "urn:ogf:network:es.net:2013::wash-cr5:6_1_1:+",
      "port_uri": "urn:ogf:network:maxgigapop.net:2013:s0:1_1:wash-cr5",
      "peer_name": "n/a",
      "port_name": "n/a",
      "peer_capacity": "5000",
      "port_capacity": "10000"
    }
  ]
}
```



#### `port_uri` and `port_name`

`port_uri` identifies the current domain's side of the inter-domain connection. `port_name` is its human-readable label. Applications should use the URI for machine-level identity.

#### `peer_uri` and `peer_name`

`peer_uri` identifies the port on the neighboring domain's side. Together, `port_uri` and `peer_uri` tell SENSE where two domains meet. `peer_name` is the human-readable label for the remote side.

#### `port_vlan_pool` and `peer_vlan_pool`

These fields advertise the VLAN ranges available or supported on the two sides of the inter-domain boundary. The ranges need not be identical. For example:

```text
port_vlan_pool: 3610-3629
peer_vlan_pool: 3600-3619
```

Different ranges may reflect separate administrative label spaces, different policy constraints, or VLAN translation at the handoff. A multi-domain service cannot assume that the same VLAN ID is used in every domain.

#### `port_capacity` and `peer_capacity`

These are the capacity values advertised for the local and remote sides. They may differ because the two domains expose different device capabilities, reservable limits, or policy restrictions.

For example:

```text
port_capacity: 10000
peer_capacity: 5000
```

Even if both values use the same unit, the usable capacity of the inter-domain connection cannot exceed the more constrained side. The end-to-end service is also limited by every other port on the route, existing reservations, the requested time window, VLAN/IP resources, and SiteRM policy.

As with edge-point capacity, the OpenAPI document does not state the units or distinguish physical, reservable, and currently available capacity.

### 1.4 Internal nodes are not part of the typed discovery response

The typed `DomainDescription` response has no general-purpose inventory of internal nodes. Such nodes could include:

- routers;
- switches;
- optical equipment;
- servers and DTNs;
- compute clusters;
- storage systems;
- virtual switches;
- other network or end-system resources represented in the semantic model.

A real domain might look like this:

```text
Edge Point A
     │
Access Switch
     │
Core Router
     │
Border Router
     │
Peer Point
```

Or it might combine compute, storage, and network resources:

```text
Compute Node ── ToR Switch ── Core Router ── Border Router
Storage Node ──────┘
```

`DomainDescription` does not define a structure such as:

```json
{
  "nodes": [
    {
      "uri": "...",
      "name": "...",
      "type": "router"
    },
    {
      "uri": "...",
      "name": "...",
      "type": "storage"
    }
  ]
}
```

This does not mean that SENSE's internal semantic model lacks nodes. It means that `/discover` does not promise a typed list of every router, switch, compute node, and storage node inside a domain.

NML `Node` is also a general topology concept. A node does not necessarily carry a simple role label such as `router`, `compute`, or `storage`; richer roles may be represented through other semantic types and relationships.

### 1.5 Internal links and adjacency are not part of the typed discovery response

A link represents a modeled connection between endpoints or ports, for example:

```text
Switch A port 1 ───── Switch B port 7
```

Adjacency describes which objects are directly connected. Knowing that nodes A, B, and C exist is not enough to reconstruct a topology; the model must also state whether the connections are A–B, B–C, A–C, or something else.

For an internal topology such as:

```text
Edge Point ── Switch A ── Router B ── Border Router
```

a complete graph would need to represent each relationship:

```text
Edge Point ↔ Switch A
Switch A ↔ Router B
Router B ↔ Border Router
```

`DomainDescription` does not define a typed structure such as:

```json
{
  "links": [
    {
      "source": "switch-a:port-1",
      "destination": "router-b:port-2",
      "capacity": "100000"
    }
  ]
}
```

The presence of `peer_points[]` does not change this limitation. Peer points identify the two sides of an inter-domain boundary:

```text
Domain A port_uri ↔ Domain B peer_uri
```

They do not describe how traffic crosses the interior of either domain:

```text
Domain A                       Domain B
EP-A ── ??? ── port-A ║ peer-B ── ??? ── EP-B
```



### 1.6 Why a richer link description matters

A minimal link can state that two endpoints are connected. Path computation, reservation, monitoring, and recovery often need additional properties.

#### Link URI

A link URI provides stable identity. Two nodes may have multiple parallel links:

```text
        ┌── Link 1: 100 Gbps ──┐
Node A ─┤                       ├─ Node B
        └── Link 2: 400 Gbps ──┘
```

An object containing only:

```json
{
  "source": "A",
  "destination": "B"
}
```

does not say which link was selected. A URI such as:

```text
urn:ogf:network:es.net:link:denv-wash-1
```

allows systems to:

- refer to a specific link in a route;
- query its attributes;
- associate reservations and monitoring data with it;
- report a failure against the correct object;
- express include/exclude constraints;
- correlate the same link across systems.



#### Direction

A connection may be bidirectional, unidirectional, or asymmetric:

```text
A ──100 Gbps──→ B
A ←──10 Gbps──── B
```

Direction determines whether A can reach B, whether B can reach A, whether a bidirectional service is feasible, and how much capacity can be reserved in each direction. It also matters when the return path differs from the forward path.

A science transfer may require 100 Gbps from storage A to compute B while returning only control traffic in the opposite direction. A simple undirected adjacency cannot express that requirement accurately.

#### Administrative and operational state

A link's presence in a topology does not imply that it is currently usable. Possible states include:

- `UP`;
- `DOWN`;
- `DEGRADED`;
- `MAINTENANCE`;
- `UNKNOWN`;
- `ADMIN_DOWN`.

Administrative and operational state may differ:

```text
Administrative state: UP
Operational state: DOWN
```

In this case the link is enabled by policy but is not working. State information is needed to exclude failed links from path computation, diagnose provisioning failures, recompute paths after faults, and avoid scheduling work onto links under maintenance.

State also needs a timestamp. An `UP` value observed several hours earlier does not prove that the link is still operational.

#### Topology and adaptation properties

Useful topology properties may include:

- source and destination ports;
- owning domain;
- optical, Ethernet, or IP layer;
- physical-link, logical-link, or tunnel type;
- supported VLAN range;
- MTU;
- encoding and encapsulation;
- label-switching support;
- adaptation between network layers;
- shared-risk group;
- shared physical resources with other logical links.

These properties determine whether adjacent links can be composed and whether the resulting path can carry the requested service.

For example, two consecutive links with incompatible VLAN ranges cannot carry an end-to-end VLAN that must remain unchanged unless the intermediate system supports VLAN translation:

```text
Link A VLAN range: 100-200
Link B VLAN range: 300-400
```

An MTU mismatch creates a similar problem:

```text
Workflow requirement: MTU 9000
Link A MTU:          9000
Link B MTU:          1500
```

The path is topologically reachable but cannot satisfy the jumbo-frame requirement.

Links at different layers also require explicit adaptation rather than simple adjacency:

```text
IP interface
→ Ethernet service
→ Optical wavelength
```



#### Performance and capacity properties

Relevant attributes may include:

- physical capacity;
- reservable capacity;
- current utilization;
- latency;
- packet loss;
- jitter;
- error rate;
- queue occupancy;
- congestion state.

These values answer different questions.

Physical capacity asks how much traffic a link can carry in total:

```text
physical capacity = 100 Gbps
```

Reservable capacity asks how much can still be promised to a new service after accounting for reservations and policy:

```text
physical capacity   = 100 Gbps
already reserved    = 70 Gbps
reservable capacity = 30 Gbps
```

Utilization measures traffic currently traversing the link:

```text
current utilization = 45 Gbps
```

A link may have 70 Gbps reserved while carrying only 45 Gbps at a particular instant. Reservation state and measured utilization are not interchangeable.

Latency describes how long traffic takes to cross a link or path. Packet loss measures discarded packets. Jitter describes variation in delay. A path with sufficient nominal bandwidth can still perform poorly for TCP or GPU-to-GPU transfers if loss, latency, or queueing is high.

These properties support SLA evaluation, path comparison, bottleneck identification, degradation detection, rerouting, and workflow rescheduling. The public SENSE evidence examined here is stronger for modeled capacity and reservation information than for live performance measurements.

#### Physical link versus abstract link

An apparent adjacency:

```text
A ↔ B
```

does not necessarily mean that A and B are connected by a single cable or fiber.

It may represent a physical connection:

```text
A:port-1 ───── cable/fiber ───── B:port-2
```

It may instead abstract a multi-hop internal path:

```text
A ── Switch X ── Router Y ── Optical Network ── B
```

represented to an upper layer as:

```text
A ═════════ logical link ═════════ B
```

Such a logical link may represent an MPLS tunnel, VLAN circuit, optical circuit, VPN, or a path through an opaque domain.

This distinction matters for failure analysis, bottleneck localization, administrative boundaries, and path independence. Two logical links can appear independent while sharing the same physical fiber:

```text
             ┌─ Logical Link 1 ─┐
A ── Fiber X ┤                  ├─ B
             └─ Logical Link 2 ─┘
```

A failure of Fiber X would break both logical links. Logical diversity does not, by itself, prove physical diversity.

### 1.7 Route sequence and typed schema

A route sequence is the ordered list of nodes, ports, or links traversed by a path. For example:

```text
EP-A
→ Switch-A port 1
→ Switch-A port 8
→ Router-A port 3
→ Domain-A border port
→ Domain-B border port
→ Router-B port 5
→ Switch-B port 2
→ EP-B
```

The same route could be represented as an ordered list of links:

```text
Link 1 → Link 2 → Inter-domain Link → Link 4 → Link 5
```

Order is necessary to determine the traffic flow, ingress and egress of each domain, which links belong to the path, and where a bottleneck occurs. An unordered set of nodes or ports cannot answer those questions.

A typed schema is a structure explicitly declared by the OpenAPI document. For example, `edge_points` is typed because the specification declares it as an array and defines fields such as `ep_uri`, `vlan_pool`, and `capacity` as strings.

A typed route might look like:

```json
{
  "route": {
    "hops": [
      {
        "sequence": 1,
        "node_uri": "switch-a",
        "ingress_port_uri": "port-1",
        "egress_port_uri": "port-8",
        "link_uri": "link-1"
      },
      {
        "sequence": 2,
        "node_uri": "router-a",
        "ingress_port_uri": "port-3",
        "egress_port_uri": "port-7",
        "link_uri": "link-2"
      }
    ]
  }
}
```

`DomainDescription` defines no comparable `nodes`, `links`, `adjacencies`, or `route.hops` structure. This is a limitation of the public response contract, not proof that SENSE's internal semantic model lacks those objects.

## 2. Resource-name and URI resolution

`GET /discover/lookup/{name}` is documented as supporting lookups based on information such as:

- an NML resource name;
- a tag;
- an `mrs:NetworkAddress`;
- a fully qualified domain name.

`GET /discover/lookup/{uri}/rooturi` can identify the root domain or topology URI associated with a resource.

This supports a workflow adapter such as:

```text
Workflow site, host, or endpoint name
                  ↓ lookup
        SENSE terminal URI
                  ↓
      Network service intent
```

However, the lookup endpoint documentation says that it returns URI candidates while the OpenAPI response references `DomainDescription`. This schema/documentation inconsistency should be resolved through testing against the target deployment.

## 3. Network conditions that an application can request

These fields express desired service conditions; they are not observations of the current network.

The primary intent submission endpoint is:

```http
POST /instance/{siUUID}
```

A typical workflow is:

```text
GET /instance
    ↓ obtain a new service-instance UUID
POST /instance/{siUUID}
    ↓ submit and compile a ServiceIntent
PUT /instance/{siUUID}/provision
    ↓ provision the computed network service
```

For a two-phase workflow, `propagate` followed by `commit` may be used instead of a single `provision` operation. Existing services can be modified with:

```http
POST /instance/{siUUID}/modify
```

The DNC intent schema supports:

- connection types:
  - `Multi-Path P2P VLAN`;
  - `Multi-Point VLAN Bridge`;
  - `Multi-Point L3VPN`;
- terminal URI;
- VLAN tag;
- IPv4 prefix information;
- IP assignment request;
- MAC address list;
- bandwidth capacity;
- QoS class:
  - `guaranteedCapped`;
  - `softCapped`;
  - `anyAvailable`;
  - `bestEffort`;
- connection start, end, and duration;
- included and excluded path URIs.

The OpenAPI description explicitly defines `bandwidth.capacity` as a **bandwidth limit in Mbps**. Its name alone does not mean current availability, remaining bandwidth, observed throughput, or a minimum guaranteed rate. The effective meaning also depends on the requested QoS class.

### 3.1 Submitting a complete intent

The client first obtains a new service-instance UUID:

```http
GET /instance
```

An example response is:

```text
3b7d41e1-b37f-4c64-84d2-d307b5e47370
```

The application then submits its network requirements as the body of:

```http
POST /instance/3b7d41e1-b37f-4c64-84d2-d307b5e47370?sync=true&proceed=false
Content-Type: application/json
Authorization: Bearer <token>
```

A complete DNC `ServiceIntent` can take the following form:

```json
{
  "service": "dnc",
  "alias": "science-transfer-a-to-b",
  "data": {
    "type": "Multi-Path P2P VLAN",
    "connections": [
      {
        "name": "Connection 1",
        "terminals": [
          {
            "uri": "urn:ogf:network:site-a:endpoint-1",
            "vlan_tag": "any",
            "ipv4_prefix_list": "192.0.2.0/30",
            "assign_ip": false,
            "mac_address_list": "a4:55:12:0e:50:49"
          },
          {
            "uri": "urn:ogf:network:site-b:endpoint-2",
            "vlan_tag": "any",
            "assign_ip": false
          }
        ],
        "bandwidth": {
          "capacity": "10000",
          "qos_class": "guaranteedCapped"
        },
        "schedule": {
          "start": "now",
          "duration": "2h"
        },
        "path_tprofile": {
          "inclusion_list": [
            {
              "uri": "urn:ogf:network:some-required-path"
            }
          ],
          "exclusion_list": [
            {
              "uri": "urn:ogf:network:some-forbidden-path"
            }
          ]
        }
      }
    ]
  }
}
```

The JSON object is the HTTP request body; there is no separate file-upload endpoint. If the intent is stored locally as `intent.json`, it can be submitted with:

```bash
curl -X POST \
  "https://<SENSE-host>/instance/<siUUID>?sync=true&proceed=false" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  --data @intent.json
```

`POST /instance/{siUUID}` creates an intent under the service instance and starts its validation and compilation workflow. It does not necessarily mean that the network configuration has already been installed.

### 3.2 Provisioning the compiled intent

In the combined workflow, a successfully compiled intent is normally provisioned with:

```http
PUT /instance/{siUUID}/provision?sync=true&intent=last
```

This is an instance of the generic operation endpoint:

```http
PUT /instance/{siUUID}/{action}
```

The OpenAPI `Operation` enum includes:

```text
provision
cancel
reprovision
propagate
release
reinstate
commit
rollback
archive
unarchive
verify
unverify
reset
```

The two-phase workflow uses separate preparation and commit steps, which is useful when network and non-network resources must be co-scheduled.

### 3.3 Reusable service profiles

An application may submit a complete intent directly or instantiate a reusable service profile. `POST /profile` creates the reusable template; it is not the ordinary endpoint for each network-service request.

A profile can define:

- the service type and basic connection structure;
- default terminals and QoS behavior;
- which fields a user may edit;
- validation rules for editable fields;
- authorization and license information.

After a profile has been created, a service request still goes to:

```http
POST /instance/{siUUID}
```

The request references the template with `service_profile_uuid` and edits permitted fields through `queries[]`:

```json
{
  "service": "dnc",
  "alias": "science-transfer-a-to-b",
  "service_profile_uuid": "456225c4-c549-4ca0-a585-a84247541315",
  "queries": [
    {
      "ask": "edit",
      "options": [
        {
          "data.connections[0].terminals[0].uri": "urn:ogf:network:site-a:endpoint-1",
          "data.connections[0].terminals[1].uri": "urn:ogf:network:site-b:endpoint-2",
          "data.connections[0].bandwidth.capacity": "10000"
        }
      ]
    }
  ]
}
```



### 3.4 Modifying an existing service

An existing service instance can be recompiled with new requirements through:

```http
POST /instance/{siUUID}/modify
```

The request body is again a `ServiceIntent`. For example, a profile-based request could change the desired capacity to 20 Gbps:

```json
{
  "service": "dnc",
  "alias": "science-transfer-a-to-b",
  "service_profile_uuid": "456225c4-c549-4ca0-a585-a84247541315",
  "queries": [
    {
      "ask": "edit",
      "options": [
        {
          "data.connections[0].bandwidth.capacity": "20000"
        }
      ]
    }
  ]
}
```



## 4. Existing service and lifecycle information

The API can expose existing service instances and their intent or lifecycle state. Relevant operations include:

- `GET /discover/service/instances`: list visible service instances;
- `GET /instance/{siUUID}/status`: retrieve the full instance state;
- `GET /instance/{siUUID}/substatus`: retrieve the backend substate;
- `GET /intent/{uuid}`: retrieve a submitted intent and provisioning information;
- `GET /instance/{siUUID}/verify`: retrieve model-addition and model-reduction verification results.

These interfaces provide orchestration, provisioning, and model-verification evidence. They do not provide network-performance telemetry.

A service-instance listing can include information such as:

```json
{
  "instances": [
    {
      "type": "Dynamic Network Connection",
      "intents": [
        {
          "id": "a8848755-39cc-44db-a0ab-dc99f9daffcc",
          "json": "string",
          "provisioned": true,
          "creation_time": "Jun 21, 2021, 1:59:01 PM",
          "serviceInstanceUUID": "59e9624b-48e0-48dd-95b9-8c020046dffa",
          "serviceDeltaUUID": "875ceb85-7a03-4799-a8dd-23d7b883d527"
        }
      ],
      "alias": "DNC Pilot",
      "referenceUUID": "59e9624b-48e0-48dd-95b9-8c020046dffa",
      "state": "CANCEL - COMMITTING",
      "owner": "admin",
      "lastState": "PROPAGATED",
      "verification": "INIT",
      "timestamp": "2021/06/21 17:59:01",
      "archived": true
    }
  ]
}
```

Fields such as `state`, `lastState`, `provisioned`, and `verification` describe the control and provisioning lifecycle. They do not report current link health, congestion, or achieved data-transfer performance.

## 5. Questions resolved by inspecting the official client and workflow examples



### 5.1 Feasible-path and maximum-reservable-bandwidth query

The official interactive workflow submits the following query within a `ServiceIntent`:

```json
{
  "queries": [
    {
      "ask": "edit",
      "options": [
        {
          "data.connections[0].bandwidth.capacity": "0"
        }
      ]
    },
    {
      "ask": "total-block-maximum-bandwidth",
      "options": [
        {
          "name": "Connection 1",
          "start": "now",
          "end-before": "+1h"
        }
      ]
    }
  ]
}
```

The client describes this operation as computing a feasible path and determining the maximum bandwidth reservable on that path during the specified time period. It extracts the result from:

```text
$.queries[*].results[*].bandwidth
```

The example divides the returned value by `1,000,000` to display Mbps, indicating that this query result is treated as bits per second.

This confirms that SENSE can answer:

> For the specified endpoints and time window, does a feasible path exist, and what is the maximum bandwidth that the model allows the application to reserve on that path?

This is reservation-aware model information. It is not instantaneous link utilization or measured throughput.

The client also warns that a request below the reported maximum may still be rejected by a SiteRM because of local constraints—for example, a requirement that bandwidth be divisible by 1 Gbps. The returned maximum is therefore not the only feasibility condition.

### 5.2 Service-resource readback through manifests

The official client supports service-instance manifests built from JSON templates containing SPARQL queries. The public OpenAPI describes:

```http
POST /service/manifest/{siUUID}
```

The newer client also contains a `/service/manifest/{siUUID}/json` variant. The exact endpoint supported by a deployment must be verified.

Official manifest examples query service-model information such as:

- terminals and switching subnets;
- bidirectional ports;
- VLAN tags;
- IPv4 addresses;
- host-port aliases;
- QoS type;
- `mrs:availableCapacity` and its unit;
- service start and end times.

For example:

```sparql
?terminal nml:hasService ?bw_svc.
?bw_svc mrs:type ?qos_type.
?bw_svc mrs:availableCapacity ?bw_available.
?bw_svc mrs:unit ?bw_unit.
```

and:

```sparql
?subnet nml:existsDuring ?lifetime.
?lifetime nml:start ?start.
?lifetime nml:end ?end.
```

This confirms that computed or provisioned service resources can be read back from the semantic service model without directly parsing the opaque `ServiceIntentResponse.model` string.

### 5.3 Modeled path ports, capacities, and VLAN allocations

The official utility implements:

```text
--troubleshoot path-bandwidth -u <service-instance-uuid>
```

It submits a manifest query for `nml:BidirectionalPort` objects associated with the service path. For each path port, it queries:

```text
mrs:reservableCapacity
mrs:unit
```

It also queries VLAN sub-ports and their modeled bandwidth allocations. The client normalizes units to bits per second and computes:

```text
Remaining Capacity = Port Capacity - VLAN sub-port allocations
```

This demonstrates that an application can inspect, at least through the service model:

- ports associated with a computed or provisioned service path;
- modeled capacity of those ports;
- VLAN sub-port allocations;
- a client-computed remaining capacity.

The result should be described as model- and reservation-based capacity. It is not a direct reading of live router interface counters.

### 5.4 Provisioning and configuration state

The client can inspect orchestration state and configuration state. Configuration values used by the example include:

```text
UNKNOWN
EXPIRED
STABLE
```

`STABLE` indicates that the data-plane configuration has reached a stable configuration state. It does not prove that throughput, latency, packet loss, or congestion satisfies the workflow's performance requirements.

### 5.5 The opaque `model` field is not a stable application interface

The OpenAPI defines `ServiceIntentResponse.model` only as a string and does not define its internal structure. The official CLI removes the field by default unless verbose output is requested:

```python
if not args.verbose and "model" in response:
    response.pop("model")
```

No official example was found that treats this opaque string as a stable application-level topology or path schema. Applications should prefer query results and manifest templates over parsing this field directly.

The verification fields `verified_reduction`, `verified_addition`, `unverified_reduction`, and `unverified_addition` are also opaque model strings. They report whether requested model changes were verified; they are not RTT, loss, or throughput measurements.

## 6. Questions that remain unresolved



### 6.1 Complete internal topology

No stable SENSE-O Northbound typed endpoint was found that returns all internal nodes, ports, links, and adjacency relationships for all domains as a complete graph.

Service manifests can expose resources related to a particular service instance, but that does not establish that an application can retrieve the entire global topology. The official client also contains direct SiteRM model APIs, but those belong to a different API layer with potentially different authorization and visibility boundaries.

### 6.2 Complete ordered selected route

The `path-bandwidth` manifest can return ports associated with a service path, but the inspected query does not provide:

- explicit hop numbers;
- ordered ingress/egress transitions;
- the link connecting each adjacent pair of ports;
- the node owning each hop;
- distinct forward and reverse route sequences.

The available evidence therefore supports “a set of modeled ports associated with the selected service path,” not a complete and ordered hop-by-hop route.

### 6.3 Physical underlay and path independence

A modeled link or service path may abstract over switches, routers, MPLS tunnels, optical circuits, or opaque domain internals. The Northbound evidence does not expose enough physical detail to determine whether two logical paths share the same fiber, optical system, device, or failure domain.

This limits direct use of the API for physical-path diversity and shared-risk analysis.

### 6.4 Real-time utilization and congestion telemetry

No Northbound typed endpoint was found for:

- current transmit or receive rate;
- interface counters;
- link utilization;
- queue occupancy;
- congestion state;
- utilization timestamps or time series.

`reservableCapacity`, `availableCapacity`, and client-computed remaining capacity must not be conflated with live utilization.

### 6.5 Latency, loss, jitter, and actual throughput

No stable Northbound response or official manifest example was found for continuous:

- one-way latency;
- RTT;
- packet loss;
- jitter;
- packet reordering;
- error rate;
- application throughput.

The official client contains a separate SiteRM Debug API with actions such as `rapid-ping`, `rapid-pingnet`, `traceroute`, `iperf-client`, `iperf-server`, and `tcpdump`. This does not establish a unified Northbound telemetry capability because:

- the debug API belongs to the SiteRM layer;
- supported actions are site-specific and dynamically discovered;
- workflow access permissions are not established;
- a common result schema has not been verified;
- one-off diagnostic tests are not continuous telemetry.



### 6.6 Exact semantics of discovery capacity fields

The precise semantics of `edge_points[].capacity`, `peer_points[].port_capacity`, and `peer_points[].peer_capacity` remain unclear. The OpenAPI supplies no unit, direction, timestamp, update frequency, or physical/reservable/available classification for these fields.

Although intent `bandwidth.capacity` is explicitly in Mbps, that definition must not be transferred automatically to the discovery capacity fields.

### 6.7 Deployment-specific API and authorization behavior

The following items require tests against the actual target deployment:

- base URL and deployed API version;
- OAuth/Keycloak roles;
- profiles visible to the workflow account;
- permission to submit custom manifest/SPARQL templates;
- permission to query modeled path ports;
- access to direct SiteRM APIs;
- debug actions supported by each SiteRM;
- actual query-result and manifest JSON formats;
- capacity units and update cadence;
- topology filtering based on authorization.



## 7. Capability matrix


| Network information                            | Finding                                    | Interface or evidence                      |
| ---------------------------------------------- | ------------------------------------------ | ------------------------------------------ |
| Domains                                        | Confirmed                                  | Discovery API                              |
| Domain edge and peer points                    | Confirmed                                  | Discovery API                              |
| Endpoint URI and name                          | Confirmed                                  | Discovery API                              |
| Advertised VLAN and IPv4 pools                 | Confirmed                                  | Discovery API                              |
| Discovery capacity values                      | Present, but semantics are incomplete      | Discovery API                              |
| Resource-name-to-URI resolution                | Declared, response format requires testing | Lookup API                                 |
| Connection type and terminal constraints       | Confirmed                                  | `ServiceIntent`                            |
| VLAN, IP, and MAC constraints                  | Confirmed                                  | `ServiceIntent`                            |
| Requested bandwidth and QoS                    | Confirmed                                  | `ServiceIntent`                            |
| Schedule and include/exclude path constraints  | Confirmed                                  | `ServiceIntent`                            |
| Feasible-path computation                      | Confirmed by official client workflow      | Intent query                               |
| Maximum reservable bandwidth for a time window | Confirmed                                  | `total-block-maximum-bandwidth` query      |
| Service terminals, VLAN, IP, QoS, and schedule | Confirmed                                  | Service manifest                           |
| Modeled ports associated with a service path   | Confirmed                                  | `path-bandwidth` manifest                  |
| Modeled port capacity and VLAN allocation      | Confirmed                                  | `path-bandwidth` manifest                  |
| Provisioning and configuration state           | Confirmed                                  | Instance status/configuration APIs         |
| Complete internal domain topology              | Not established                            | No Northbound typed schema found           |
| Complete ordered route sequence                | Not established                            | Path-port query lacks hop order            |
| Physical underlay and shared-risk information  | Not established                            | No supporting Northbound evidence found    |
| Real-time link utilization                     | Not established                            | No Northbound telemetry endpoint found     |
| Queue occupancy and congestion telemetry       | Not established                            | No Northbound telemetry endpoint found     |
| RTT, one-way latency, loss, and jitter         | Not established in the Northbound API      | SiteRM debug is separate and site-specific |
| Actual end-to-end throughput                   | Not established in the Northbound API      | Requires measurement                       |
| Unified time-series telemetry                  | Not established                            | No supporting Northbound endpoint found    |


