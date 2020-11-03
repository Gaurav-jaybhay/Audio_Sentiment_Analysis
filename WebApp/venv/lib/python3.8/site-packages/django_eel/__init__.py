from django.http import HttpResponse
import sys, os
import re as rgx
import random as rnd
import pkg_resources as pkg
import json as jsn
import gevent as gvt
import django_eel.browsers as brw

_js_root_dir = os.sep.join(['django_eel', 'static', 'eel', 'js'])
_eel_js_file = pkg.resource_filename(pkg.Requirement.parse('django-eel'), 'django_eel/static/eel/js/eel.js')
#_eel_js = open(os.sep.join([_js_root_dir, _eel_js_file]), encoding='utf-8').read()
_eel_js = open(_eel_js_file, encoding='utf-8').read()

_websockets = []
_exposed_functions = {}
_js_functions = []
_call_number = 0
_start_geometry = {}
_mock_queue = []
_mock_queue_done = set()
_on_close_callback = None
_call_return_values = {}
_call_return_callbacks = {}
_default_options = {
    'mode': 'chrome-app',
    'host': 'localhost',
    'port': 8000,
    'chromeFlags': []
}

# Public functions
def expose(name_or_function=None):
    # Deal with '@eel.expose()' - treat as '@eel.expose'
    if name_or_function is None:
        return expose

    if type(name_or_function) == str:   # Called as '@eel.expose("my_name")'
        name = name_or_function

        def decorator(function):
            _expose(name, function)
            return function
        return decorator
    else:
        function = name_or_function
        _expose(function.__name__, function)
        return function

def init(path):
    global root_path, _js_functions
    root_path = _get_real_path(path)

    js_functions = set()
    for root, _, files in os.walk(root_path):
        for name in files:
            allowed_extensions = '.js .html .txt .htm .xhtml'.split()
            if not any(name.endswith(ext) for ext in allowed_extensions):
                continue

            try:
                with open(os.path.join(root, name), encoding='utf-8') as file:
                    contents = file.read()
                    expose_calls = set()
                    finder = rgx.findall(r'eel\.expose\((.*)\)', contents)
                    for expose_call in finder:
                        expose_call = expose_call.strip()
                        msg = "eel.expose() call contains '(' or '='"
                        assert rgx.findall(
                            r'[\(=]', expose_call) == [], msg
                        expose_calls.add(expose_call)
                    js_functions.update(expose_calls)
            except UnicodeDecodeError:
                pass    # Malformed file probably

    _js_functions = list(js_functions)
    for js_function in _js_functions:
        _mock_js_function(js_function)

# start localhost browsing
def start(*start_urls, **kwargs):
    global _on_close_callback

    block = kwargs.pop('block', True)
    options = kwargs.pop('options', {})
    size = kwargs.pop('size', None)
    position = kwargs.pop('position', None)
    geometry = kwargs.pop('geometry', {})
    _on_close_callback = kwargs.pop('callback', None)

    for k, v in list(_default_options.items()):
        if k not in options:
            options[k] = v

    _start_geometry['default'] = {'size': size, 'position': position}
    _start_geometry['pages'] = geometry

    if options['port'] == 0:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        options['port'] = sock.getsockname()[1]
        sock.close()

    brw.open(start_urls, options)

def sleep(seconds):
    gvt.sleep(seconds)

def spawn(function, *args, **kwargs):
    gvt.spawn(function, *args, **kwargs)

# Routes : eel/urls.py
# intercepts request of `eel.js`, 
# replaces /** _py_functions **/ and /** _start_geometry **/
def _eel(request):
    funcs = list(_exposed_functions.keys())
    page = _eel_js.replace('/** _py_functions **/',
                           '_py_functions: %s,' % funcs)
    page = page.replace('/** _start_geometry **/',
                        '_start_geometry: %s,' % jsn.dumps(_start_geometry))
    response = HttpResponse(content=page)
    response['Content-Type'] = 'application/javascript'
    return response

# Private functions
def _expose(name, function):
    msg = 'Already exposed function with name "%s"' % name
    assert name not in _exposed_functions, msg
    _exposed_functions[name] = function

def _get_real_path(path):
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, path)
    else:
        return os.path.abspath(path)

def _mock_js_function(f):
    exec('%s = lambda *args: _mock_call("%s", args)' % (f, f), globals())

def _mock_call(name, args):
    call_object = _call_object(name, args)
    global _mock_queue
    _mock_queue += [call_object]
    return _call_return(call_object)

def _call_object(name, args):
    global _call_number
    _call_number += 1
    call_id = _call_number + rnd.random()
    return {'call': call_id, 'name': name, 'args': args}

def _call_return(call):
    call_id = call['call']

    def return_func(callback=None):
        if callback is not None:
            _call_return_callbacks[call_id] = callback
        else:
            for w in range(10000):
                if call_id in _call_return_values:
                    return _call_return_values.pop(call_id)
                sleep(0.001)
    return return_func

def _import_js_function(f):
    exec('%s = lambda *args: _js_call("%s", args)' % (f, f), globals())

def _process_message(message, ws):
    if 'call' in message:
        return_val = _exposed_functions[message['name']](*message['args'])
        ws._repeated_send(jsn.dumps({  'return': message['call'],
                                        'value': return_val    })) 
    elif 'return' in message:
        call_id = message['return']
        if call_id in _call_return_callbacks:
            callback = _call_return_callbacks.pop(call_id)
            callback(message['value'])
        else:
            _call_return_values[call_id] = message['value']
    else:
        print('Invalid message received: ', message)

def _js_call(name, args):
    call_object = _call_object(name, args)
    for _, ws in _websockets:
        ws._repeated_send(jsn.dumps(call_object))
    return _call_return(call_object)