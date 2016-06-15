import sys
import argparse
from logger import logger
from contrail_api import ContrailApi
from introspect import Introspect
from introspect import AgentIntrospectCfg
from contrail_utils import ContrailUtils
from collections import OrderedDict
from vertex_print import vertexPrint
from basevertex import baseVertex

class debugVertexVMI(baseVertex):
    dependant_vertexes = ['debugVertexVM', 'debugVertexVN', 'debugVertexSG']
    vertex_type = 'virtual-machine-interface'

    def process_self(self, vertex_type, uuid, vertex):
        agent = {}
        agent['oper'] = self.agent_oper_db(self._get_agent_oper_db, vertex_type, vertex)
        self._add_agent_to_context(uuid, agent)
        control = {}
        control['oper'] = {}
        self._add_control_to_context(uuid, control)

    def get_schema(self):
        #VM UUID, VMI UUID, VMI Name, VN UUID
        schema_dict = {
                'virtual-machine': {
                    'uuid': 'virtual_machine_interface_back_refs'
                },
                'virtual-network': {
                    'uuid': 'virtual_machine_interface_back_refs',
                    'display_name': 'virtual_machine_interface_back_refs'
                },
                'security-group': {
                    'uuid': 'virtual_machine_interface_back_refs'
                },
                'floating-ip': {
                    'uuid': 'virtual_machine_interface_refs'
                }
        }
        return schema_dict

    def _get_agent_oper_db(self, host_ip, agent_port, vertex_type, vertex):
        error = False
        base_url = 'http://%s:%s/%s' % (host_ip, agent_port, 'Snh_ItfReq?')
        vmi_uuid = vertex[vertex_type]['uuid']
        search_str = ('name=&type=&uuid=%s') % (vmi_uuid)
        oper = {}
        url_dict_resp = Introspect(url=base_url + search_str).get()
        if len(url_dict_resp['ItfResp']['itf_list']) == 1:
            intf_rec = url_dict_resp['ItfResp']['itf_list'][0]
        else:
            pstr = "Agent Error interface uuid %s, doesn't exist" % (vmi_uuid)
            error = True
            self.logger.error(pstr)
            print pstr
            return oper

        # Is interface active
        if intf_rec['active'] != 'Active':
            pstr = "Agent Error %s, %s is not Active" % (intf_rec['uuid'], intf_rec['name'])
            error = True
            self.logger.error(pstr)
            print pstr
        else:
            pstr = "Agent: Interface %s is active" % (intf_rec['name'])
            self.logger.debug(pstr)
            print pstr

        # Is dhcp enabled
        if intf_rec['dhcp_service'] != 'Enable':
            pstr = "Agent Error %s, %s, dhcp is %s, but not enabled" % \
                   (intf_rec['uuid'], intf_rec['name'], intf_rec['dhcp_service'])
            error = True
            self.logger.error(pstr)
            print pstr
        else:
            self.logger.debug("Agent: Interface %s dhcp is enabled" % (intf_rec['name']))

        # Is dns enabled
        if intf_rec['dns_service'] != 'Enable':
            pstr = "Agent Error %s, %s, dns is %s, but not enabled" % \
                (intf_rec['uuid'], intf_rec['name'], intf_rec['dns_service'])
            error = True
            self.logger.error(pstr)
            print pstr
        else:
            self.logger.debug("Agent: Interface %s dns is enabled" % (intf_rec['name']))

        pstr = "Agent Verified interface %s %s" % (intf_rec['name'], 'with errors' if error else '')
        self.logger.debug(pstr)
        print pstr
        oper['interface'] = url_dict_resp
        return oper

def parse_args(args):
    defaults = {
        'config_ip': '127.0.0.1',
        'config_port': '8082',
        'detail': False,        
    }
    parser = argparse.ArgumentParser(description='Debug utility for VMI',
                                     add_help=True)
    parser.set_defaults(**defaults)
    parser.add_argument('-cip', '--config_ip',
                        help='Config node ip address')
    parser.add_argument('-cport', '--config_port',
                        help='Config node REST API port')
    parser.add_argument('-obj', '--obj_type',
                        help='Object type to search')
    parser.add_argument('-uuid', '--uuid',
                        help='uuid')
    parser.add_argument('-dname', '--display_name',
                        help='Display name of the object')
    parser.add_argument('--detail',
                        help='Context detail output to console')
    cliargs = parser.parse_args(args)
    if len(args) == 0:
        parser.print_help()
        sys.exit(2)
    return cliargs

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vVMI= debugVertexVMI(config_ip=args.config_ip,
                         config_port=args.config_port,
                         uuid=args.uuid,
                         obj_type=args.obj_type,
                         display_name=args.display_name)
    context = vVMI.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(context)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_based_on_uuid( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1',context, False)
    #vP.print_object_catalogue(context, True)
    vP.convert_json(context)

