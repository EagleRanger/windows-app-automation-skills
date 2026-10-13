"""Identity-checked, local-only client. No retries; no ArcPy or pip dependency.

Exit codes: 0 success, 1 remote failure, 2 unknown outcome, 3 locally blocked.
The add-in itself is a trusted-user loopback service, not a security sandbox.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import sys
import time
import uuid

MAX_BYTES = 8 * 1024 * 1024
READ_ONLY = frozenset({
    'ping', 'get_capabilities', 'diagnose', 'get_arcgis_info',
    'get_project_info', 'list_maps', 'get_layers', 'get_layer_info',
    'get_broken_layers', 'get_map_extent', 'list_layouts', 'get_layout_info',
    'list_geoprocessing_tools', 'describe_geoprocessing_tool', 'list_toolboxes',
    'get_messages', 'get_map_view', 'get_raster_palette',
})
SCHEMA_PATH = Path(__file__).resolve().parents[1] / 'assets/addin-source/Resources/tools.json'


class Blocked(Exception):
    pass


class Unknown(Exception):
    pass


class RemoteFailure(Exception):
    pass


def schemas():
    return {item['name']: item for item in json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))['tools']}


def redact(value):
    """Do not echo credential-looking response fields to terminal or receipts."""
    if isinstance(value, dict):
        return {key: ('[REDACTED]' if any(word in key.lower() for word in
                ('password', 'secret', 'token', 'credential', 'api_key', 'apikey', 'authorization'))
                else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def absolute_path(value, label):
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        raise Blocked(label + ' must be an absolute local path')
    # UNC/network roots and device namespaces are outside this local-only client.
    if value.startswith(('\\\\', '//')) or '\x00' in value:
        raise Blocked(label + ' must not be a network/device path')
    return Path(value).resolve()


def same_path(left, right):
    return os.path.normcase(str(left)) == os.path.normcase(str(right))


def validate_params(params, schema):
    if not isinstance(params, dict):
        raise Blocked('params-json must contain an object')
    model = schema.get('inputSchema', {})
    properties = model.get('properties', {})
    if set(params) - set(properties):
        raise Blocked('Unknown command parameter; inspect --schema')
    if any(name not in params for name in model.get('required', [])):
        raise Blocked('Required command parameter missing; inspect --schema')
    types = {'string': str, 'array': list, 'object': dict, 'boolean': bool}
    for name, value in params.items():
        kind = properties.get(name, {}).get('type')
        if kind in types and not isinstance(value, types[kind]):
            raise Blocked('Invalid parameter type; inspect --schema')
        if kind in ('integer', 'number') and (isinstance(value, bool) or
                not isinstance(value, (int, float)) or not math.isfinite(value) or
                (kind == 'integer' and not isinstance(value, int))):
            raise Blocked('Invalid numeric parameter; inspect --schema')


def discover(directory):
    directory = Path(directory)
    if not directory.is_dir():
        return []
    found = set()
    for file in sorted(directory.glob('*.json')):
        try:
            if file.stat().st_size > 65536:
                continue
            item = json.loads(file.read_text(encoding='utf-8-sig'))
            pid, port = item.get('pid'), item.get('port')
            if (type(pid) is int and pid > 0 and type(port) is int and 1 <= port <= 65535
                    and item.get('host', '127.0.0.1') == '127.0.0.1'):
                found.add((pid, port))
        except (OSError, ValueError, AttributeError):
            continue
    return [{'pid': pid, 'port': port} for pid, port in sorted(found)]


def endpoint(args):
    if args.host != '127.0.0.1':
        raise Blocked('Only literal 127.0.0.1 is supported; DNS and remote hosts are refused')
    if args.pid is not None and args.pid <= 0:
        raise Blocked('pid must be positive')
    if args.port is not None and not 1 <= args.port <= 65535:
        raise Blocked('port is out of range')
    if args.pid is not None and args.port is not None:
        return args.pid, args.port
    candidates = [item for item in discover(args.instances_dir)
                  if (args.pid is None or item['pid'] == args.pid)
                  and (args.port is None or item['port'] == args.port)]
    if len(candidates) != 1:
        raise Blocked('Specify --pid and --port; discovery did not identify exactly one instance')
    return candidates[0]['pid'], candidates[0]['port']


def output_target(value, root, *, shapefile=False):
    path = absolute_path(value, 'output')
    if root is None:
        raise Blocked('File output requires --output-root')
    root = absolute_path(root, 'output-root')
    if not root.is_dir() or root == Path(root.anchor) or same_path(root, Path.home()):
        raise Blocked('output-root must be an existing specific task directory')
    if path == root or root not in path.parents:
        raise Blocked('Output is outside output-root')
    if not path.parent.is_dir() or path.exists():
        raise Blocked('Output parent must exist and destination must be new')
    # ArcGIS datasets inside a GDB cannot be reliably checked by Path.exists().
    if any(part.lower().endswith(('.gdb', '.sde', '.mdb')) for part in path.parts):
        raise Blocked('Use a new file output, not a geodatabase dataset')
    if shapefile:
        if path.suffix.lower() != '.shp':
            raise Blocked('GP output must be a new .shp file in this client')
        if any(path.parent.glob(path.stem + '.*')):
            raise Blocked('Shapefile destination or sidecar already exists')
    return path


def prepare_command(args, params):
    known = schemas()
    if args.command not in known or args.command == 'check_extension':
        raise Blocked('Unknown or license-related command is disabled')
    validate_params(params, known[args.command])
    write = args.command not in READ_ONLY
    if write and not args.allow_write:
        raise Blocked('This command requires explicit --allow-write')
    expected = None
    target = None
    if write:
        if args.pid is None:
            raise Blocked('Writes require an explicit --pid, not discovery alone')
        expected = absolute_path(args.expected_project, 'expected-project')
        if expected.suffix.lower() != '.aprx':
            raise Blocked('expected-project must be an APRX path')
        if not args.receipt:
            raise Blocked('Writes require a new exclusive --receipt')
    elif args.expected_project:
        expected = absolute_path(args.expected_project, 'expected-project')
    if args.command == 'save_project':
        target = output_target(params.get('save_as_path'), args.output_root)
        if target.suffix.lower() != '.aprx':
            raise Blocked('SaveAs destination must end in .aprx; in-place saves are disabled')
        params['save_as_path'] = str(target)
    elif args.command in ('export_layout', 'export_map_view'):
        target = output_target(params.get('output_path'), args.output_root)
        params['output_path'] = str(target)
    elif args.command == 'run_geoprocessing_tool':
        tool = str(params.get('tool_name', '')).lower()
        if tool not in ('analysis.buffer', 'buffer_analysis', 'analysis.clip', 'clip_analysis'):
            raise Blocked('Only analysis.Buffer and analysis.Clip are enabled')
        if params.get('overwrite') not in (None, False) or params.get('checkout_extension'):
            raise Blocked('GP overwrite and extension checkout are disabled')
        params['overwrite'] = False
        has_args = isinstance(params.get('args'), list)
        has_named = isinstance(params.get('parameters'), dict)
        if has_args == has_named:
            raise Blocked('GP requires exactly one of args or parameters')
        if has_args:
            index = 1 if 'buffer' in tool else 2
            if len(params['args']) <= index:
                raise Blocked('GP output argument missing')
            target = output_target(params['args'][index], args.output_root, shapefile=True)
            params['args'][index] = str(target)
        else:
            named = params['parameters']
            names = [key for key in named if key.lower() == 'out_feature_class']
            if len(names) != 1:
                raise Blocked('GP requires out_feature_class')
            target = output_target(named[names[0]], args.output_root, shapefile=True)
            named[names[0]] = str(target)
    return write, expected, target


def remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise Unknown('Total deadline expired; inspect outputs before any retry')
    return seconds


def rpc(port, command, params, deadline):
    request_id = uuid.uuid4().int & ((1 << 53) - 1)
    payload = json.dumps({'id': request_id, 'command': command, 'params': params},
                         ensure_ascii=False, allow_nan=False).encode('utf-8') + b'\n'
    if len(payload) > MAX_BYTES:
        raise Blocked('Request exceeds 8 MiB')
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=remaining(deadline)) as sock:
            sock.settimeout(remaining(deadline))
            sock.sendall(payload)
            data = bytearray()
            while b'\n' not in data:
                sock.settimeout(remaining(deadline))
                chunk = sock.recv(min(65536, MAX_BYTES + 1 - len(data)))
                if not chunk:
                    raise Unknown('Connection closed before a complete response; no retry')
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise Unknown('Response exceeds 8 MiB; no retry')
            line, extra = bytes(data).split(b'\n', 1)
            if extra.strip():
                raise Unknown('Multiple response frames; no retry')
            result = json.loads(line.decode('utf-8'))
            if not isinstance(result, dict) or type(result.get('id')) is not int or result['id'] != request_id:
                raise Unknown('Response id mismatch; no retry')
            if type(result.get('success')) is not bool:
                raise Unknown('Invalid response success field; no retry')
            if not result['success']:
                raise RemoteFailure('Remote command reported failure; inspect local GIS state')
            return result.get('data')
    except (OSError, UnicodeError, ValueError) as exc:
        raise Unknown('Transport or response failure; inspect outputs before any retry') from exc


def verify_project(port, expected, deadline):
    data = rpc(port, 'get_project_info', {}, deadline)
    if not isinstance(data, dict):
        raise Unknown('Invalid project identity response')
    try:
        actual = absolute_path(data.get('path'), 'reported project')
    except Blocked as exc:
        raise Unknown('Invalid project identity response') from exc
    if not same_path(actual, expected):
        raise Blocked('Project identity mismatch; operation not sent')
    return actual


def parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples (PowerShell; replace PID and paths):
  python bridge_client.py --discover
  python bridge_client.py --schema export_layout
  python bridge_client.py --port 6510 --pid 1234 --command get_project_info
  python bridge_client.py --port 6510 --pid 1234 --expected-project C:/GIS/source.aprx --command save_project --params-json '{"save_as_path":"C:/GIS/output/copy.aprx"}' --allow-write --output-root C:/GIS/output --receipt C:/GIS/output/save-receipt.json
Each invocation rechecks identity. After SaveAs use the new APRX as expected-project.
--timeout bounds the whole sequence, not each socket. Receipts are local and exclusive.
preview_layout uses the add-in's temporary PNG; it is classified as a write.
GP outputs are deliberately limited to new .shp files; GDB outputs are refused.
This client cannot lock Pro against another controller or provide server-side path guards.''')
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--discover', action='store_true')
    mode.add_argument('--schema', metavar='COMMAND')
    mode.add_argument('--command')
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int)
    p.add_argument('--pid', type=int)
    p.add_argument('--instances-dir', default=str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'ArcGIS-MCP/instances'))
    p.add_argument('--expected-project')
    p.add_argument('--params-json', default='{}', help='Inline JSON object, not a file path')
    p.add_argument('--allow-write', action='store_true')
    p.add_argument('--output-root')
    p.add_argument('--receipt', help='New local audit file, created exclusively before network calls')
    p.add_argument('--timeout', type=float, default=20, help='Total seconds for all calls (default 20)')
    return p


def run(args):
    receipt = None
    record = {'status': 'BLOCKED_BEFORE_MUTATION', 'command': args.command,
              'started_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'retry': False}
    dispatched = False
    try:
        if args.host != '127.0.0.1':
            raise Blocked('Only literal 127.0.0.1 is supported')
        if args.discover:
            return 0, {'status': 'DISCOVERY_ONLY_NOT_LIVENESS', 'instances': discover(args.instances_dir)}
        if args.schema:
            if args.schema not in schemas():
                raise Blocked('Unknown command schema')
            return 0, {'status': 'SCHEMA_ONLY', 'schema': schemas()[args.schema],
                       'disabled': args.schema == 'check_extension'}
        if not math.isfinite(args.timeout) or not 0 < args.timeout <= 600:
            raise Blocked('timeout must be finite, positive, and at most 600 seconds')
        try:
            params = json.loads(args.params_json, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (ValueError, TypeError):
            raise Blocked('Invalid params-json')
        write, expected, target = prepare_command(args, params)
        pid, port = endpoint(args)
        record.update(pid=pid, port=port, write=write,
                      parameters_sha256=hashlib.sha256(args.params_json.encode()).hexdigest())
        if args.receipt:
            receipt_path = absolute_path(args.receipt, 'receipt')
            if target and same_path(receipt_path, target):
                raise Blocked('Receipt and output must be different files')
            try:
                receipt = receipt_path.open('x', encoding='utf-8')
                receipt.write(json.dumps(record) + '\n')
                receipt.flush()
                os.fsync(receipt.fileno())
            except OSError as exc:
                raise Blocked('Receipt must be a new writable file in an existing directory') from exc
        deadline = time.monotonic() + args.timeout
        identity = rpc(port, 'ping', {}, deadline)
        if not isinstance(identity, dict) or type(identity.get('pid')) is not int or identity['pid'] != pid:
            raise Blocked('PID identity mismatch; requested operation not sent')
        if expected:
            verify_project(port, expected, deadline)
        # Recheck filesystem immediately before dispatch; another controller still
        # requires external single-writer coordination (the protocol has no lock).
        if target:
            output_target(str(target), args.output_root, shapefile=args.command == 'run_geoprocessing_tool')
        dispatched = True
        data = identity if args.command == 'ping' else rpc(port, args.command, params, deadline)
        current_project = None
        if write:
            try:
                current_project = str(verify_project(port, target if args.command == 'save_project' else expected, deadline))
            except (Blocked, RemoteFailure) as exc:
                raise Unknown('Write returned, but post-write project identity was not verified; no retry') from exc
        record.update(status='SUCCESS_RETURNED_NOT_OUTPUT_ACCEPTANCE', data=redact(data))
        if current_project:
            record['current_project'] = current_project
        return 0, record
    except Blocked as exc:
        record.update(status='UNKNOWN_OUTCOME' if dispatched else 'BLOCKED_BEFORE_MUTATION', error=str(exc))
        return (2 if dispatched else 3), record
    except RemoteFailure as exc:
        record.update(status='REMOTE_FAILURE', error=str(exc))
        return 1, record
    except Unknown as exc:
        record.update(status='UNKNOWN_OUTCOME', error=str(exc))
        return 2, record
    except (OSError, ValueError, KeyError, TypeError) as exc:
        record.update(status='UNKNOWN_OUTCOME' if dispatched else 'BLOCKED_BEFORE_MUTATION',
                      error='Local client/configuration error; inspect receipt and state')
        return (2 if dispatched else 3), record
    finally:
        if receipt is not None:
            try:
                receipt.write(json.dumps(redact(record), ensure_ascii=False, allow_nan=False) + '\n')
                receipt.flush()
                os.fsync(receipt.fileno())
            finally:
                receipt.close()


def main(argv=None):
    code, result = run(parser().parse_args(argv))
    print(json.dumps(redact(result), ensure_ascii=False, allow_nan=False))
    return code


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
