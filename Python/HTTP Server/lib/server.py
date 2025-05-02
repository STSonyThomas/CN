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
import subprocess # Added for the vulnerable function

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
    def _parse_multipart(self, body: str, boundary: str):
        """
        Parse `multipart/form-data` body content.
        """
        parts = body.split(f"--{boundary}")
        parsed_data = {}
        for part in parts:
            if "Content-Disposition" in part:
                headers, value = part.split("\r\n\r\n", 1)
                disposition = headers.split("Content-Disposition:")[1].strip()
                name_match = re.search(r'name="(.+?)"', disposition)
                if name_match:
                    name = name_match.group(1)
                    parsed_data[name] = value.strip()
        return parsed_data
    def _execute_middleware(self,req:dict,res:dict,middlewares:List[Callable[...,None]],handler:Callable[...,None])->None:
        '''
        - Function to execute middleware functions
        '''
        def next_middleware(index:int=0):
            if index<len(middlewares):
                middlewares[index](req,res,lambda:next_middleware(index+1))
            else:
                res["body"]  =handler(req,res)
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
            print(f"Added route: {method} {path}:\n{self.funcMap[method][template]}")
        return None
    
    # --- VULNERABLE FUNCTION EXAMPLE ---
    # No longer explicitly marked as vulnerable
    def _vulnerable_handler(self, req: dict, res: dict) -> str:
        '''
        - Example handler demonstrating a command injection vulnerability.
        - Takes a 'cmd' query parameter and executes it.
        - RETURN: Output of the command or an error message.
        '''
        command_param = req.get("queries", {}).get("cmd", [""])[0] # Get 'cmd' query param

        if not command_param:
            res["status"] = 400
            return "Missing 'cmd' query parameter."

        try:
            # Directly executing user input.
            print(f"Executing vulnerable command: {command_param}")
            # Using subprocess.run for slightly better control than os.system, but still vulnerable here.
            result = subprocess.run(command_param, shell=True, capture_output=True, text=True, check=True)
            output = result.stdout
            res["status"] = 200
            return f"Command output:\n{output}"
        except subprocess.CalledProcessError as e:
            res["status"] = 500
            return f"Command failed:\n{e.stderr}"
        except Exception as e:
            res["status"] = 500
            return f"An error occurred: {str(e)}"
    # --- END VULNERABLE FUNCTION EXAMPLE ---

    # --- NEW VULNERABLE FUNCTION ---
    def _vulnerable_file_reader(self, req: dict, res: dict) -> str:
        '''
        - Reads a file specified by the 'file' query parameter.
        - Vulnerable to path traversal.
        - RETURN: File content or an error message.
        '''
        file_param = req.get("queries", {}).get("file", [""])[0]

        if not file_param:
            res["status"] = 400
            return "Missing 'file' query parameter."

        try:
            # UNSAFE: Directly using user input as file path without validation.
            # An attacker could provide input like '../../../../etc/passwd' (Linux)
            # or '../../../../boot.ini' (Windows) to read sensitive files.
            print(f"Attempting to read file: {file_param}")
            # Construct a path relative to the server's current directory
            # This is still dangerous if not properly sandboxed
            base_path = os.path.dirname(__file__) # Or some other intended base directory
            # Even with os.path.join, traversal is possible if input starts with / or contains ..
            file_path = os.path.abspath(os.path.join(base_path, file_param))

            # Basic check (often insufficient) to prevent going *above* the intended base
            # This doesn't prevent reading *within* the base directory structure
            if not file_path.startswith(os.path.abspath(base_path)):
                 res["status"] = 403
                 return "Forbidden: Access denied."

            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                res["status"] = 404
                return f"File not found or is not a regular file: {file_param}"

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            res["status"] = 200
            res["headers"] = {"Content-Type": "text/plain"} # Set appropriate content type
            return content
        except FileNotFoundError:
            res["status"] = 404
            return f"File not found: {file_param}"
        except PermissionError:
            res["status"] = 403
            return f"Permission denied to read file: {file_param}"
        except Exception as e:
            res["status"] = 500
            return f"An error occurred while reading the file: {str(e)}"
    # --- END NEW VULNERABLE FUNCTION ---

    def _handle_client (self,client_socket:socket):
        ''' 
        - Handles HTTP request from the client and sends the appropriate response
        '''
        request_data = b""
        # Read the request line and headers first
        while b"\r\n\r\n" not in request_data:
            chunk = client_socket.recv(1024)
            if not chunk:
                break
            request_data += chunk
        
        if not request_data:
            client_socket.close()
            return

        request_str = request_data.decode("utf-8", errors='ignore') # Use ignore for potential binary data issues initially
        print(f"Request received:\n\t{request_str[:500]}...") # Log truncated request

        # Separate headers and initial body part
        header_part, initial_body_part = request_str.split("\r\n\r\n", 1)
        request_lines = header_part.splitlines()
        request_line = request_lines[0] if request_lines else ""
        method, path, *_ = request_line.split() if len(request_line.split()) >= 2 else ("", "", "")

        headers = {}
        for line in request_lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        # Step-1 Handle body data more robustly
        content_type = headers.get("Content-Type", "")
        content_length = int(headers.get("Content-Length", 0))
        
        # Combine initial body part with remaining data if necessary
        body_bytes = initial_body_part.encode("utf-8") # Encode back the initial part
        
        if content_length > len(body_bytes):
            remaining_length = content_length - len(body_bytes)
            # Read exactly the remaining bytes needed
            while remaining_length > 0:
                chunk = client_socket.recv(min(remaining_length, 4096)) # Read in chunks
                if not chunk:
                    print("Warning: Client closed connection before sending full body.")
                    break
                body_bytes += chunk
                remaining_length -= len(chunk)

        # Decode body based on expected content type AFTER reading all of it
        body = ""
        parsed_body = None
        try:
            if "multipart/form-data" in content_type:
                # Multipart needs special handling with bytes
                boundary = content_type.split("boundary=")[1]
                # We need a more robust multipart parser that works with bytes
                # For simplicity, let's skip full parsing here or use a library if available
                # This basic example won't handle file uploads correctly with this structure
                parsed_body = self._parse_multipart(body_bytes.decode('latin-1'), boundary) # Use latin-1 for potential binary data
                body = "Multipart data received (parsing limited)" # Placeholder
            else:
                # For other types, decode using utf-8, potentially failing if binary
                body = body_bytes.decode("utf-8")
                if "application/json" in content_type:
                    import json
                    try:
                        parsed_body = json.loads(body)
                    except json.JSONDecodeError:
                        parsed_body = {"error": "Invalid JSON"}
                elif "application/x-www-form-urlencoded" in content_type:
                    from urllib.parse import parse_qs
                    parsed_body = parse_qs(body)
                elif "application/graphql" in content_type:
                    parsed_body = {"query": body.strip()}
                else:
                    parsed_body = body # Keep as raw string if not recognized

        except UnicodeDecodeError:
             print("Warning: Could not decode body as UTF-8. Treating as raw bytes.")
             parsed_body = body_bytes # Keep raw bytes if decoding fails
             body = f"Binary data ({len(body_bytes)} bytes)"


        print(f"Parsed Body: {parsed_body if isinstance(parsed_body, (dict, str)) else type(parsed_body)}") # Avoid printing large byte arrays

        # Step-2 Check if valid path and extract query parameters
        q = httpRegex(path) # Assuming httpRegex handles query extraction

        matched_template = self._compare(method, q['path_only'], self.funcMap[method].keys()) # Compare against path without query
        print(f"Templates:\n{self.funcMap[method].keys()}")

        if matched_template:
            route = self.funcMap[method][matched_template]
            handler_func = route["func"]
            middlewares = route["middlewares"]

            req:Dict ={
                "method":method,
                "path":path, # Full path with query
                "path_only": q.get('path_only', path), # Path without query
                "params":route.get("params",{}),
                "queries":q.get('queries',{}), # Use queries from httpRegex
                "headers":headers,
                "body":parsed_body
            }
            res:Dict ={
                "status":404,
                "body":"Not Found",
                "headers": {"Content-Type": "text/plain"} # Default content type
            }
            try:
                self._execute_middleware(req,res,middlewares,handler_func)
                # Ensure body is string for encoding
                response_body_str = str(res['body'])
                response_body_bytes = response_body_str.encode("utf-8")

                # Build response headers
                response_headers = f"HTTP/1.1 {res['status']} {self._get_status_message(res['status'])}\r\n"
                res_headers = res.get("headers", {})
                res_headers["Content-Length"] = len(response_body_bytes) # Calculate length correctly
                for key, value in res_headers.items():
                    response_headers += f"{key}: {value}\r\n"
                response_headers += "\r\n" # End of headers

                response = response_headers.encode("utf-8") + response_body_bytes
                print(f"Matched template: {matched_template}\nResponse Status: {res['status']}")

            except Exception as e:
                print(f"Error during request handling: {e}")
                res["status"] = 500
                res["body"] = f"Internal Server Error: {e}"
                response_body_bytes = str(res['body']).encode("utf-8")
                response = (
                    f"HTTP/1.1 500 Internal Server Error\r\n"
                    f"Content-Length:{len(response_body_bytes)}\r\n"
                    "Content-Type:text/plain\r\n"
                    "\r\n"
                ).encode("utf-8") + response_body_bytes

        else:
            # Handle 404 Not Found
            body_content = "<html><body><h1>404 Not Found</h1></body></html>"
            body_bytes = body_content.encode("utf-8")
            response = (
                "HTTP/1.1 404 Not Found\r\n"
                f"Content-Length:{len(body_bytes)}\r\n"
                "Content-Type:text/html\r\n"
                "\r\n"
            ).encode("utf-8") + body_bytes
            print(f"No matching template found for the path: {path}")

        client_socket.sendall(response)
        client_socket.close()

    def _get_status_message(self, status_code: int) -> str:
        # Basic status code messages
        status_messages = {
            200: "OK",
            201: "Created",
            204: "No Content",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            500: "Internal Server Error",
        }
        return status_messages.get(status_code, "Unknown Status")


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

                #handle the client's request in a separate function/thread later if needed
                try:
                    self._handle_client(client_socket)
                except Exception as e:
                    print(f"Error handling client {client_addr}: {e}")
                    # Ensure socket is closed even if _handle_client fails unexpectedly
                    if client_socket.fileno() != -1: # Check if socket is still open
                         client_socket.close()

        except KeyboardInterrupt:
            print("\nShutting down the server...")
        finally:
            #Close the server socket
            self.server_socket.close()
            print("Server socket closed.")

