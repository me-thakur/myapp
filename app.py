import os
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer

DB_HOST = os.getenv("DB_HOST", "mysql-db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))


def check_database():
    try:
        connection = socket.create_connection(
            (DB_HOST, DB_PORT),
            timeout=3
        )
        connection.close()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}", flush=True)
        return False


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        db_status = check_database()

        if db_status:
            message = "Application is running. Database connection successful."
            status = 200
        else:
            message = "Application is running. Database connection failed."
            status = 503

        self.send_response(status)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

        self.wfile.write(message.encode())

server = HTTPServer(("0.0.0.0", 8080), Handler)

print("Application starting...", flush=True)
print(f"Database host: {DB_HOST}", flush=True)
print(f"Database port: {DB_PORT}", flush=True)

server.serve_forever()
