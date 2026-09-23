"""Busca somente leitura nas fontes de dados exportadas pelo PI Vision."""
from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ApiError(RuntimeError):
    pass


def base_url(server):
    server = server.strip().rstrip("/")
    if "://" not in server:
        server = "https://" + server
    parts = urlsplit(server)
    if parts.scheme not in ("https", "http") or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("Informe o servidor ou a URL do PI Vision, sem credenciais/query.")
    if server.lower().endswith("/utility/api/v1"):
        return server
    return server + ("/PIVision" if not parts.path else "") + "/Utility/api/v1"


class VisionApi:
    def __init__(self, url, session, page_size=100, timeout=60):
        self.url = base_url(url)
        self.session = session
        self.page_size = page_size
        self.timeout = timeout

    def get(self, endpoint, params=None):
        try:
            response = self.session.get(
                f"{self.url}/{endpoint}", params=params,
                timeout=self.timeout, allow_redirects=False,
            )
            if response.status_code != 200:
                raise ApiError(f"GET {endpoint}: HTTP {response.status_code}")
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ApiError(f"GET {endpoint}: {exc}") from exc

    def items(self, endpoint, folder_id=None):
        skip, seen = 0, set()
        while True:
            params = {"Skip": skip, "Count": self.page_size}
            if folder_id is not None:
                params["FolderId"] = folder_id
            data = self.get(endpoint, params)
            if not isinstance(data, dict) or not isinstance(data.get("Items"), (list, type(None))) or "Items" not in data or not isinstance(data.get("HasMore"), bool):
                raise ApiError(f"GET {endpoint}: resposta sem Items/HasMore validos")
            items = data["Items"] or []
            for item in items:
                if not isinstance(item, dict) or type(item.get("Id")) is not int or item["Id"] <= 0:
                    raise ApiError(f"GET {endpoint}: item sem Id inteiro positivo")
                if item["Id"] in seen:
                    raise ApiError(f"GET {endpoint}: Id repetido na paginacao; lista pode ter mudado")
                seen.add(item["Id"])
                yield item
            if not data["HasMore"]:
                return
            if not items:
                raise ApiError(f"GET {endpoint}: HasMore=true com pagina vazia")
            skip += len(items)


def canonical(source):
    value = unquote(source.split("?", 1)[0].strip())
    if value.lower().startswith(("pi:", "af:")):
        value = value[3:]
    return value.replace("/", "\\").casefold()


