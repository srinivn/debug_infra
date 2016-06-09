import pdb
import json
from contrail_uve import ContrailUVE
from contrail_api import ContrailApi

'''
context_path: list of elements
              element['type']
              element['uuid']

    def get_contrail_info(uuid, uuid_type, config_ip='127.0.0.1', config_port='8082', **kwargs):
    change to
    def get_contrail_info(uuid, uuid_type, config_ip='127.0.0.1', config_port='8082', **kwargs):
    kwargs will have context_path or you make it explicit

    uuid_type is virtual_network, context path has VM or VMI, get agent/control nodes assoicated with it
    uuid_type is virtual_network, context path is empty, goto VN and find all VMI's agent/control nodes
    Same functionality for Security group also...

    while returning contrail_info, Change 'vrouter' to list, earlier I made it to dict
'''

class ContrailUtils(object):

    @staticmethod
    def add_unique_object_in_object_list(object_list, obj, key_field):
        found_obj = False
        for object_item in object_list:
            if obj[key_field] == object_item[key_field]:
                found_obj = True
        if not found_obj:
            object_list.append(obj)

    @staticmethod
    def check_for_vm_vmi_in_context(contrail_info, context_path, config_ip, config_port, analytics_ip, uve_obj, config_api):
        #Check if there is VM/VMI in the context Path
        for element in context_path:
            if element['type'] == 'virtual-machine':
                #vm_uuid = element['uuid']
                fq_name = element['fq_name']
                contrail_info.update(ContrailUtils.get_contrail_vm_info(fq_name, config_ip=config_ip, config_port=config_port,
                                                                        analytics_ip=analytics_ip))
                return True 
            elif  element['type'] == 'virtual-machine-interface':
                vmi_obj = uve_obj.get_object(element['fq_name'], "virtual-machine-interface", select_fields = ['UveVMInterfaceAgent.vm_uuid'])
                vm_uuid = vmi_obj['UveVMInterfaceAgent.vm_uuid']
                fq_name = ':'.join(config_api.post("id-to-fqname", {"uuid": vm_uuid})['fq_name'])
                #fq_name = vm_uuid
                #object_type = 'virtual-machine'
                #where = 'uuid==%s' % (vm_uuid)
                #vm_objs = config_api.get_object_deep(object_type, '', where=where)
                #if vm_objs:
                #    fq_name = ':'.join(vm_objs[0][object_type]['fq_name'])
                contrail_info.update(ContrailUtils.get_contrail_vm_info(fq_name, config_ip=config_ip, config_port=config_port,
                                                                        analytics_ip=analytics_ip))
                return True
        return False 


    @staticmethod
    def get_contrail_info_v2(uuid, uuid_type, config_ip='127.0.0.1', config_port='8082', **kwargs):
        pdb.set_trace()
        #get the vrouter and control data
        contrail_control_agent_info = ContrailUtils.get_contrail_info(uuid,
                                                                uuid_type,
                                                                config_ip,
                                                                config_port)
        #get the list of all nodes from the config
        contrail_role_info = ContrailUtils.get_contrail_nodes(config_ip, config_port)
        #Plug detailed contrail vrouter info here
        contrail_role_info['virtual_routers'] = contrail_control_agent_info['vrouter']

        return contrail_role_info 



    @staticmethod
    def get_control_nodes(config_ip='127.0.0.1', config_port='8082'):
        contrail_info = ContrailUtils.get_contrail_nodes(config_ip, config_port)
        contrail_info.pop('vrouters')
        return contrail_info
           

    @staticmethod
    def get_contrail_info(uuid, uuid_type, config_ip='127.0.0.1', config_port='8082', **kwargs):
