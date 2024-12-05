''' 
- Creating a http server from scratch
- author:Sony Thomas
'''
from collections import defaultdict
import os
import re
import socket
from typing import Optional,Callable,Dict,DefaultDict,List
from utils.regexUtils import httpRegex

def middleware(req:dict,res:dict,next:Callable[[],None])->None:
    ''' 
    - Process the request and response or call next to continue to next middleware
    - RETURN:None
    - REQUIRE:req:dict,res:dict,next:Callable[[],None]
    '''

class Server:
    def __init__(self,port:int=80,host:Optional[str]="localhost"):
        self.port = port
        self.msg = []
        self.host:str = host
        self.server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.funcMap:DefaultDict = defaultdict(dict)

    def _compare(self,method:str,path:str,templates:str)->str:
        ''' 
        - Compare the path recieved from the connection with templates
        - REQUIRES: path:str and template:[str]
        '''
        matchTemplate = ""
        for template in templates:
            match = re.match(template,path)
            if match:
                matchTemplate=template
                self.funcMap[method][template]["params"] = match.groupdict()
                print(f"Matched template: {template}:{self.funcMap[method][template]}")
        return matchTemplate

    def _execute_middleware(self,req:dict,res:dict,middlewares:List[Callable[...,None]],handler:Callable[...,None])->None:
        '''
        - Function to execute middleware functions
        '''
        def next_middleware(index:int=0):
            if index<len(middlewares):
                middlewares[index](req,res,lambda:next_middleware(index+1))
            else:
                res["body"]  =handler(req["params"])
                res["status"]=200
        next_middleware(0)
    def add_route(self,methods:List[str],path:str,middleware:Optional[List[Callable[...,object]]],func:Callable[...,object])->None:
        ''' 
        - Function to define requests for GET,POST,PUT,DELETE
        - Set up middlewares defined and execute them before the response function gets executed
        - RETURN:None
        - REQUIRE:Caching to not recompile the routes that have already been defined
        '''
        for method in methods:
            if method not in ["GET","POST","PUT","DELETE"]:
                raise Exception("Invalid method")
            template=r""
            pathList = path.strip("/").split("/")
            for subpath in pathList:
                if subpath[0]=='{' and subpath[-1]=="}":
                    template+=rf"/(?P<{subpath[1:-1]}>[a-zA-Z0-9_.\-~%]+)"
                else:
                    template+=rf"/{subpath}"
            if self.funcMap[method].get(template):# I can check if the path already exists before templating to avoid unnecessary templating
                raise Exception("Route already exists")
            self.funcMap[method][template]={
                "middlewares": middleware or [],
                "func":func,
                "path":path
            }
        return None
    
    def _handle_client (self,client_socket:socket):
        ''' 
        - Handles HTTP request from the client and sends the appropriate response
        '''
        request = client_socket.recv(1024).decode("utf-8")
        if not request:
            client_socket.close()
            return
        print(f"Request recieved:\n\t{request}")

        request_lines     = request.splitlines()
        request_line      = request_lines[0] if request_lines else ""
        method,path,*rest = request_line.split() if len(request_line.split())>=2 else ("","")
        # what does the *_ do here?It unpacks and ignores
        headers={}
        # Step-0 Add headers to the Request Object
        for line in request_lines[1:]:
            if line.strip()=="":
                break
            key,value            =  line.split(":",1)
            headers[key.strip()] =  value.strip()
        # Step-1 Check if valid path
        q = httpRegex(path)# check if the path is valid and if so extract query parameters

        matched_template = self._compare(method,path,self.funcMap[method].keys())
        if matched_template:
            self.funcMap[method][matched_template]["queries"]=q
            route = self.funcMap[method][matched_template]
            handler_func = route["func"]
            middlewares = route["middlewares"]

            req:Dict ={
                "method":method,
                "path":path,
                "params":route.get("params",{}),
                "queries":route.get("queries",{}),
                "headers":headers
            }
            res:Dict ={
                "status":404,
                "body":"Not Found"
            } 
            self._execute_middleware(req,res,middlewares,handler_func)
            response = (
                f"HTTP/1.1 {res['status']} OK\r\n"
                f"Content-Length:{len(res['body'])}\r\n"
                "Content-Type:text/plain\r\n"
                "\r\n"
                f"{res['body']}\r\n"
            ).encode("utf-8")
            print(f"Matched template: {matched_template}:{self.funcMap[method][matched_template]}\n{res}")
        else:
            body = b"<html><body><h1> 404 Not Found </h1></body></html>"
            response = (
                "HTTP/1.1 404 Not Found\r\n"
                f"Content-Length:{len(body)}\r\n"
                "Content-Type:text/html\r\n"
                "\r\n"
            ).encode("utf-8") + body
            print("No matching template found for the path",path)

        # if path == "/":
        #     path = "/src/index.html"
        #     #shouldn't we allow for any file to be rendered? 
        # file_path = f".{path}"

        # #check if the file exists
        # try:
        #     if os.path.isfile(file_path):
        #         with open(file_path,'rb') as file:
        #             body = file.read()
        #         response = (
        #             "HTTP/1.1 200 OK\n"
        #             f"Content-Length:{len(body)}\r\n"
        #             "Content-Type:text/html\r\n"
        #             "\r\n"
        #         ).encode("utf-8") + body
        #     else:
        #         body = b"<html><body><h1> 404 Not Found </h1></body></html>"
        #         response = (
        #             "HTTP/1.1 404 Not Found\r\n"
        #             f"Content-Length:{len(body)}\r\n"
        #             "Content-Type:text/html\r\n"
        #             "\r\n"
        #         ).encode("utf-8") + body
        # except Exception as e:
        #     body =  f"<html><body><h1> 500 Internal Server Error</h1><p>{e}</p></body></html>".encode("utf-8")
        #     response = (
        #         "HTTP/1.1 500 Internal Server Error\r\n"
        #         f"Content-Length:{len(body)}\r\n"
        #         "Content-Type:text/html\r\n"
        #         "\r\n"
        #     ).encode("utf-8") + body
        
        client_socket.sendall(response)
        client_socket.close()
    
    def start_server(self):
        '''
        - Create HTTP server session and listens for incoming connections 
        '''
        self.server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.server_socket.bind((self.host,self.port))
        
        #listen for incoming connections
        self.server_socket.listen(5)
        print(f"Server started on {self.host}:{self.port}")
        try:
            while True:
                client_socket,client_addr = self.server_socket.accept()
                print(f"New connection from client:{client_addr}")

                #handle the client's request
                self._handle_client(client_socket)
        except KeyboardInterrupt:
            print("\nShutting down the server...")
        finally:
            #Close the server socket
            self.server_socket.close()

#Example implementation
#use curl http://localhost:<port> to test the server out
if __name__ == "__main__":
    def log_middleware(req, res, next):
        print(f"Request Log: {req['method']} {req['path']}")
        next()

    def auth_middleware(req, res, next):
        # Example: Require an "Authorization" header
        if "Authorization" in req.get("headers", {}):
            print("Authorization passed")
            next()
        else:
            res["status"] = 401
            res["body"] = "Unauthorized"
            print(req)

    server = Server(port=8000)
    server.add_route(
    methods=["GET"],
    path="/secure/{id}",
    middleware=[log_middleware, auth_middleware],
    func=lambda params: f"Secure Data for ID: {params['id']}",
    )
    server.add_route(
    methods=["GET"],
    path="/public",
    middleware=[log_middleware],
    func=lambda _: "Public Data",
    )
    server.add_route(
        methods=["GET"],
        path="/test/{id}",
        middleware=None,
        func=lambda params: f"User ID: {params['id']}"
    )
    server.start_server()
