# Vídeo para MP3

Aplicação desktop em Python e Qt/PySide6 para converter gravações **WebM e MP4**
em MP3, localmente. Nenhuma gravação é enviada a serviços externos.

## Plataformas e pacotes

| Sistema alvo | Arquitetura | Pacote |
|---|---|---|
| Windows 11 | x64 | `video-to-mp3-1.0.0-windows-x64.zip` |
| macOS 13 ou superior | Intel x64 | `video-to-mp3-1.0.0-macos-x64.zip` |
| macOS 13 ou superior | Apple Silicon ARM64 | `video-to-mp3-1.0.0-macos-arm64.zip` |
| Ubuntu/Zorin base 22.04 ou superior | x64 | `video-to-mp3-1.0.0-linux-x64.tar.gz` |

Os pacotes incluem Python, Qt, FFmpeg e FFprobe; não é necessário instalá-los
separadamente. É preciso **extrair a pasta inteira**, mantendo suas dependências.
Os arquivos em `dist/` são gerados pelo build; os quatro artefatos são produzidos
pelo workflow **Test and package desktop apps** no GitHub Actions.

- **Windows:** extraia o ZIP e abra `video-to-mp3.exe`.
- **macOS:** escolha o pacote para o seu processador, extraia e copie
  `Vídeo para MP3.app` para Aplicativos. Os builds têm assinatura técnica ad hoc,
  sem certificado Developer ID/notarização. Se o sistema bloquear, verifique a
  origem do pacote e use a opção **Abrir Mesmo Assim** em Privacidade e Segurança,
  quando disponível. Políticas corporativas podem impedir sua execução.
- **Linux:** extraia o `.tar.gz` e abra `video-to-mp3`. Opcionalmente execute
  `./install.sh` para adicionar ao menu. Não mova a pasta após criar o lançador.
  O sistema precisa das bibliotecas básicas de desktop: glibc 2.35+, EGL/OpenGL,
  X11/xcb ou Wayland. Em Ubuntu/Zorin, se necessário:
  `sudo apt install libgl1 libegl1 libopengl0 libxcb-cursor0 libxkbcommon-x11-0`.

Windows também pode mostrar avisos por falta de certificado comercial. Esta
primeira versão destina-se a uso pessoal/equipe; não possui atualização automática.
Para atualizar, feche a aplicação, extraia o novo pacote em outra pasta e substitua
a instalação anterior. No Linux, execute novamente `install.sh`. Para remover,
use `./install.sh --uninstall` no Linux e apague a pasta/app. Seus áudios permanecem.

## Usar

1. Clique em **Selecionar…** e escolha o WebM ou MP4.
2. Confira o destino sugerido ou use **Salvar como…**.
3. Escolha a qualidade: 64, **128** (padrão), 192 ou 320 kbps.
4. Clique em **Converter para MP3**. Você pode cancelar inclusive durante a análise.
5. Use **Abrir pasta** para encontrar o resultado.

A primeira faixa de áudio vira MP3 estéreo de 44,1 kHz. Arquivos existentes nunca
são sobrescritos, mesmo se outro programa ocupar o destino durante a conversão.
O arquivo original é preservado. Vídeos sem áudio produzem uma mensagem de erro.
Sem duração conhecida, o progresso é indeterminado. Fechar durante a conversão
pede confirmação e aguarda o encerramento do processo.

O resultado é publicado por hard link quando disponível. Em FAT/exFAT e outros
sistemas sem hard links, a aplicação cria o destino de forma exclusiva e copia o
MP3: nesse intervalo, ele pode aparecer incompleto. Cancelamento ou erro tratado
remove a saída parcial criada pela operação. Uma queda de energia ou encerramento
forçado pode deixar temporários/saídas parciais; não existe limpeza garantida nesses casos.

A interface usa Qt Widgets, paleta e estilo padrão da plataforma, seletores nativos
quando disponíveis e ícones próprios. Ela não replica necessariamente o tema GTK.

## Desenvolvimento

