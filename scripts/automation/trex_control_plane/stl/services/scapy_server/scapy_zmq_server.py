
import time
import sys
import os

python2_zmq_path = os.path.abspath(os.path.join(os.pardir,os.pardir,os.pardir,os.pardir,
                                                os.pardir,'external_libs','pyzmq-14.5.0','python2','fedora18','64bit'))
stl_pathname = os.path.abspath(os.path.join(os.pardir, os.pardir))
sys.path.append(stl_pathname)
sys.path.append(python2_zmq_path)
import zmq
import inspect
from scapy_service import *
from argparse import *
import socket


class ParseException(Exception): pass
class InvalidRequest(Exception): pass
class MethodNotFound(Exception): pass
class InvalidParams(Exception): pass

class Scapy_wrapper:
    def __init__(self):
        self.scapy_master = Scapy_service()

    def parse_req_msg(self,JSON_req):
        try:
            req = json.loads(JSON_req)
            req_id=b'null'
            if (type(req)!= type({})):
                raise ParseException(req_id)
            json_rpc_keys = ['jsonrpc','id','method']
            if ((set(req.keys())!=set(json_rpc_keys)) and (set(req.keys())!=set(json_rpc_keys+['params']))) :
                if 'id' in req.keys():
                    req_id = req['id']
                raise InvalidRequest(req_id)
            req_id = req['id']
            if (req['method']=='shut_down'):
                return 'shut_down',[],req_id
            if not (self.scapy_master.supported_methods(req['method'])):
                raise MethodNotFound(req_id)
            scapy_method = eval("self.scapy_master."+req['method'])
            arg_num_for_method = len(inspect.getargspec(scapy_method)[0])
            if (arg_num_for_method>1) :
                if not ('params' in req.keys()):
                    raise InvalidRequest(req_id)
                params_len = len(req['params'])+1 # +1 because "self" is considered parameter in args for method
                if not (params_len==arg_num_for_method):
                    raise InvalidParams(req_id)
                return req['method'],req['params'],req_id
            else:
                return req['method'],[],req_id
        except ValueError:
            raise ParseException(req_id)

    def create_error_response(self,error_code,error_msg,req_id='null'):
        return {"jsonrpc": "2.0", "error": {"code": error_code, "message:": error_msg}, "id": req_id}
        
    def create_success_response(self,result,req_id=b'null'):
        return {"jsonrpc": "2.0", "result": result, "id": req_id }
    
    def get_exception(self):
        return sys.exc_info()


    def execute(self,method,params):
        if len(params)>0:
            result = eval('self.scapy_master.'+method+'(*'+str(params)+')')
        else:
            result = eval('self.scapy_master.'+method+'()')
        return result


    def error_handler(self,e,req_id):
        response = []
        try:
            raise e
        except ParseException as e:
            response = self.create_error_response(-32700,'Parse error ',req_id)
        except InvalidRequest as e:
            response = self.create_error_response(-32600,'Invalid Request',req_id)
        except MethodNotFound as e:
            response = self.create_error_response(-32601,'Method not found',req_id)
        except InvalidParams as e:
            response = self.create_error_response(-32603,'Invalid params',req_id)
        except SyntaxError as e:
            response = self.create_error_response(-32097,'SyntaxError',req_id)
        except Exception as e:
            if hasattr(e,'message'):
                response = self.create_error_response(-32098,'Scapy Server: '+str(e.message),req_id)
            else:
                response = self.create_error_response(-32096,'Scapy Server: Unknown Error',req_id)            
        finally:
            return response

class Scapy_server():
    def __init__(self, port=4507):
        self.scapy_wrapper = Scapy_wrapper()
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:"+str(port))
        self.IP_address = socket.gethostbyname(socket.gethostname())

    def activate(self):
        print ('***Scapy Server Started***\nListening on port: %d' % self.port)
        print ('Server IP address: %s' % self.IP_address)
        try:
            while True:
                message = self.socket.recv_string()
                if args.verbose:
                    print('Received Message: %s \n' % message)
                try:
                    params = []
                    method=''
                    req_id = 'null'
                    method,params,req_id = self.scapy_wrapper.parse_req_msg(message)
                    if (method == 'shut_down'):
                        print ('Shut down by remote user')
                        result = 'Server shut down command received - server had shut down'
                    else:
                        result = self.scapy_wrapper.execute(method,params)
                    response = self.scapy_wrapper.create_success_response(result,req_id)
                except Exception as e:
                    response = self.scapy_wrapper.error_handler(e,req_id)
                finally:
                    json_response = json.dumps(response)
                    if args.verbose:
                        print('Sending Message: %s \n' % json_response)
                #  Send reply back to client
                    self.socket.send_string(json_response)
                    if (method == 'shut_down'):
                        break

        except KeyboardInterrupt:
                print(b'Terminated By Ctrl+C')

        finally:
            self.socket.close()
            self.context.destroy()



#arg1 is port number for the server to listen to
def main(arg1=4507):
    s = Scapy_server(arg1)
    s.activate()

if __name__=='__main__':
    if len(sys.argv)>1:
        parser = ArgumentParser(description=' Runs Scapy Server ')
        parser.add_argument('-s','--scapy-port',type=int, default = 4507, dest='scapy_port',
                            help='Select port to which Scapy Server will listen to.\n default is 4507\n',action='store')
        parser.add_argument('-v','--verbose',help='Print Client-Server Request-Reply logging',action='store_true',default = False)
        args = parser.parse_args()
        port = args.scapy_port
        sys.exit(main(port))
    else:
        sys.exit(main())
