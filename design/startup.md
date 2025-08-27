# Basic flow in the exporter

Applies to version 2.2.0.

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
* Determine the target CPCs based on the "cpcs" config property.
* For each target CPC:
  * Get SE version
    - "Get CPC Properties"
  * List API features of the CPC
    - "List CPC API Features"
* Determine the metric groups enabled for export based on the "metric_groups"
  config property, separately for resource-based and metric-based metric groups.
* If there are metric-based metric groups enabled, create a metrics context
  for them.
  - "Create Metrics Context"
* Create resource cache
  - `ResourceCache()`
* Fetch resources into the resource cache
  - call `ResourceCache.setup()`
* Create collector
  - `ZHMCUsageCollector()`, knows the `ResourceCache`
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
* If there are metric-based metric groups enabled, retrieve metrics from HMC
  * Loop until successful:
    - call `retrieve_metrics()`
  * Log message: "Building family objects for HMC metrics"
  * Call `build_family_objects()`
* Log message: "Building family objects for resource metrics"
* Call `build_family_objects_res()`
* Log message: "Returning family objects"
* Yield family objects (back to Prometheus)
* Log message: "Done collecting metrics"

## Resource data kept in the exporter

There is a single resource cache where resource data is kept in the exporter:

* `ResourceCache`

  - Known by every class/function that needs to access resources

    - `ZHMCUsageCollector` class
    - `expand_group_label_value()` function
    - `expand_metric_label_value()` function
    - `build_family_objects()` function
    - `build_family_objects_res()` function

  - Based on the currently defined metric groups, the cache stores the following
    resource classes for use as metric resources (and for use in label values):

    - cpc
    - adapter
    - logical-partition
    - partition
    - nics
    - storage-group
    - storage-volume

  - In addition, the cache stores the following resource classes for use in
    label values:

    - virtual-switch (only up to z16 CPCs)
    - port (only for network and storage adapters)

    For 'port', the resource class names in the actual resource objects are
    'storage-port' and 'network-port', but the cache stores them together
    and uses the artificial resource class name 'port'.

  - The resource cache knows about dependencies of resources. For example,
    when a metric group for partitions is enabled, it knows that the resource
    objects for the parent CPCs also need to be fetched, so that the processing
    of labels can navigate to the parent resources without having to fetch
    additional resources from the HMC. The dependencies can be seen in the
    `_setup_<resource>()` methods of `ResourceCache`.

  - Object accessibility: If the HMC user does not have object access permission
    to a resource object, the HMC omits it in List operations, or considers
    it as not found when its URI is used in an operation.

    Not each resource class has its own object access permissions in the HMC.
    For example, NIC objects are child element objects of partitions and do
    not have their own access permissions.

    There are cases where the URIs of resources are surfaced that have their
    own object access permissions. For example, partitions and adapters
    have a "parent" property that is the parent CPC, or storage groups have
    a "cpc-uri" property for the associated CPC.

    The resource cache and the rest of the exporter currently tolerates missing
    object access for resources of enabled metric groups and then does not show
    their metrics, but once a resource of an enabled metric group is accessible,
    its direct and indirect parent resources also must be accessible.

  - For more details about the cache, look at the descriptions in the
    `ResourceCache` class.

## Fetch thread

The fetch thread runs forever. It fetches data for resource classes that
are needed for enabled metric groups and do not support update notifications,
only for the target CPCs.

The fetch thread has a loop where it waits for a variable sleep time
and then performs the actual fetches.

The sleep time is adjusted according to the intervals in which Prometheus
fetches the data.

`ZHMCUsageCollector.run_fetch_thread()`

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
  It does that by using single call to `console.list_permitted_lpars()`,
  with filters for the target CPCs and `additional_properties` which is set to
  the LPAR properties that are needed.

* Fetch the CPC properties:
  It does that by looping through the target CPCs. For each CPC, it
  performs `cpc.pull_properties(cpc_props)` to retrieve only the properties
  that are needed.

* Adjust the sleep time
  - Log message "Increasing/Decreasing sleep time for fetching properties in background"

* Update properties of the resources in the resource cache from the fetch results.