def read_tags(path):
    result = {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            result.setdefault(canonical(line), line)
    if not result:
        raise ValueError("O TXT nao contem tags. Use uma tag por linha, em UTF-8.")
    return result


def sources(node, symbol=""):
    """Percorre DataSources inclusive em estruturas de simbolos aninhadas."""
    if isinstance(node, dict):
        if "SymbolType" in node:
            symbol = str(node.get("Name", symbol))
        for key, value in node.items():
            if key == "DataSources":
                if value is None:
                    continue
                if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                    raise ApiError("DataSources em formato nao suportado")
                for source in value:
                    yield symbol, source
            elif isinstance(value, (dict, list)):
                yield from sources(value, symbol)
    elif isinstance(node, list):
        for child in node:
            yield from sources(child, symbol)


def matched_tags(source, tags):
    full = canonical(source)
    keys = {full}
    # Nome curto somente para PI Points; atributos AF exigem caminho completo.
    if not source.strip().lower().startswith("af:") and "|" not in full:
        keys.add(full.rsplit("\\", 1)[-1])
    return [tags[key] for key in sorted(keys) if key in tags]


def scan(api, tags, emit, include_unorganized=True):
    errors, found, seen_displays, seen_folders = [], set(), set(), set()
    checked, folders = 0, 0
    stack = [(None, "/")]
    if include_unorganized:
        stack.insert(0, ("Unorganized", "/[Unorganized]"))

    def failure(stage, folder, display_id, exc):
        errors.append({"etapa": stage, "pasta": folder, "display_id": display_id, "erro": str(exc)})
        print(f"AVISO: {stage} {folder} {display_id}: {exc}", file=sys.stderr)

    while stack:
        folder_id, folder = stack.pop()
        folders += 1
        print(f"Pasta: {folder}", flush=True)
        try:
            for item in api.items("displays", folder_id):
                display_id = item["Id"]
                if display_id in seen_displays:
                    continue
                seen_displays.add(display_id)
                try:
                    data = api.get(f"displays/{display_id}/export")
                    if not isinstance(data, dict) or not isinstance(data.get("Display"), dict) or not isinstance(data["Display"].get("Symbols"), list):
                        raise ApiError("Exportacao sem Display.Symbols; display nao analisado")
                    display_sources = list(sources(data))
                    rows = set()
                    for symbol, source in display_sources:
                        for tag in matched_tags(source, tags):
                            row = (tag, display_id, item.get("Name", ""), folder,
                                   item.get("Owner", ""), symbol, source,
                                   api.url[:-len('/Utility/api/v1')] + f"/#/Displays/{display_id}")
                            if row not in rows:
                                emit(row)
                                rows.add(row)
                            found.add(tag)
                    checked += 1
                    print(f"  Display {display_id}: {item.get('Name', '')} ({len(rows)} ocorrencias)", flush=True)
                except ApiError as exc:
                    failure("exportar", folder, display_id, exc)
        except ApiError as exc:
            failure("listar_displays", folder, "", exc)

        if folder_id == "Unorganized":
            continue
        try:
            for child in api.items("folders", folder_id):
                if child["Id"] in seen_folders:
                    failure("listar_pastas", folder, "", ApiError(f"Pasta repetida/ciclo: {child['Id']}"))
                    continue
                seen_folders.add(child["Id"])
                stack.append((child["Id"], folder.rstrip("/") + "/" + str(child.get("Name") or child["Id"])))
        except ApiError as exc:
            failure("listar_pastas", folder, "", exc)
    return {
        "completo": not errors, "pastas_visitadas": folders,
        "displays_descobertos": len(seen_displays), "displays_analisados": checked,
        "tags_encontradas": sorted(found),
        "tags_sem_ocorrencias_observadas": sorted(set(tags.values()) - found),
        "unorganized_incluido": include_unorganized, "erros": errors,
    }


def csv_safe(value):
    text = str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else text


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--server", help="Servidor, URL do PI Vision ou URL completa da API")
    p.add_argument("--tags", type=Path, help="TXT UTF-8 com uma tag por linha")
    p.add_argument("--username", help=r"Usuario NTLM: DOMINIO\usuario")
    p.add_argument("--auth", choices=("ntlm", "bearer"), default="ntlm")
    p.add_argument("--output", type=Path, default=Path("resultados"))
    p.add_argument("--page-size", type=int, default=100)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--ca-bundle", help="Arquivo PEM da CA corporativa")
    p.add_argument("--insecure", action="store_true", help="Desabilita validacao TLS explicitamente")
    p.add_argument("--skip-unorganized", action="store_true", help="Para versoes sem a pasta Unorganized")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    if args.page_size <= 0 or args.timeout <= 0:
        raise ValueError("page-size e timeout devem ser positivos")
    server = args.server or input("Servidor/URL do PI Vision: ").strip()
    url = base_url(server)
    tags = read_tags(args.tags or input("Caminho do TXT de tags: ").strip().strip('"'))
    with requests.Session() as session:
        session.headers.update({"Accept": "application/json", "X-Requested-With": "PIVisionTagFinder"})
        session.verify = False if args.insecure else (args.ca_bundle or True)
        if args.auth == "ntlm":
            from requests_ntlm import HttpNtlmAuth
            username = args.username or input(r"Usuario (DOMINIO\usuario): ").strip()
            password = os.environ.get("PIVISION_PASSWORD") or getpass.getpass("Senha: ")
            session.auth = HttpNtlmAuth(username, password)
            if os.environ.get("PIVISION_TOKEN"):
                session.headers["PVBearerToken"] = os.environ["PIVISION_TOKEN"]
        else:
            token = os.environ.get("PIVISION_TOKEN") or getpass.getpass("Access token: ")
            session.headers["Authorization"] = "Bearer " + token
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 502, 503, 504], allowed_methods=["GET"])
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.mount("http://", HTTPAdapter(max_retries=retry))
        # Cada execucao tem seu proprio diretorio, evitando resultados antigos misturados.
        from datetime import datetime
        output = args.output / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output.mkdir(parents=True)
        summary_path = output / "resumo.json"
        summary_path.write_text(json.dumps({"completo": False, "estado": "em_andamento"}), encoding="utf-8")
        with (output / "ocorrencias.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Tag", "DisplayId", "Display", "Pasta", "Proprietario", "Simbolo", "DataSource", "URL"])
            def emit(row):
                writer.writerow([csv_safe(v) for v in row])
                f.flush()
            summary = scan(VisionApi(url, session, args.page_size, args.timeout), tags, emit, not args.skip_unorganized)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n{'Concluido' if summary['completo'] else 'INCOMPLETO - consulte erros no resumo.json'}: {output.resolve()}")
        print(f"Displays analisados: {summary['displays_analisados']}; tags encontradas: {len(summary['tags_encontradas'])}")
        return 0 if summary["completo"] else 2


if __name__ == "__main__":
    interactive = len(sys.argv) == 1
    try:
        code = main()
    except (OSError, ValueError, EOFError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        code = 1
    except KeyboardInterrupt:
        print("\nInterrompido. Resultados parciais nao representam uma busca completa.", file=sys.stderr)
        code = 130
    if interactive:
        try:
            input("Pressione Enter para fechar...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(code)
