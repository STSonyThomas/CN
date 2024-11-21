from lib.server import Server
from utils.regexUtils import httpRegex

def main():
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
if __name__ == "__main__":
    main()