#        _agent_schema_dict = {
#            'virtual-network' : 'virtual_machine_interface_back_refs.virtual_machine_refs.uuid',
#            'floating-ip': 'virtual_machine_interface_refs.virtual_machine_refs.uuid',
#            'security-group' : 'virtual_machine_interface_back_refs.virtual_machine_refs.uuid',
#            'virtual-machine-interface': 'virtual_machine_refs.uuid'
#        }
        _agent_schema_dict = {
            'virtual-network' : 'virtual_machine_interface_back_refs.virtual_machine_refs',
            'floating-ip': 'virtual_machine_interface_refs.virtual_machine_refs',
            'security-group' : 'virtual_machine_interface_back_refs.virtual_machine_refs',
            'virtual-machine-interface': 'virtual_machine_refs'
        }


        contrail_info = {'vrouter': [], 'control': []}
        analytics_ip = kwargs.get('analytics_ip', None)
        analytics_port = kwargs.get('analytics_port', '8081')
        #Could be a list of dict
        context_path = kwargs.get('context_path', [])
        fq_name = kwargs.get('fq_name', None)
 
        if not analytics_ip:
            contrail_nodes = ContrailUtils.get_contrail_nodes(config_ip=config_ip, config_port=config_port)
            analytics_ip = contrail_nodes['analytics_nodes'][0]['ip_address']
        uve_obj = ContrailUVE(ip=analytics_ip, port=analytics_port)
        if uuid_type == "virtual-machine":
            vm_uuid = uuid
        else:
            #generic code to get associated Vrouter and control objects.
            where = 'uuid==%s' %(uuid)
            config_api = ContrailApi(ip=config_ip, port=config_port)
            if ContrailUtils.check_for_vm_vmi_in_context(contrail_info, context_path, config_ip, config_port, analytics_ip, uve_obj, config_api):
                return contrail_info
            #there was no VM/VMI object in the context path
            #so return info for all the VM's.
            object_name = uuid_type.replace('_', '-')                
            schema_to_use = _agent_schema_dict[object_name] 
            #import pdb;pdb.set_trace()
            vm_objs = config_api.get_object_deep(object_name, schema_to_use, where = where)
