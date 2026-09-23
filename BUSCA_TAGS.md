# Busca de tags nos displays do PI Vision

`buscar_tags.py` percorre a raiz, todas as pastas/subpastas retornadas pela API e a pasta especial `Unorganized`. Lista pastas e displays com `FolderId`, `Skip`, `Count` e `HasMore`; exporta cada display uma vez e procura as tags nos campos `DataSources`, inclusive em estruturas aninhadas. Faz apenas GETs.

## Usar o executável

Execute `dist/PIVisionTagFinder.exe` por duplo clique e informe servidor, caminho do TXT, usuário `DOMINIO\usuario` e senha. A senha não aparece na tela nem é gravada. O executável é de console e não exige Python instalado no computador de destino.

Ou execute no PowerShell:

```powershell
.\dist\PIVisionTagFinder.exe --server https://SERVIDOR/PIVision --tags .\tags.txt --username 'DOMINIO\usuario'
```

O servidor pode ser um hostname, a URL do PI Vision (inclusive diretório virtual personalizado) ou a URL completa terminada em `/Utility/api/v1`. Os caminhos relativos são resolvidos na pasta de trabalho atual.

Crie `tags.txt` em UTF-8, com uma tag por linha:

```text
SINUSOID
CDT158
\\PISERVER\TAG.EXEMPLO
```

Use `tags.example.txt` como modelo. Linhas vazias e comentários iniciados por `#` são ignorados. A comparação é exata, sem diferenciar maiúsculas/minúsculas: `TAG1` não encontra `TAG10`. Uma tag simples encontra PI Points com esse nome em qualquer servidor; para distinguir servidores, forneça `\\servidor\tag`. Prefixo `pi:`, codificação URL e metadados após `?` são tratados.

## Relatórios

Cada execução cria uma subpasta datada em `resultados` (ou no caminho de `--output`):

- `ocorrencias.csv`: UTF-8 com BOM, separado por ponto e vírgula, com tag, ID/nome do display, pasta completa, proprietário, símbolo, fonte original e link. Uma linha por tag/display/símbolo/fonte; células que poderiam virar fórmulas no Excel recebem apóstrofo de proteção.
- `resumo.json`: displays analisados, tags encontradas, tags sem ocorrências observadas e erros por pasta/display. Se houver falhas, `completo` será `false`; ausência de ocorrência não comprova ausência no servidor. Uma execução interrompida mantém o marcador `em_andamento` e CSV parcial.

Códigos de saída: `0` busca concluída no escopo selecionado; `2` busca incompleta; `1` erro de configuração/arquivo; `130` interrupção.

## Autenticação e compatibilidade

A API requer PI Vision com Display API disponível (introduzida em 2021) e conta autorizada como **Utility User** ou **Administrator**. A cobertura depende das permissões e dos displays retornados pelo servidor. NTLM usa o usuário/senha informados, seguindo o exemplo local `PYTHON/Advanced/extract_tags.py`.

Para automação, a senha pode vir da variável de ambiente `PIVISION_PASSWORD`. Para servidor OpenID Connect, use `--auth bearer` e informe um access token, ou defina `PIVISION_TOKEN`. O programa não emite/renova tokens. Em modo NTLM, quando `PIVISION_TOKEN` estiver definido, também envia `PVBearerToken` para configuração mista Windows/OIDC.

TLS é validado por padrão. Para CA interna, use `--ca-bundle C:\certificados\ca.pem`. `--insecure` desativa explicitamente essa validação. Timeout por requisição: `--timeout 60`; tamanho de página: `--page-size 100`. Há até três novas tentativas para falhas transitórias.

Versões antigas podem rejeitar `FolderId=Unorganized`; isso aparece como erro e resultado incompleto. Nesses servidores, use `--skip-unorganized` para buscar apenas a raiz e as pastas comuns. Essa exclusão fica registrada no resumo.

**Limite da busca:** examina referências explícitas em `DataSources` do JSON exportado. Um atributo AF pode apontar para um PI Point sem expor seu nome no display; resolver esse vínculo exige AF SDK ou PI Web API e não é feito aqui. Para referências AF, forneça o caminho completo `af:\\servidor\base\elemento|atributo`. Não infere tags de coleções dinâmicas, cálculos ou símbolos personalizados que armazenem referências fora de `DataSources`. Exportações sem `Display.Symbols` são registradas como não analisadas.

## Executar Python e gerar EXE

No Windows, com Python 3.10 ou superior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-search.txt
.\.venv\Scripts\python.exe buscar_tags.py --server SERVIDOR --tags tags.txt --username 'DOMINIO\usuario'
```

Para testar e empacotar automaticamente:

```powershell
.\build.ps1
```

Ou empacote diretamente após instalar as dependências:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --console --name PIVisionTagFinder --icon PYTHON/Advanced/extract.ico buscar_tags.py
```

O build deve ser feito no Windows para produzir o `.exe`. O script também executa `tests/smoke_exe.py`, que inicia um servidor HTTP local temporário e testa o próprio executável, incluindo geração dos relatórios. Os testes usam uma API simulada e cobrem paginação, pastas aninhadas, duplicatas, falhas e comparação exata; não validam o handshake NTLM nem substituem validação no servidor real.

## Referências

- [Visão geral oficial](https://docs.aveva.com/bundle/pi-vision-api-reference/page/overview.html)
- [Folders: contrato e paginação](https://docs.aveva.com/bundle/pi-vision-api-reference/page/api-reference/utility/folders.html)
- [Displays: listagem e exportação](https://docs.aveva.com/bundle/pi-vision-api-reference/page/api-reference/utility/displays.html)
- Exemplos locais: `PYTHON/Basic/overview_visionapi.ipynb` e `PYTHON/Advanced/extract_tags.py`.
