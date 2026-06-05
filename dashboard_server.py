import http.server
import socketserver
import os

PORT = 5000

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Disable browser caching so new pictures refresh instantly
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def main():
    # Make sure we serve from the active TacoCam1 directory context
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    handler = CustomHandler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"🚀 TacoSam Dashboard active at: http://localhost:{PORT}")
        print("Keep this terminal window running. Open the link above in your browser!")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Dashboard Server.")
            httpd.shutdown()

if __name__ == "__main__":
    main()