''' 
- Creating a http server from scratch
- author:Sony Thomas
'''
import os
import socket
from typing import Optional,Callable,Dict,DefaultDict,List
from collections import defaultdict
class Server:
    def __init__(self,port:int=80,host:Optional[str]="localhost"):
        self.port = port
        self.msg = []
        self.host:str = host
        self.server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.funcMap:DefaultDict = defaultdict(dict)

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
            if self.funcMap[method].get(path):
                raise Exception("Route already exists")
            self.funcMap[method][path]={
                "middlewares": middleware,
                "func":func
            }
        return None
    
    def _handle_client (self,client_socket:socket):
        ''' 
        Handles HTTP request from the client and sends the appropriate response
        '''
        request = client_socket.recv(1024).decode("utf-8")
        if not request:
            client_socket.close()
            return
        print(f"Request recieved:\n\t{request}")

        request_lines  = request.splitlines()
        request_line   = request_lines[0] if request_lines else ""
        method,path,*_ = request_line.split() if len(request_line.split())>=2 else ("","")
        #what does the *_ do here?
        if path == "/":
            path = "/src/index.html"
            #shouldn't we allow for any file to be rendered? 
        file_path = f".{path}"

        #check if the file exists
        try:
            if os.path.isfile(file_path):
                with open(file_path,'rb') as file:
                    body = file.read()
                response = (
                    "HTTP/1.1 200 OK\n"
                    f"Content-Length:{len(body)}\r\n"
                    "Content-Type:text/html\r\n"
                    "\r\n"
                ).encode("utf-8") + body
            else:
                body = b"<html><body><h1> 404 Not Found </h1></body></html>"
                response = (
                    "HTTP/1.1 404 Not Found\r\n"
                    f"Content-Length:{len(body)}\r\n"
                    "Content-Type:text/html\r\n"
                    "\r\n"
                ).encode("utf-8") + body
        except Exception as e:
            body =  f"<html><body><h1> 500 Internal Server Error</h1><p>{e}</p></body></html>".encode("utf-8")
            response = (
                "HTTP/1.1 500 Internal Server Error\r\n"
                f"Content-Length:{len(body)}\r\n"
                "Content-Type:text/html\r\n"
                "\r\n"
            ).encode("utf-8") + body
        
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
    server = Server(port=8000)
    server.start_server()
