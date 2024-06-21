import threading
import http.server
import socketserver
import webbrowser


class HTMLServer:
	"""

	"""

	def __init__(self, html: str, port: int = 8000) -> None:
		"""

		:param html:
		:param port:
		"""
		self.html = html
		self.port = port
		self.httpd = None
		self.server_thread = None

	class RequestHandler(http.server.SimpleHTTPRequestHandler):
		def __init__(self, *args, html: str, **kwargs):
			self.html = html
			super().__init__(*args, **kwargs)

		def do_GET(self) -> None:
			self.send_response(200)
			self.send_header("Content-type", "text/html")
			self.end_headers()
			self.wfile.write(self.html.encode('utf-8'))

	def _serve_html(self) -> None:
		"""

		"""

		#
		def handler(*args, **kwargs):
			return self.RequestHandler(*args, html=self.html, **kwargs)

		self.httpd = socketserver.TCPServer(("", self.port), handler)

		try:
			print(f"Serving html at port {self.port}.")
			self.httpd.serve_forever()
		except Exception as e:
			raise Exception(f"Server error: {e}")
		finally:
			self.httpd.server_close()

	def _open_browser(self) -> None:
		"""

		"""

		webbrowser.open(f"http://localhost:{self.port}")
		input("Press any key to close the server...\n")

	def serve_html(self) -> None:
		"""

		"""

		# Start the server in a separate thread
		self.server_thread = threading.Thread(target=self._serve_html)
		self.server_thread.daemon = True
		self.server_thread.start()

		# Open the web browser to the local server and wait for it to close
		try:
			self._open_browser()
		except KeyboardInterrupt:
			print("Interrupted. Closing server.")
		finally:
			print("Shutting down server.")
			self.httpd.shutdown()
			self.httpd.server_close()
			# Ensure the thread joins properly
			self.server_thread.join()