#                                                    detail = True,
#                                                    de_ref = True, strip_obj_name = False)
            for vm in vm_objs:
                fq_name = ':'.join(vm.values()[0]['fq_name'])
                tmp_contrail_info = ContrailUtils.get_contrail_vm_info(fq_name, config_ip=config_ip, config_port=config_port,
                                                           analytics_ip=analytics_ip)
                vrouter_objs = tmp_contrail_info['vrouter']
                control_objs = tmp_contrail_info['control']
                for vrouter_obj in vrouter_objs:
                    ContrailUtils.add_unique_object_in_object_list(contrail_info['vrouter'], vrouter_obj, 'ip_address')                   
                for control_obj in control_objs:
                    ContrailUtils.add_unique_object_in_object_list(contrail_info['control'], control_obj, 'ip_address')                   
            return contrail_info
	#Should we move this to each of the cases.
        if not fq_name:
            fq_name = vm_uuid
        contrail_info = ContrailUtils.get_contrail_vm_info(fq_name, config_ip=config_ip, config_port=config_port,
                                                           analytics_ip=analytics_ip)
        return contrail_info


    @staticmethod
    def get_contrail_info_from_vm(uve_obj, uuid):
        contrail_info = {'vrouter': [], 'control': []}
        try:
            vrouter_obj = uve_obj.get_object(uuid, "virtual-machine", select_fields = ['UveVirtualMachineAgent.vrouter'])
            vrouter = {}
            vrouter_name = vrouter_obj['UveVirtualMachineAgent.vrouter']
            vrouter['hostname'] = vrouter_name
            peer_list = uve_obj.get_object(vrouter_name , "vrouter", select_fields = ['VrouterAgent.xmpp_peer_list', 
                                                                                      'VrouterAgent.self_ip_list',
                                                                                      'VrouterAgent.sandesh_http_port'])
            vrouter['ip_address'] = peer_list['VrouterAgent.self_ip_list'][0]
            vrouter['sandesh_http_port'] = peer_list['VrouterAgent.sandesh_http_port']
            contrail_info['vrouter'].append(vrouter)
            xmpp_peer_list = peer_list['VrouterAgent.xmpp_peer_list']
            for peer in xmpp_peer_list:
                control = {}
                control['ip_address'] = peer['ip']
                control['xmpp_status'] = peer['status']
                control['primary'] = peer['primary']
                control['sandesh_http_port'] = '8083'
                contrail_info['control'].append(control)
            return contrail_info
        except:
            return contrail_info

    @staticmethod
    def get_contrail_vmi_info(uuid, config_ip='127.0.0.1', config_port='8082', **kwargs):
        contrail_info = {'vrouter': [], 'control': []}
        analytics_ip = kwargs.get('analytics_ip', None)
        analytics_port = kwargs.get('analytics_port', '8081')
        try:
            if not analytics_ip:
                contrail_nodes = ContrailUtils.get_contrail_nodes(config_ip=config_ip, config_port=config_port)
                analytics_ip = contrail_nodes['analytics_nodes'][0]['ip_address']
            uve_obj = ContrailUVE(ip=analytics_ip, port=analytics_port)
            vmi_obj = uve_obj.get_object(uuid, "virtual-machine-interface", select_fields = ['UveVMInterfaceAgent.vm_uuid'])
            vm_uuid = vmi_obj['UveVMInterfaceAgent.vm_uuid']
            contrail_info = ContrailUtils.get_contrail_vm_info(vm_uuid, config_ip=config_ip, config_port=config_port,
                                                               analytics_ip=analytics_ip)
            return contrail_info
        except:
            return contrail_info


    @staticmethod
    def get_contrail_vm_info(uuid, config_ip='127.0.0.1', config_port='8082', **kwargs):
        # vrouter['hostname'], vrouter['ip_address'], control['hostname'], control['ip_address']
        contrail_info = {'vrouter': [], 'control': []}
        analytics_ip = kwargs.get('analytics_ip', None)
        analytics_port = kwargs.get('analytics_port', '8081')
        try:
            if not analytics_ip:
                contrail_nodes = ContrailUtils.get_contrail_nodes(config_ip=config_ip, config_port=config_port)
                analytics_ip = contrail_nodes['analytics_nodes'][0]['ip_address']
            uve_obj = ContrailUVE(ip=analytics_ip, port=analytics_port)        
            vrouter_obj = uve_obj.get_object(uuid, "virtual-machine", select_fields = ['UveVirtualMachineAgent.vrouter'])
            vrouter = {}
            vrouter_name = vrouter_obj['UveVirtualMachineAgent.vrouter']
            vrouter['hostname'] = vrouter_name
            peer_list = uve_obj.get_object(vrouter_name ,"vrouter", select_fields = ['VrouterAgent.xmpp_peer_list', 
                                                                                     'VrouterAgent.self_ip_list',
                                                                                     'VrouterAgent.sandesh_http_port'])
            vrouter['ip_address'] = peer_list['VrouterAgent.self_ip_list'][0]
            vrouter['sandesh_http_port'] = peer_list['VrouterAgent.sandesh_http_port']
            vrouter['peers'] = []
            contrail_info['vrouter'].append(vrouter)
            xmpp_peer_list = peer_list['VrouterAgent.xmpp_peer_list']
            for peer in xmpp_peer_list:
                control = {}
                control['ip_address'] = peer['ip']
                control['xmpp_status'] = peer['status']
                control['primary'] = peer['primary']
                control['sandesh_http_port'] = '8083'
                contrail_info['control'].append(control)
                vrouter['peers'].append(control)
            return contrail_info
        except:
            return contrail_info

    @staticmethod
    def get_contrail_nodes(config_ip='127.0.0.1', config_port='8082'):
        contrail_nodes = {}
        config_api = ContrailApi(ip=config_ip, port=config_port)
        global_configs_url = 'http://%s:%s/global-system-configs' % (config_ip, config_port)
        global_configs = config_api.get_object(object_name='', 
                                               url=global_configs_url)
        global_config = config_api.get_object(object_name='', 
                                              url=global_configs['global-system-configs'][0]['href'])['global-system-config']

        config_nodes = global_config['config_nodes']
        contrail_nodes['config_nodes'] = []
        for node in config_nodes:
            config_node = config_api.get_object(object_name='',
                                                url=node['href'])
            cnode = {}
            cnode['ip_address'] = str(config_node['config-node']['config_node_ip_address'])
            cnode['hostname'] = str(config_node['config-node']['name'])
            cnode['port'] = 8082
            contrail_nodes['config_nodes'].append(cnode)

        database_nodes = global_config['database_nodes']
        contrail_nodes['database_nodes'] = []
        for node in database_nodes:
            database_node = config_api.get_object(object_name='',
                                                  url=node['href'])
            dnode = {}
            dnode['ip_address'] = str(database_node['database-node']['database_node_ip_address'])
            dnode['hostname'] = str(database_node['database-node']['name'])
            contrail_nodes['database_nodes'].append(dnode)

        analytics_nodes = global_config['analytics_nodes']
        contrail_nodes['analytics_nodes'] = []
        for node in analytics_nodes:
            analytics_node = config_api.get_object(object_name='',
                                                   url=node['href'])
            anode = {}
            anode['ip_address'] = str(analytics_node['analytics-node']['analytics_node_ip_address'])
            anode['hostname'] = str(analytics_node['analytics-node']['name'])
            anode['port'] = 8081
            contrail_nodes['analytics_nodes'].append(anode)

        virtual_routers = global_config['virtual_routers']
        contrail_nodes['vrouters'] = []
        for node in virtual_routers:
            virtual_router = config_api.get_object(object_name='',
                                                   url=node['href'])
            vnode = {}
            vnode['ip_address'] = str(virtual_router['virtual-router']['virtual_router_ip_address'])
            vnode['hostname'] = str(virtual_router['virtual-router']['name'])
            vnode['sandesh_http_port'] = 8085
            contrail_nodes['vrouters'].append(vnode)

        bgp_routers_url = 'http://%s:%s/bgp-routers?detail=True' % (config_ip, config_port)
        bgp_routers = config_api.get_object(object_name='', url=bgp_routers_url)['bgp-routers']
        contrail_nodes['control_nodes'] = []
        for bgp_router in bgp_routers:
            controller = config_api.get_object(object_name='', url=bgp_router['href'])
            if controller['bgp-router']['bgp_router_parameters']['vendor'] == 'contrail':
                cnode = {}
                cnode['ip_address'] = str(controller['bgp-router']['bgp_router_parameters']['address'])
                cnode['hostname'] = str(controller['bgp-router']['name'])
                cnode['sandesh_http_port'] = 8083
                contrail_nodes['control_nodes'].append(cnode)
        return contrail_nodes



if __name__ == "__main__":
    #roles = ContrailUtils.get_contrail_nodes(config_ip='10.84.17.5', config_port='8082')
    #vm_info = ContrailUtils.get_contrail_vm_info('9f838303-7d84-44c4-9aa3-b34a3e8e56b1', 
    #                                             config_ip='10.84.17.5', config_port='8082',
    #                                             analytics_ip='10.84.17.5', analytics_port='8081')
    #contrail_info = ContrailUtils.get_contrail_vm_info('9f838303-7d84-44c4-9aa3-b34a3e8e56b1', config_ip='10.84.17.5')
    contrail_info = ContrailUtils.get_contrail_vmi_info('default-domain:admin:060c2b5f-d43a-4ea5-844d-393819ff36fd', 
                                                        config_ip='10.84.17.5', config_port='8082')


    contrail_test_info = ContrailUtils.get_contrail_info_v2('4c7b468b-69ef-4ea4-a820-69aa06653d2f',
                                                             uuid_type = 'virtual-machine',
                                                             config_ip = '10.84.17.5',
                                                             config_port = '8082')
    contrail_t_info = ContrailUtils.get_control_nodes(config_ip = '10.84.17.5', config_port = '8082')
    pdb.set_trace()

              
        
 

