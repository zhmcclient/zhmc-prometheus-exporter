# Copyright 2025 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A resource cache for the IBM Z HMC Prometheus Exporter.
"""

import re
import logging
import zhmcclient
import zhmcclient_mock

from ._logging import PRINT_V, PRINT_VV, PRINT_ALWAYS, logprint
from ._exceptions import InvalidMetricDefinitionFile


class ResourceCache:
    # pylint: disable=too-many-instance-attributes,line-too-long
    """
    A resource cache for the exporter.

    This is the only resource cache in the exporter. It contains the
    zhmcclient resource objects for all use cases:

    * To resolve the resource URIs returned by the HMC metric service into
      zhmcclient resource objects.
    * To know which resources provide resource-based metric groups, and to get
      their properties.
    * To get the properties of resources for use in metric labels.

    The resource objects in the cache are:

    * The resource objects that are defined as resource classes of enabled
      metric groups, for the target CPCs.
    * The direct and indirect parent objects of these resource objects for the
      target CPCs, because the metric labels are defined to show the names of
      parent resources.
    * Additional resources referenced by the metric labels, for the target CPCs.
    * The resources of non-target CPCs for enabled metric-based metric groups,
      because the HMC metric service does not allow to filter its results by
      CPC and the cache needs to support resolving all returned resource URIs
      in order to determine whether the returned metric value is for a target
      CPC.

    The different resource classes in the cache are used as follows:

    Resource class      Metric   Resource   Labels   Dependents
                        based    based
    ---------------------------------------------------------------------------
    cpc                 Yes      Yes        Yes      -
    adapter             Yes      Yes        Yes      cpc
    logical-partition   Yes      Yes        Yes      cpc
    partition           Yes      Yes        Yes      cpc,storage-group
    nic                 Yes      No         Yes      cpc,partition
    virtual-switch      No       No         No (1)   part.,adapter,port,vswitch
    port (2)            No       No         Yes      cpc,adapter
    storage-group       No       Yes        Yes      cpc
    storage-volume      No       Yes        Yes      cpc,sto-grp

    (1) The vswitch resource is needed up to z16 CPCs to find the backing
        adapter of a NIC.
    (2) The resource class names in the actual resource objects are
        'storage-port' and 'network-port', but the cache stores them together
        and uses the artificial resource class name 'port'.

    The resource objects in the cache that are used for at least one enabled
    resource-based metric group will be auto-update enabled. All other
    zhmcclient resource objects in the cache are not auto-update enabled.
    This means that resources used for labels will not always be auto-update
    enabled, but that typically affects only the resource name.

    Where possible, the zhmcclient resource objects in the cache have only the
    minimal set of properties that is needed:

    Resource class      Without auto-update                  With auto-update
    -------------------------------------------------------------------------
    cpc                 as prepared in cpc_list              all
    adapter             from List HMC operation              all
    logical-partition   from List HMC operation              all
    partition           from List HMC operation + nic-uris   all
    nic                 all (1)                              N/A
    virtual-switch      from List HMC operation              N/A
    port                all (1)                              N/A
    storage-group       N/A                                  all
    storage-volume      N/A                                  all

    (1) For element objects, there is no List HMC operation, so the zhmcclient
        'list()' method returns all properties, since it needs to loop through
        the referenced element objects anyway.

    Object access permissions are handled by the cache such that objects without
    access are stored in the all-resources dict with a None value, so that the
    cache remembers that they are inaccessible and does not retry fetching them
    over and over again.
    """  # noqa: E501

    def __init__(self, client, all_cpc_list, target_cpc_list, mdf_metric_groups,
                 exported_mg_names, se_features_by_cpc):
        """
        Parameters:

          client (zhmcclient.Client): Client object used for communicating
            with the HMC. This object will get all the cached resources
            added.

          all_cpc_list (list of zhmcclient.Cpc): All managed CPCs.

          target_cpc_list (list of zhmcclient.Cpc): Target CPCs for which
            metrics are to be exported. The target CPCs can be defined in the
            exporter config file.

          mdf_metric_groups (dict): All metric groups from the metric definition
            file (i.e. the value of the 'metric_groups' item in the file).

          exported_mg_names (list of str): Names of the metric groups that
            are set to be exported in the exporter config file. This includes
            both metric-based and resource-based metric groups.

          se_features_by_cpc (dict): Names of SE API features for each CPC.
            Key: CPC name
            Value: List of str: Names of SE API features for the CPC
        """
        self._client = client
        self._all_cpc_list = all_cpc_list
        self._target_cpc_list = target_cpc_list
        self._mdf_metric_groups = mdf_metric_groups
        self._exported_mg_names = exported_mg_names
        self._se_features_by_cpc = se_features_by_cpc

        # Indicator that setup() was called
        self._setup_called = False

        # Some objects for faster access
        self._console = client.consoles.console
        self._session = client.session

        # Target CPC URI list
        #
        # This list is set up to have the same CPCs as in target_cpc_list.
        # This is used to check whether new resource objects are in a target
        # CPC. Note that the set of target CPCs is static over the lifetime of
        # an exporter run.
        #
        # List of str: URI of the CPC.
        self._target_cpc_uri_list = None  # Deferred initialization

        # Auto-update enablement dict
        #
        # This dict is set based on the metric groups that are enabled for
        # export: If the metric groups for a particular resource class has
        # one or more resource-based metric groups, auto-update gets enabled.
        # This dict has only items for resource classes of metric groups that
        # are enabled for export.
        #
        # Key: Resource class.
        # Value: Boolean indicating that auto-update should be enabled for the
        # resource class.
        self._auto_update = {}

        # All-resources dict
        #
        # This dict contains all resources in the cache. This includes
        # accessible resources as well as inaccessible URIs that are returned
        # by the HMC metric service.
        # This dict is used when a global lookup of a resource URI is performed,
        # for example when processing metric-based metrics.
        #
        # Key: Resource URI.
        # Value: zhmcclient.BaseResource if the resource is accessible, or None
        # if the resource is not accessible.
        self._all_resources_by_uri = {}

        # All-resource list dicts
        #
        # These dicts exist for certain resource classes in order to list their
        # resources. Each dict contains all resources of the resource class,
        # for all CPCs.
        #
        # The resource objects in this dict are the same (= same object ID)
        # Python objects as in the all-resources dict. The Python object ID is
        # used as a key in order to save memory and make the lookup faster.
        #
        # Key: Python object ID of the resource object.
        # Value: zhmcclient.BaseResource
        self._all_partitions_by_id = {}
        self._all_storage_groups_by_id = {}

        # Resource-based resource dict
        #
        # This dict contains only the resources needed for resource-based
        # metric groups that are enabled for export and only for the target
        # CPCs. This dict is used when building the family objects to be
        # returned to Prometheus for resource-based metric groups.
        #
        # The resource objects in this dict are the same (= same object ID)
        # Python objects as in the all-resources dict.
        #
        # Key: Metric group name
        # Value: list of zhmcclient.BaseResource
        self._resource_based_resources_by_mg = {}

        # Target CPC resource dict
        #
        # This dict contains the subset of resources in the all-resources dict
        # that are in the target CPCs. This dict is used when processing the
        # data returned by the HMC metric service in order to decide whether a
        # metric belongs to a target CPC.
        #
        # The resource objects in this dict are the same (= same object ID)
        # Python objects as in the all-resources dict. The Python object ID is
        # used as a key in order to save memory and make the lookup faster.
        #
        # Key: Python object ID of the resource object.
        # Value: zhmcclient.BaseResource
        self._target_cpc_resources_by_id = {}

        # Resource class dicts
        #
        # Each of these dicts contains all resources for a particular resource
        # class and only for the target CPCs. These dicts are used for
        # iterating through the resources of a specific resource class.
        #
        # The resource objects in these dicts are the same (= same object ID)
        # Python objects as in the all-resources dict. The Python object ID is
        # used as a key in order to save memory and make the lookup faster.
        #
        # Key: Python object ID of the resource object.
        # Value: zhmcclient.BaseResource
        self._cpcs = {}
        self._adapters = {}
        self._logical_partitions = {}
        self._partitions = {}
        self._nics = {}
        self._vswitches = {}
        self._ports = {}  # Ports of only network and storage adapters
        self._storage_groups = {}
        self._storage_volumes = {}

        # Lookup dict for getting the resource class dict by resource class.
        # Note: For vswitches and ports, there is no lookup needed because
        # they are not a resource of any metric group.
        self._resource_id_dicts = {
            'cpc': self._cpcs,
            'adapter': self._adapters,
            'logical-partition': self._logical_partitions,
            'partition': self._partitions,
            'nic': self._nics,
            'storage-group': self._storage_groups,
            'storage-volume': self._storage_volumes,
        }

    def __repr__(self):
        """
        Show the resources in the cache.
        """
        repr_lines = []
        repr_lines.append(f"{self.__class__.__name__} at 0x{id(self):08x} (")
        for uri, res in self._all_resources_by_uri.items():
            if res is None:
                res_class = "unknown"
                target_str = ""
                auto_str = ""
                res_name = "unknown"
            else:
                res_class = res.__class__.__name__
                for_target_cpc = id(res) in self._target_cpc_resources_by_id
                target_str = "(for target CPC)" if for_target_cpc else ""
                auto_str = "(auto-update)" if res.auto_update_enabled() else ""
                res_name = res.properties.get('name', "(name not fetched)")
            repr_lines.append(
                f"  {uri}: {res_class} {res_name} {auto_str} {target_str}")
        repr_lines.append(")")
        return '\n'.join(repr_lines)

    def _resource_id_dict(self, uri):
        """
        Return the resource class dict for the URI.
        """
        if re.match(r'/api/storage-groups/[a-f0-9\-]+/'
                    r'storage-volumes/[a-f0-9\-]+$', uri):
            return self._storage_volumes
        if re.match(r'/api/storage-groups/[a-f0-9\-]+$', uri):
            return self._storage_groups
        if re.match(r'/api/partitions/[a-f0-9\-]+/nics/[a-f0-9\-]+$', uri):
            return self._nics
        if re.match(r'/api/partitions/[a-f0-9\-]+$', uri):
            return self._partitions
        if re.match(r'/api/logical-partitions/[a-f0-9\-]+$', uri):
            return self._logical_partitions
        if re.match(r'/api/adapters/[a-f0-9\-]+$', uri):
            return self._adapters
        if re.match(r'/api/adapters/[a-f0-9\-]+/'
                    r'(network|storage)-ports/[a-f0-9\-]+$', uri):
            return self._ports
        if re.match(r'/api/cpcs/[a-f0-9\-]+/virtual-switches/[a-f0-9\-]+$',
                    uri):
            return self._vswitches
        if re.match(r'/api/cpcs/[a-f0-9\-]+$', uri):
            return self._cpcs
        raise ValueError(f"Invalid URI for detecting resource dict: {uri}")

    def _enable_auto_update(self, resource, res_kind, res_name):
        """
        Enable auto-update for the specified resource.

        Test mode: If the session is a zhmcclient_mock (faked) session,
        no auto-update enablement is performed, because the STOMP connection
        in zhmcclient has no mock support.
        """
        if isinstance(self._session, zhmcclient_mock.FakedSession):
            logprint(
                logging.INFO, PRINT_V,
                "Test mode: Ignoring enablement of auto-update for "
                f"{res_kind} {res_name}")
            return

        logprint(
            logging.DEBUG, PRINT_VV,
            f"Enabling auto-update for {res_kind} {res_name}")
        try:
            resource.enable_auto_update()
        except zhmcclient.Error as exc:
            logprint(
                logging.ERROR, PRINT_ALWAYS,
                "The metric values of resource-based metric groups using "
                f"{res_kind} {res_name} will not be updated because "
                "enabling auto-update for it failed with "
                f"{exc.__class__.__name__}: {exc}")

    @staticmethod
    def _needs_auto_update(mg_items):
        """
        Return boolean indicating whether the set of metric groups needs
        auto-update enabled.

        That is the case when at least one of the metric groups is
        resource-based.
        """
        if mg_items:
            for mg_item in mg_items:
                if mg_item['type'] == 'resource':
                    return True
        return False

    def _setup_cpcs(self, mg_items_by_rc):
        """
        Setup for resource class 'cpc'.

        This is called during setup() when metric groups for that resource
        class are enabled for export, or when this resource class is a
        dependency for other resource classes.
        """
        self._auto_update['cpc'] = \
            self._needs_auto_update(mg_items_by_rc.get('cpc'))
        if not self._cpcs:
            for cpc in self._all_cpc_list:
                self._add_cpc(cpc)

    def _setup_adapters(self, mg_items_by_rc):
        """
        Setup for resource class 'adapter'.

        This is called during setup() when metric groups for that resource
        class are enabled for export, or when this resource class is a
        dependency for other resource classes.
        """
        self._auto_update['adapter'] = \
            self._needs_auto_update(mg_items_by_rc.get('adapter'))
        if not self._adapters:
            self._setup_cpcs(mg_items_by_rc)
            for cpc in self._all_cpc_list:
                logprint(
                    logging.DEBUG, PRINT_VV,
                    f"Listing adapters of CPC {cpc.name}")
                adapters = cpc.adapters.list()
                for adapter in adapters:
                    self._add_adapter(adapter)

    def _setup_logical_partitions(self, mg_items_by_rc):
        """
        Setup for resource class 'logical-partition'.

        This is called during setup() when metric groups for that resource
        class are enabled for export, or when this resource class is a
        dependency for other resource classes.
        """
        self._auto_update['logical-partition'] = \
            self._needs_auto_update(mg_items_by_rc.get('logical-partition'))
        if not self._logical_partitions:
            self._setup_cpcs(mg_items_by_rc)
            for cpc in self._all_cpc_list:
                if cpc.dpm_enabled:
                    continue
                logprint(
                    logging.DEBUG, PRINT_VV,
                    f"Listing LPARs of classic-mode CPC {cpc.name}")
                lpars = cpc.lpars.list()
                for lpar in lpars:
                    self._add_logical_partition(lpar)

    def _setup_partitions(self, mg_items_by_rc):
        """
        Setup for resource class 'partition'.

        This is called during setup() when metric groups for that resource
        class are enabled for export, or when this resource class is a
        dependency for other resource classes.
        """
        self._auto_update['partition'] = \
            self._needs_auto_update(mg_items_by_rc.get('partition'))
        if not self._partitions:
            self._setup_cpcs(mg_items_by_rc)
            self._setup_storage_groups(mg_items_by_rc)
            for cpc in self._all_cpc_list:
                if not cpc.dpm_enabled:
                    continue
                logprint(
                    logging.DEBUG, PRINT_VV,
                    f"Listing partitions of DPM-mode CPC {cpc.name}")
                # While listing, get the URI props for possibly exported
                # element child objects into the cached resource
                if self._client.version_info() >= (4, 1):
                    partitions = cpc.partitions.list(
                        additional_properties=["nic-uris"])
                else:
                    partitions = cpc.partitions.list()
                for partition in partitions:
                    self._add_partition(partition)

    def _setup_nics(self, mg_items_by_rc):
        """
        Setup for resource class 'nic'.

        This is called during setup() when metric groups for that resource
        class are enabled for export, or when this resource class is a
        dependency for other resource classes.
        """
        self._auto_update['nic'] = \
            self._needs_auto_update(mg_items_by_rc.get('nic'))
        if not self._nics:
            self._setup_partitions(mg_items_by_rc)
            self._setup_adapters(mg_items_by_rc)  # for backing adapters
            self._setup_ports(mg_items_by_rc)  # for backing adapters
            self._setup_vswitches(mg_items_by_rc)  # for backing adapters
            for partition in self._all_partitions_by_id.values():
                cpc = partition.manager.parent
                logprint(
                    logging.DEBUG, PRINT_VV,
                    "Listing NICs of partition "
                    f"{cpc.name}.{partition.name}")
                nics = partition.nics.list()
                for nic in nics:
                    self._add_nic(nic)

    def _setup_vswitches(self, mg_items_by_rc):
        """
        Setup for virtual switches.

        This is not needed for metrics, but in order to identify the
        backing adapters of NICs.

        Only vswitches on the target CPCs are added.

        This is called during setup() as a dependency for NIC setup.
        """
        if not self._vswitches:
            self._setup_cpcs(mg_items_by_rc)
            for cpc in self._target_cpc_list:
                if 'network-express-support' not in \
                        self._se_features_by_cpc[cpc.name]:
                    logprint(
                        logging.DEBUG, PRINT_VV,
                        f"Listing vswitches of CPC {cpc.name}")
                    vswitches = cpc.vswitches.list()
                    for vswitch in vswitches:
                        self._add_vswitch(vswitch)

    def _setup_ports(self, mg_items_by_rc):
        """
        Setup for adapter ports.

        This is not needed for metrics, but in order to identify the
        backing adapters of NICs.

        Only ports on the target CPCs are added.

        This is called during setup() as a dependency for NIC setup.
        """
        if not self._ports:
            self._setup_adapters(mg_items_by_rc)
            for adapter in self._adapters.values():
                net_ports = adapter.prop('network-port-uris')
                if net_ports:
                    cpc = adapter.manager.parent
                    logprint(
                        logging.DEBUG, PRINT_VV,
                        "Listing ports of network adapter "
                        f"{cpc.name}.{adapter.name}")
                    ports = adapter.ports.list()
                    for port in ports:
                        self._add_port(port)

    def _setup_storage_groups(self, mg_items_by_rc):
        """
        Setup for resource class 'storage-group'.

        This is called during setup() when metric groups for that resource
        class are enabled for export, or when this resource class is a
        dependency for other resource classes.
        """
        self._auto_update['storage-group'] = \
            self._needs_auto_update(mg_items_by_rc.get('storage-group'))
        if not self._storage_groups:
            self._setup_cpcs(mg_items_by_rc)
            logprint(
                logging.DEBUG, PRINT_VV,
                "Listing storage groups")
            # StorageGroupManager.list() does not support specifying
            # additional properties (e.g. 'storage-volume-uris' )
            storage_groups = self._console.storage_groups.list()
            for sg in storage_groups:
                self._add_storage_group(sg)

    def _setup_storage_volumes(self, mg_items_by_rc):
        """
        Setup for resource class 'storage-volume'.

        This is called during setup() when metric groups for that resource
        class are enabled for export, or when this resource class is a
        dependency for other resource classes.
        """
        self._auto_update['storage-volume'] = \
            self._needs_auto_update(mg_items_by_rc.get('storage-volume'))
        if not self._storage_volumes:
            self._setup_storage_groups(mg_items_by_rc)
            for sg in self._all_storage_groups_by_id.values():
                logprint(
                    logging.DEBUG, PRINT_VV,
                    f"Listing volumes of storage group {sg.name}")
                storage_volumes = sg.storage_volumes.list()
                for sv in storage_volumes:
                    self._add_storage_volume(sv)

    def _add_cpc(self, cpc):
        """
        Add an accessible CPC to the cache.
        """
        self._all_resources_by_uri[cpc.uri] = cpc
        if cpc in self._target_cpc_list:  # comparison by object ID
            self._target_cpc_resources_by_id[id(cpc)] = cpc
            self._cpcs[id(cpc)] = cpc
            if self.is_auto_update('cpc'):
                self._enable_auto_update(cpc, "CPC", cpc.name)

    def _add_adapter(self, adapter):
        """
        Add an accessible adapter to the cache.
        """
        self._all_resources_by_uri[adapter.uri] = adapter
        cpc = adapter.manager.parent
        if cpc in self._target_cpc_list:  # comparison by object ID
            self._target_cpc_resources_by_id[id(adapter)] = adapter
            self._adapters[id(adapter)] = adapter
            if self.is_auto_update('adapter'):
                self._enable_auto_update(
                    adapter, "adapter", f"{cpc.name}.{adapter.name}")

    def _add_logical_partition(self, lpar):
        """
        Add an accessible LPAR to the cache.
        """
        self._all_resources_by_uri[lpar.uri] = lpar
        cpc = lpar.manager.parent
        if cpc in self._target_cpc_list:  # comparison by object ID
            self._target_cpc_resources_by_id[id(lpar)] = lpar
            self._logical_partitions[id(lpar)] = lpar
            if self.is_auto_update('logical-partition'):
                self._enable_auto_update(
                    lpar, "LPAR", f"{cpc.name}.{lpar.name}")

    def _add_partition(self, partition):
        """
        Add an accessible partition to the cache.
        """
        self._all_resources_by_uri[partition.uri] = partition
        self._all_partitions_by_id[id(partition)] = partition
        cpc = partition.manager.parent
        if cpc in self._target_cpc_list:  # comparison by object ID
            self._target_cpc_resources_by_id[id(partition)] = partition
            self._partitions[id(partition)] = partition
            if self.is_auto_update('partition'):
                self._enable_auto_update(
                    partition, "partition", f"{cpc.name}.{partition.name}")

    def _add_nic(self, nic):
        """
        Add a NIC of an accessible partition to the cache.
        """
        self._all_resources_by_uri[nic.uri] = nic
        partition = nic.manager.parent
        cpc = partition.manager.parent
        if cpc in self._target_cpc_list:  # comparison by object ID
            self._target_cpc_resources_by_id[id(nic)] = nic
            self._nics[id(nic)] = nic
            if self.is_auto_update('nic'):
                # Just for safety - there are no resource-based metric groups
                # for NICs.
                self._enable_auto_update(
                    nic, "NIC", f"{cpc.name}.{partition.name}.{nic.name}")
            else:
                nic.pull_properties(
                    ['name', 'virtual-switch-uri',
                     'network-adapter-port-uri'])
            # Add artificial attributes ot the Nic object
            logprint(logging.INFO, PRINT_V,
                     "Getting backing adapter port for NIC "
                     f"{cpc.name}.{partition.name}.{nic.name}")
            adapter_name, port_index = self._get_backing_adapter_info(nic)
            nic.adapter_name = adapter_name
            nic.port_index = port_index

    def _add_vswitch(self, vswitch):
        """
        Add an accessible vswitch to the cache.
        """
        self._all_resources_by_uri[vswitch.uri] = vswitch
        cpc = vswitch.manager.parent
        if cpc in self._target_cpc_list:  # comparison by object ID
            self._target_cpc_resources_by_id[id(vswitch)] = vswitch
            self._vswitches[id(vswitch)] = vswitch

    def _add_port(self, port):
        """
        Add a port of an accessible adapter to the cache.
        """
        self._all_resources_by_uri[port.uri] = port
        adapter = port.manager.parent
        cpc = adapter.manager.parent
        if cpc in self._target_cpc_list:  # comparison by object ID
            self._target_cpc_resources_by_id[id(port)] = port
            self._ports[id(port)] = port

    def _add_storage_group(self, sg):
        """
        Add an accessible storage group to the cache.
        """
        self._all_resources_by_uri[sg.uri] = sg
        self._all_storage_groups_by_id[id(sg)] = sg
        cpc_uri = sg.get_property('cpc-uri')
        cpc = self._all_resources_by_uri[cpc_uri]
        if cpc in self._target_cpc_list:  # comparison by object ID
            self._target_cpc_resources_by_id[id(sg)] = sg
            self._storage_groups[id(sg)] = sg
            if self.is_auto_update('storage-group'):
                self._enable_auto_update(
                    sg, "storage group", f"{sg.name} (CPC {cpc.name})")

    def _add_storage_volume(self, sv):
        """
        Add a storage volume of an accessible storage group to the cache.
        """
        self._all_resources_by_uri[sv.uri] = sv
        sg = sv.manager.parent
        cpc_uri = sg.get_property('cpc-uri')
        cpc = self._all_resources_by_uri[cpc_uri]
        if cpc in self._target_cpc_list:  # comparison by object ID
            self._target_cpc_resources_by_id[id(sv)] = sv
            self._storage_volumes[id(sv)] = sv
            if self.is_auto_update('storage-volume'):
                self._enable_auto_update(
                    sv, "storage volume",
                    f"{sg.name}.{sv.name} (CPC {cpc.name})")
            else:
                # Get the name of the element object into the cached
                # resource object
                sv.pull_properties(['name'])

    def _add_inaccessible(self, uri):
        """
        Add an inaccessible object to the cache.
        """
        self._all_resources_by_uri[uri] = None  # Indicates inaccessible

    def _get_backing_adapter_info(self, nic):
        """
        Return backing adapter and port of the specified NIC.

        Parameters:
          nic (zhmcclient.Nic): The NIC.

        Returns:
          tuple(adapter_name, port_index)
        """
        vswitch_uri = nic.prop('virtual-switch-uri')
        if vswitch_uri:
            # Handle vswitch-based NIC (OSA, HS before z17)
            vswitch = self.lookup(vswitch_uri)
            adapter_uri = vswitch.get_property('backing-adapter-uri')
            adapter = self.lookup(adapter_uri)
            port_index = vswitch.get_property('port')
        else:
            # Handle adapter-based NIC (RoCE, CNA before z17, all since z17)
            port_uri = nic.get_property('network-adapter-port-uri')
            port = self.lookup(port_uri)
            adapter = port.manager.parent
            port_index = port.get_property('index')
        return adapter.name, port_index

    def _setup_target_cpc_uri_list(self):
        """
        Setup the target CPC URI list, if not yet set up.
        """
        if self._target_cpc_uri_list is None:
            self._target_cpc_uri_list = \
                [cpc.uri for cpc in self._target_cpc_list]

    @property
    def resource_based_resources(self):
        """
        dict: The resources for resource-based metric groups that are enabled
        for export.

        * key (str): Metric group name
        * value (list): List of zhmcclient.BaseResource
        """
        return self._resource_based_resources_by_mg

    @property
    def cpcs(self):
        """
        List view of zhmcclient.Cpc: The CPCs in the cache.
        """
        return self._cpcs.values()

    @property
    def adapters(self):
        """
        List view of zhmcclient.Adapter: The adapters in the cache.
        """
        return self._adapters.values()

    @property
    def logical_partitions(self):
        """
        List view of zhmcclient.LogicalPartition: The LPARs in the cache.
        """
        return self._logical_partitions.values()

    @property
    def partitions(self):
        """
        List view of zhmcclient.Partition: The partitions in the cache.
        """
        return self._partitions.values()

    @property
    def nics(self):
        """
        List view of zhmcclient.Nic: The NICs in the cache.
        """
        return self._nics.values()

    @property
    def storage_groups(self):
        """
        List view of zhmcclient.StorageGroup: The storage groups in the cache.
        """
        return self._storage_groups.values()

    @property
    def storage_volumes(self):
        """
        List view of zhmcclient.StorageVolume: The storage volumes in the cache.
        """
        return self._storage_volumes.values()

    def setup(self):
        """
        Set up the cache with resources from the exported metric groups and
        target CPCs.

        The resources will be listed on the HMC and put into the cache.
        Resources that are needed for resource-based metric groups will get
        auto-enabled.
        """

        # Some methods check that so we set it right at the begin
        self._setup_called = True

        mg_items_by_rc = {}  # key: resource class, value: list of mg_items
        for mg_name in self._exported_mg_names:
            mg_item = self._mdf_metric_groups[mg_name]
            resource_class = mg_item['resource_class']
            if resource_class not in mg_items_by_rc:
                mg_items_by_rc[resource_class] = []
            mg_items_by_rc[resource_class].append(mg_item)

        for resource_class in mg_items_by_rc:
            # Note that vswitches and ports are not a resource of any metric
            # group.
            if resource_class == 'cpc':
                self._setup_cpcs(mg_items_by_rc)
            elif resource_class == 'adapter':
                self._setup_adapters(mg_items_by_rc)
            elif resource_class == 'logical-partition':
                self._setup_logical_partitions(mg_items_by_rc)
            elif resource_class == 'partition':
                self._setup_partitions(mg_items_by_rc)
            elif resource_class == 'nic':
                self._setup_nics(mg_items_by_rc)
            elif resource_class == 'storage-group':
                self._setup_storage_groups(mg_items_by_rc)
            elif resource_class == 'storage-volume':
                self._setup_storage_volumes(mg_items_by_rc)
            else:
                new_exc = InvalidMetricDefinitionFile(
                    f"Unknown resource class {resource_class} in a metric "
                    f"group in the metric definition file.")
                new_exc.__cause__ = None  # pylint: disable=invalid-name
                raise new_exc

        for mg_name in self._exported_mg_names:
            mg_item = self._mdf_metric_groups[mg_name]
            mg_type = mg_item['type']
            resource_class = mg_item['resource_class']
            if mg_type == "resource":
                res_list = self._resource_id_dicts[resource_class].values()
                self._resource_based_resources_by_mg[mg_name] = list(res_list)

    def num_resources(self):
        """
        Return the number of all resources in the cache.
        """
        return len(self._all_resources_by_uri)

    def cpc_from_resource(self, resource):
        """
        Return the CPC of the specified resource.

        The CPC of a resource is one of:
        - the resource itself, if it is a CPC.
        - a direct or indirect parent of the resource.
        - if the resource does not have a CPC parent but an associated CPC, the
          associated CPC (for storage groups/volumes).

        If the resource has no CPC, None is returned. This should not happen
        for the resource classes currently supported by the resource cache.

        The setup() method must have been called before calling this method.

        Parameters:

          resource (zhmcclient.BaseResource): The resource.

        Returns:

          zhmcclient.Cpc: The CPC of the resource, or None if the resource
          does not have a CPC.
        """
        assert self._setup_called
        if isinstance(resource, zhmcclient.StorageGroup):
            # Storage groups are not children of CPCs
            sg = resource
            cpc_uri = sg.get_property('cpc-uri')
            return self.lookup(cpc_uri)

        if isinstance(resource, zhmcclient.StorageVolume):
            # Storage groups are not children of CPCs
            sv = resource
            sg = sv.manager.parent
            cpc_uri = sg.get_property('cpc-uri')
            return self.lookup(cpc_uri)

        # Assume the resource is a CPC or has one as a direct or indirect
        # parent.
        cpc = resource
        while True:
            if cpc is None or cpc.manager.class_name == 'cpc':
                return cpc
            cpc = cpc.manager.parent

        return None  # Safe coding - this should never be reached

    def is_for_target_cpc(self, resource):
        """
        Return boolean indicating that the specified resource is for a target
        CPC.

        This method is used to determine whether a metric returned by the HMC
        metric service is for a target CPC.

        The setup() method must have been called before calling this method.

        Parameters:

          resource (zhmcclient.BaseResource): The resource to be tested.
            May be None (= inaccessible).

        Return:

          bool: Boolean indicating that the specified resource is for a target
          CPC.
        """
        assert self._setup_called
        return resource is not None and \
            id(resource) in self._target_cpc_resources_by_id

    def is_auto_update(self, resource_class):
        """
        Return boolean indicating that the specified resource class is enabled
        for auto-update.

        The setup() method must have been called before calling this method.

        Parameters:

          resource_class (str): The resource class to be tested.

        Return:

          bool: Boolean indicating that the specified resource class has metric
          groups that are enabled for export.
        """
        assert self._setup_called
        try:
            return self._auto_update[resource_class]
        except KeyError:
            return False

    def lookup(self, uri):
        """
        Look up the zhmcclient resource object for the specified URI in the
        cache and return it.

        If the resource URI cannot be found in the cache, the resource is
        retrieved from the HMC.

        If the resource URI cannot be found on the HMC, `NotFound` is raised.
        Note that missing object access permissions may be a reason for that.

        The setup() method must have been called before calling this method.

        Parameters:

          uri (str): URI of the resource.

        Returns:

          zhmcclient.BaseResource: zhmcclient resource object.

        Raises:

          zhmcclient.NotFound: The resource URI is not found on the HMC.
        """
        assert self._setup_called
        try:
            return self._all_resources_by_uri[uri]
        except KeyError:
            return self.add(uri)

    def _get_resource_tolerant(self, uri):
        """
        Perform a "Get <resource> Properties" operation on the HMC for the
        specified URI and return the resulting resource properties.

        If the URI cannot be found, we assume it is because of missing object
        access permissions. In that case, None is returned.

        Parameters:

          uri (str): URI of the resource.

        Returns:

          dict: Properties of the resource, or None if the resource cannot be
          found on the HMC.

        Raises:

          Other zhmcclient exceptions
        """
        try:
            props = self._session.get(uri)
        except zhmcclient.HTTPError as exc:
            if exc.http_status == 404 and exc.reason == 1:
                return None
            raise
        return props

    def add(self, uri):
        """
        Find a resource on the HMC and add its zhmcclient resource object to
        the cache.

        If the URI cannot be found on the HMC, NotFound is raised.
        Note that missing object access permissions may be a reason for that.

        The caller must ensure that the URI is for one of the resource classes
        supported by the cache because the use of the URI is optimized for
        performance and invalid resource classes are not fully detected by this
        method.

        The setup() method must have been called before calling this method.

        Parameters:

          uri (str): URI of the resource.

        Returns:

          zhmcclient.BaseResource: zhmcclient resource object.

        Raises:
          zhmcclient.NotFound: The resource URI is not found on the HMC.
        """
        assert self._setup_called
        self._setup_target_cpc_uri_list()

        # The order of URI tests is by decreasing number of resources, so it is
        # optimitzed for the initial setup.

        m = re.match(
            r'(/api/storage-groups/[a-f0-9\-]+)/storage-volumes/[a-f0-9\-]+$',
            uri)
        if m:
            # A new storage volume
            sg_uri = m.group(1)
            sg = self.lookup(sg_uri)  # adds if needed
            if sg is None:
                self._add_inaccessible(uri)
                return None
            sv = sg.storage_volumes.resource_object(uri)
            self._add_storage_volume(sv)
            return sv

        m = re.match(r'/api/storage-groups/[a-f0-9\-]+$', uri)
        if m:
            # A new storage group
            # Storage groups have access permissions, so we check access.
            sg_get_uri = f"{uri}?properties=name,cpc-uri"
            sg_props = self._get_resource_tolerant(sg_get_uri)
            if sg_props is None:
                self._add_inaccessible(uri)
                return None
            sg = self._console.storage_groups.resource_object(uri, sg_props)
            self._add_storage_group(sg)
            return sg

        m = re.match(r'(/api/partitions/[a-f0-9\-]+)/nics/[a-f0-9\-]+$', uri)
        if m:
            # A new NIC
            part_uri = m.group(1)
            part = self.lookup(part_uri)  # adds if needed
            if part is None:
                self._add_inaccessible(uri)
                return None
            nic = part.nics.resource_object(uri)
            self._add_nic(nic)
            return nic

        m = re.match(r'/api/partitions/[a-f0-9\-]+$', uri)
        if m:
            # A new partition
            # Partitions have access permissions, so we check access.
            part_get_uri = f"{uri}?properties=name,parent"
            part_props = self._get_resource_tolerant(part_get_uri)
            if part_props is None:
                self._add_inaccessible(uri)
                return None
            cpc_uri = part_props['parent']
            cpc = self._all_resources_by_uri[cpc_uri]
            part = cpc.partitions.resource_object(uri, part_props)
            self._add_partition(part)
            return part

        m = re.match(r'/api/logical-partitions/[a-f0-9\-]+$', uri)
        if m:
            # A new LPAR
            # LPARs have access permissions, so we check access.
            lpar_get_uri = f"{uri}?properties=name,parent"
            lpar_props = self._get_resource_tolerant(lpar_get_uri)
            if lpar_props is None:
                self._add_inaccessible(uri)
                return None
            cpc_uri = lpar_props['parent']
            cpc = self._all_resources_by_uri[cpc_uri]
            lpar = cpc.lpars.resource_object(uri, lpar_props)
            self._add_logical_partition(lpar)
            return lpar

        m = re.match(r'/api/adapters/[a-f0-9\-]+$', uri)
        if m:
            # A new adapter
            # Adapters have access permissions, so we check access.
            # "Get Adapter Properties" does not support property selection
            ad_props = self._get_resource_tolerant(uri)
            if ad_props is None:
                self._add_inaccessible(uri)
                return None
            cpc_uri = ad_props['parent']
            cpc = self._all_resources_by_uri[cpc_uri]
            ad = cpc.adapters.resource_object(uri, ad_props)
            self._add_adapter(ad)
            return ad

        m = re.match(
            r'(/api/adapters/[a-f0-9\-]+)/(network|storage)-ports/[a-f0-9\-]+$',
            uri)
        if m:
            # A new network or storage port
            adapter_uri = m.group(1)
            ad = self.lookup(adapter_uri)  # adds if needed
            if ad is None:
                self._add_inaccessible(uri)
                return None
            port = ad.ports.resource_object(uri)
            self._add_port(port)
            return port

        m = re.match(
            r'(/api/cpcs/[a-f0-9\-]+)/virtual-switches/[a-f0-9\-]+$', uri)
        if m:
            # A new vswitch
            # Vswitches use the access permissions of the backing adapter, so
            # we check access.
            # "Get V. Switch Properties" does not support property selection
            vswitch_props = self._get_resource_tolerant(uri)
            if vswitch_props is None:
                self._add_inaccessible(uri)
                return None
            cpc_uri = m.group(1)
            cpc = self.lookup(cpc_uri)  # adds if needed
            vswitch = cpc.vswitches.resource_object(uri, vswitch_props)
            self._add_vswitch(vswitch)
            return vswitch

        m = re.match(r'/api/cpcs/[a-f0-9\-]+$', uri)
        if m:
            # A new CPC
            # CPCs have access permissions, so we check access.
            cpc_get_uri = f"{uri}?properties=name"
            cpc_props = self._get_resource_tolerant(cpc_get_uri)
            if cpc_props is None:
                self._add_inaccessible(uri)
                return None
            cpc = self._client.cpcs.resource_object(uri, cpc_props)
            self._add_cpc(cpc)
            return cpc

        raise ValueError(f"Invalid resource class in URI: {uri}")

    def remove(self, uri):
        """
        Remove a resource from the cache.

        This is used when resources are deleted on the HMC. The cache itself
        does not recognize that, so it needs to be told from the outside.

        If the cache does not have a resource for the specified URI, this is
        ignored.

        The setup() method must have been called before calling this method.

        Parameters:

          uri (str): URI of the resource.
        """
        assert self._setup_called
        res_id_dict = self._resource_id_dict(uri)
        try:
            res = self._all_resources_by_uri[uri]
            del self._all_resources_by_uri[uri]
            del self._target_cpc_resources_by_id[id(res)]
            if res_id_dict is self._storage_groups:
                del self._all_storage_groups_by_id[id(res)]
            if res_id_dict is self._partitions:
                del self._all_partitions_by_id[id(res)]
            del res_id_dict[id(res)]
        except KeyError:
            logprint(logging.ERROR, None,
                     "Ignored failure when removing a resource from the cache: "
                     f"URI not found in one of the cache properties: '{uri}'")