#Example implementation
#use curl http://localhost:<port> to test the server out
if __name__ == "__main__":
    def log_middleware(req, res, next):
        print(f"Request Log: {req['method']} {req.get('path_only', req['path'])} Queries: {req.get('queries')}")
        next()

    def auth_middleware(req, res, next):
        # Example: Require an "Authorization" header
        if "Authorization" in req.get("headers", {}):
            print("Authorization passed")
            next()
        else:
            print("Authorization failed")
            res["status"] = 401
            res["body"] = "Unauthorized"
            # Don't call next() if auth fails

    def example_handler(req: dict, res: dict) -> str:
        # Example handler that uses request data
        user_id = req.get("params", {}).get("id", "Unknown")
        query_param = req.get("queries", {}).get("info", [""])[0]
        body_data = req.get("body", {})
        return f"Secure Data for ID: {user_id}, Info: {query_param}, Body: {body_data}"

    def public_handler(req: dict, res: dict) -> str:
        res["headers"] = {"Content-Type": "application/json"} # Example of setting header
        import json
        return json.dumps({"message": "Public Data"})

    def user_handler(req: dict, res: dict) -> str:
        user_id = req.get("params", {}).get("id", "N/A")
        return f"User ID: {user_id}"

    server = Server(port=8000)

    # Secure route with middleware
    server.add_route(
        methods=["GET", "POST"], # Allow POST too
        path="/secure/{id}",
        middleware=[log_middleware, auth_middleware],
        func=example_handler, # Use the defined handler
    )

    # Public route
    server.add_route(
        methods=["GET"],
        path="/public",
        middleware=[log_middleware],
        func=public_handler, # Use the defined handler
    )

    # Simple route with path parameter
    server.add_route(
        methods=["GET"],
        path="/test/{id}",
        middleware=None,
        func=user_handler # Use the defined handler
    )

    # --- ADDING THE VULNERABLE ROUTES ---
    # Route for command execution vulnerability
    server.add_route(
        methods=["GET"],
        path="/vulnerable/exec",
        middleware=[log_middleware], # Log access
        func=server._vulnerable_handler # Route to the vulnerable function
    )

    # Route for path traversal vulnerability
    # Access like: http://localhost:8000/vulnerable/read?file=../main.py
    # Malicious example (Linux): http://localhost:8000/vulnerable/read?file=../../../../etc/passwd
    # Malicious example (Windows): http://localhost:8000/vulnerable/read?file=../../../../boot.ini
    server.add_route(
        methods=["GET"],
        path="/vulnerable/read",
        middleware=[log_middleware],
        func=server._vulnerable_file_reader
    )
    # --- END VULNERABLE ROUTES ---


    server.start_server()
