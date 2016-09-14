import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser

class debugVertexSG(baseVertex):
    dependant_vertexes = ['debugVertexVMI']
    vertex_type = 'security-group'

    def process_self(self, vertex):
        agent = {}
        agent['oper'] = self.agent_oper_db(self._get_agent_oper_db, vertex)
        self._add_agent_to_context(vertex, agent)
        control = {}
        control['oper'] = {}
        self._add_control_to_context(vertex, control)

    def _get_agent_oper_db(self, introspect, vertex):
        error = False
        sg_uuid = vertex['uuid']
        oper = {}
        sg_info = introspect.get_sg_details(sg_uuid)
        if len(sg_info['SgListResp']['sg_list']) == 1:
            sg_rec = sg_info['SgListResp']['sg_list'][0]
            oper[vertex['vertex_type']] = sg_rec
        else:
            error = True

        egress_acl_uuid = sg_rec['egress_acl_uuid']
        ingress_acl_uuid = sg_rec['ingress_acl_uuid']
        url_dict_resp = introspect.get_acl_details(egress_acl_uuid)
        if len(url_dict_resp['AclResp']['acl_list']) == 1:
            egress_acl_rec = url_dict_resp['AclResp']['acl_list'][0]
            oper['egress_acl'] = egress_acl_rec
        else:
            error = True

        url_dict_resp = introspect.get_acl_details(ingress_acl_uuid)
        if len(url_dict_resp['AclResp']['acl_list']) == 1:
            ingress_acl_rec = url_dict_resp['AclResp']['acl_list'][0]
            oper['ingress_acl'] = ingress_acl_rec
        else:
            error = True
        pstr = "Agent Verified security group %s %s" % (sg_uuid, 'with errors' if error else '')
        self.logger.debug(pstr)
        print pstr
        return oper

    def get_schema(self):
        schema_dict = {
                "virtual-machine": {
                        "uuid": 'virtual_machine_interface_back_refs.security_group_refs'
                },
                "virtual-machine-interface": {
                        "uuid": 'security_group_refs'
                }
        }
        return schema_dict

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for SG', add_help=True)
    parser.add_argument('--display_name', help='Display name')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vSG= debugVertexSG(**args)
    #context = vSG.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(vSG)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_catalogue(context, False)
    #vP.convert_to_file_structure(context)
    vP.convert_json()
