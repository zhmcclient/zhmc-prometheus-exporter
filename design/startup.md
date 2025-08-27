# Basic flow in the exporter

Applies to version 2.1.0.

## Startup

* Parse arguments
* Parse exporter config file
* Parse metric definition file
* Create session with the HMC
  - "Logon"
* Get HMC info
  - "Query API Version"
* List API features of the HMC
  - "List Console API Features"
* List managed CPCs
  - "List CPC Objects"
  - Returns the accessible CPCs
* Check that "cpcs" config property does not specify unknown CPCs
* Define the set of cpcs based on the "cpcs" config property. We refer to
  that as `cpc_list`.
* For each CPC in `cpc_list`:
  * List API features of the CPC
    - "List CPC API Features"
* Create metrics context
  - With `cpc_list`
  - "Create Metrics Context"
* Create `ResourceCache()`
* Create `ZHMCUsageCollector()`
  - knows about `ResourceCache`
* Register the collector and perform first collection
  - see [Collection](#collection)
* Start HTTP server for Prometheus
* Start resource fetch thread
  - See [Fetch thread](#fetch thread)
  - Handles resource updates for resources / properties that do not support
    update notifications.
* Log message: "Exporter is up and running"

## Collection

Collection is performed by Prometheus calling the API provided by the
HTTP server. This causes a call into `ZHMCUsageCollector.collect()`.

Prometheus performs this call as configured (e.g. every 30 seconds).

`ZHMCUsageCollector.collect()`:

* Log message "Collecting metrics"
* Loop until successful:
  * Get Metrics from HMC
    - call `retrieve_metrics()`
* Log message: "Building family objects for HMC metrics"
* Call `build_family_objects()`
* Log message: "Building family objects for resource metrics"
* Call `build_family_objects_res()`
* Log message: "Returning family objects"
* Yield family objects (back to Prometheus)
* Log message: "Done collecting metrics"

`retrieve_metrics()`:

TBD

`build_family_objects()`:

TBD

`build_family_objects_res()`:

TBD

## Resource data kept in the exporter

There are several places where resource data is kept (cached) in the exporter:

* Attributes of the `ZHMCUsageCollector` object:

  * `self.resources` and `self.uri2resource`:

    These attributes are used only for resource metric groups.
    Both attributes contain the same (= same object ID) zhmcclient resource
    objects, for resource metric groups that are enabled, for only the CPCs
    on `cpc_list`. These resource objects are all auto-update enabled.

    `self.resources` is a dict with key = metric group name, value = list of
    zhmcclient resource objects for the resources defined in enabled resource
    metric groups.

    `self.uri2resource` is a dict with key = resource URI, value = zhmcclient
    resource object for the resources defined in enabled resource metric
    groups.

    The zhmcclient resource objects in these attributes are:
      - For the "partition-resource" metric group: All (accessible) partitions
        on all CPCs in `cpc_list`.
      - For the "storagegroup-resource" metric group: All (accessible) storage
        groups.
        TODO: Optimization: This should be reduced to only the storage
        groups associated with the CPCs in `cpc_list`.
      - For the "storagevolume-resource" metric group: All storage volumes in
        all (accessible) storage groups.
        TODO: Optimization: This should be reduced to only the storage
        groups associated with the CPCs in `cpc_list`.
      - For the "adapter-resource" metric group: All (accessible) adapters on
        all CPCs in `cpc_list`.
      - For the "cpc-resource" metric group: All (accessible) CPCs in
       `cpc_list`.

  * `self.resource_cache`

    This attribute is used only for HMC metric groups.

    It is a `ResourceCache` object where resources can be looked up by URI.
    The resource URIs are provided in the retrieved metric data, and
    the `ResourceCache.resource()` method looks up the resource by URI, or
    if not yet in the cache, finds the resource on the HMC based on the URI
    and puts it into the cache.

    The resource objects in the cache are zhmcclient resource objects.
    They are not auto-update enabled.

    TODO: Optimization: Finding the resources on the HMC is done resource by
    resource. It would be more efficient to list the resources once.

## Fetch thread

The fetch thread runs forever. It fetches data for resources or properties that
do not support update notifications.

The fetch thread has a loop where it waits for a variable sleep time
and then performs the actual fetches.

The sleep time is adjusted according to the intervals in which Prometheus
fetches the data.

`run_fetch_thread()`

* Determine properties to be fetched from `ZHMCUsageCollector.yaml_fetch_properties`.

  That property has been set up during startup and contains the "fetch_properties"
  property from the metric definition file.
  That property defines these resource classes:
  - cpc
    - some properties depend on the HMC or SE version
    - a total of 11 properties on a z16 CPC
  - logical-partition
    - some properties depend on the HMC or SE version
    - a total of 22 properties on a z16 CPC

* Fetch the LPAR properties:
  It does that by using single call to `console.list_permitted_lpars()`
  where `additional_properties` is set to the LPAR properties that are needed.

  TODO: This returns data for LPARs that are not in the `cpc_list`. Optimize.

* Fetch the CPC properties:
  It does that by looping through the `cpc_list`, and for each CPC, it
  performs `cpc.pull_properties(cpc_props)` to retrieve only the properties
  that are needed, from only the CPCs that are needed.

* Adjust the sleep time
  - Log message "Increasing/Decreasing sleep time for fetching properties in background"

* Update properties of the local resource objects from the fetch results
  * `ZHMCUsageCollector.uri2resource`
  * `ZHMCUsageCollector.resources`
