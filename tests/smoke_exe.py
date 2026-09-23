"""Teste local do EXE: HTTP simulado, sem acesso ao servidor corporativo."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        url = urlsplit(self.path)
        endpoint = url.path.split('/api/v1/')[-1]
        params = parse_qs(url.query)
        folder = params.get('FolderId', ['root'])[0]
        skip = int(params.get('Skip', ['0'])[0])
        count = int(params.get('Count', ['100'])[0])
        if endpoint == 'folders':
            items = {'root': [{'Id': 1, 'Name': 'Area'}],
                     '1': [{'Id': 2, 'Name': 'Subarea'}]}.get(folder, [])
        elif endpoint == 'displays':
            items = {'root': [{'Id': 10, 'Name': 'Raiz'}, {'Id': 11, 'Name': 'Raiz2'}],
                     '2': [{'Id': 12, 'Name': 'Fundo'}]}.get(folder, [])
        elif endpoint.startswith('displays/') and endpoint.endswith('/export'):
            body = {'Display': {'Symbols': [{'SymbolType': 'value', 'Name': 's',
                                            'DataSources': [r'pi:\\srv\TAG']} ]}}
            items = None
        else:
            self.send_error(404)
            return
        if items is not None:
            body = {'Items': items[skip:skip + count], 'HasMore': skip + count < len(items)}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / 'tags.txt').write_text('TAG\nAUSENTE', encoding='utf-8')
            env = {**os.environ, 'PIVISION_PASSWORD': 'dummy-local-test'}
            env.pop('PIVISION_TOKEN', None)
            run = subprocess.run([
                str(root / 'dist/PIVisionTagFinder.exe'), '--server',
                f'http://127.0.0.1:{server.server_port}/PIVision',
                '--tags', str(path / 'tags.txt'), '--username', 'test',
                '--output', str(path / 'reports'), '--page-size', '1',
            ], env=env, capture_output=True, text=True, timeout=90)
            assert run.returncode == 0, (run.stdout, run.stderr)
            report = json.loads(next((path / 'reports').glob('*/resumo.json')).read_text(encoding='utf-8'))
            assert report['completo'], report
            assert report['displays_analisados'] == 3, report
            assert report['tags_encontradas'] == ['TAG'], report
            assert report['tags_sem_ocorrencias_observadas'] == ['AUSENTE'], report
            csv = next((path / 'reports').glob('*/ocorrencias.csv')).read_text(encoding='utf-8-sig')
            assert '/Area/Subarea' in csv, csv
            print('EXE OK: HTTP local, paginacao, raiz, subpastas, exportacao, CSV e resumo.')
    finally:
        server.shutdown()
        server.server_close()