Requisitos: Python 3.10–3.13 e FFmpeg/FFprobe no `PATH` com `libmp3lame`.
No Linux, rodar do fonte exige as mesmas bibliotecas de desktop do pacote, que
o Qt carrega em tempo de execução. Em Ubuntu/Zorin:
`sudo apt install libgl1 libegl1 libopengl0 libxcb-cursor0 libxkbcommon-x11-0`.
Sem `libxcb-cursor0`, o Qt 6.5+ aborta ao iniciar em sessões X11.
Os builds de distribuição usam Python 3.12 e dependências fixadas em `uv.lock`.
Os testes geram gravações sintéticas usando uma instalação completa de FFmpeg,
com libopus e libvpx; não usam suas gravações. A versão reduzida incluída no pacote
serve à conversão e ao teste de pacote, não substitui a instalação de desenvolvimento.

Com [uv](https://docs.astral.sh/uv/):

```bash
uv sync --frozen --extra build
uv run --frozen python app.py
uv run --frozen python -m unittest -v
```

Sem uv, crie um ambiente virtual e instale `python -m pip install -e '.[build]'`.
Execute `python app.py` dentro dele. Para builds reproduzíveis, use uv e o lock.
O antigo requisito de GTK/PyGObject foi removido.

## Compilar um pacote

Faça o build **no sistema e arquitetura alvo**. Linux usa Ubuntu 22.04 como base;
compilar em distribuições mais novas pode elevar a versão mínima de glibc.
Qt/PySide6 6.8.3 foi escolhido para manter compatibilidade com essa base e macOS 13.
No macOS, use Xcode Command Line Tools; no Linux, GCC, make, pkg-config, curl,
xz-utils e Perl; no Windows, MSYS2 MINGW64 com GCC, make, diffutils, pkgconf,
Perl, tar, curl e xz. O workflow lista os pacotes exatos de sistema.

```bash
uv sync --frozen --extra build
bash scripts/build-media.sh
uv run --frozen --extra build python scripts/test_media.py
uv run --frozen --extra build python scripts/package.py
uv run --frozen --extra build python scripts/check_package.py
```

No Windows, execute apenas `build-media.sh` no shell MSYS2 MINGW64; execute os
comandos Python com Python Windows, não com Python MSYS2. Não use WSL para gerar
o pacote Windows. O download das fontes e dependências requer internet; os
pacotes finais funcionam offline.

O script verifica hashes das fontes FFmpeg 8.1.1 e LAME 3.100, compila ambos,
registra configuração/hashes dos binários e inclui as fontes na distribuição.
`package.py` cria um build PyInstaller em diretório, arquivos de licença, arquivo
compactado e checksum SHA256. No macOS, PyInstaller aplica assinatura ad hoc.
Os recursos visuais são próprios e podem ser regenerados por
`uv run --extra build python scripts/make_icons.py`.

Leia [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) e mantenha os materiais de
licenciamento e `media-sources/` ao redistribuir. Bibliotecas Qt ficam separadas
para permitir sua substituição conforme a LGPL.

## Verificação e limites de validação

O CI executa testes do motor e da interface nas quatro arquiteturas, compila o
pacote e testa o arquivo **extraído**, com diretório de trabalho diferente e
`PATH` vazio. O teste interno `--smoke-test PASTA` gera WebM/MP4 sintéticos,
converte pela janela Qt e verifica o MP3 com o FFprobe incluído. Ele grava
`smoke-result.json` nessa pasta; não é uma interface de uso normal.

No Linux, `bash scripts/check_linux_container.sh` também testa o pacote em um
container Ubuntu 22.04 com bibliotecas básicas de desktop, sem Python/FFmpeg e
com a rede desligada durante a execução. Requer Docker.

Os testes automatizados de interface usam Qt offscreen e seletores Qt de teste;
não comprovam integração visual dos diálogos nativos. Antes de divulgar uma
versão, registrar a verificação manual em máquinas/VMs sem Python/FFmpeg:

- Windows 11 x64 e macOS 13 nas duas arquiteturas: abrir o pacote, escolher/salvar,
  converter, cancelar, fechar durante conversão e abrir a pasta do resultado.
- Ubuntu/Zorin base 22.04: repetir em sessões X11 e Wayland.
- Verificar escalas de tela, navegação por teclado, tema claro/escuro e ausência
  de console no Windows; testar gravação em pendrive exFAT.

Os runners Windows Server 2022/macOS 14/15 não substituem os testes manuais em
Windows 11/macOS 13. Suporte nas versões mínimas só deve ser anunciado como
validado após essas verificações.
