from channels.generic.websocket import WebsocketConsumer
from . import _js_functions, _websockets, _import_js_function, \
			  _mock_queue_done, _mock_queue, _process_message, \
			  _on_close_callback, sleep, spawn
import json as jsn
import threading

class EelConsumer(WebsocketConsumer):

	def connect(self):
		global _websockets

		for js_function in _js_functions:
			_import_js_function(js_function)

		page = self.scope['query_string'].decode("utf-8").split('=')[1]
		if page not in _mock_queue_done:
			for call in _mock_queue:
				self._repeated_send(jsn.dumps(call))
			_mock_queue_done.add(page)

		_websockets += [(page, self)]

		self.accept()


	def receive(self, *, text_data):
		page = self.scope['query_string'].decode("utf-8").split('=')[1]
		if text_data is not None:
			if isinstance(text_data, str):
				text_data = jsn.loads(text_data)
			# [NOTE] gevent.spawn seems not working correctly with Django
			# and Celery is not working because of lmabda pickling issue
			# replacing original statement:
			# > spawn(_process_message, text_data, self)
			# by simple theading:
			t = threading.Thread(target=_process_message, args=(text_data, self), kwargs={})
			t.setDaemon(True)
			t.start()
		else:
			_websockets.remove((page, self))
			pass

	def disconnect(self, message):
		page = self.scope['query_string'].decode("utf-8").split('=')[1]

	def _repeated_send(self, msg):
		for attempt in range(100):
			try:
				self.send(msg)
			except Exception:
				sleep(0.001)

	def _websocket_close(page):
		if _on_close_callback is not None:
			sockets = [p for _, p in _websockets]
			_on_close_callback(page, sockets)
		else:
			sleep(1.0)
			if len(_websockets) == 0:
				#sys.exit()
				pass
