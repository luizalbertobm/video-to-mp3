# Vídeo para MP3

Aplicação para Linux em Python e GTK 3. Selecione uma gravação WebM ou MP4,
escolha onde salvar e converta o áudio para MP3 usando o FFmpeg instalado no
computador. O processamento é local; nenhum arquivo é enviado a um serviço
externo.

A janela acompanha o tema, as fontes, os ícones e os controles de janela do
desktop. No Zorin OS/GNOME, usa o visual configurado no sistema, incluindo modo
claro ou escuro. Abrir e salvar usam `Gtk.FileChooserNative`, com navegação por
pastas e locais do sistema. Não há paleta de cores ou tema fixo na aplicação.

## Abrir

No menu de aplicativos do Linux, procure **Vídeo para MP3**. Também é possível
abrir pelo terminal:

```bash
python3 app.py
```

1. Clique em **Selecionar…** e escolha o arquivo WebM ou MP4.
2. Confira o destino sugerido ou use **Salvar como…**.
3. Escolha a qualidade; **128 kbps** é o padrão para reuniões.
4. Clique em **Converter para MP3**. Você pode cancelar durante a conversão.
5. Use **Abrir pasta** para encontrar o resultado e enviá-lo ao Tactiq.

O arquivo original é preservado. Arquivos existentes no destino não são
sobrescritos: escolha outro nome. A primeira faixa de áudio é convertida para
MP3 estéreo de 44,1 kHz, qualquer que seja o codec de origem (Opus, Vorbis, AAC).
Arquivos sem áudio produzem uma mensagem de erro. Se a duração do vídeo estiver
ausente, o progresso é exibido sem percentual. Arquivos temporários são
removidos ao cancelar ou em caso de erro tratado.

## Requisitos

- Python 3.10 ou superior com PyGObject e GTK 3.20 ou superior;
- FFmpeg e FFprobe no PATH, com o encoder `libmp3lame`.

Esses requisitos já estavam disponíveis na máquina onde a aplicação foi criada.
Não há dependências pip. Em outra máquina Debian/Ubuntu, os pacotes de sistema
são `python3`, `python3-gi`, `gir1.2-gtk-3.0` e `ffmpeg`.

## Verificar

```bash
cd /home/luiz/projects/bee/webm-to-mp3
python3 -m unittest -v
```

Os testes geram pequenos arquivos WebM e MP4 sintéticos com FFmpeg; não usam
suas gravações.
Os testes da interface precisam de uma sessão gráfica; sem ela, são marcados
como ignorados. Eles validam os seletores nativos, conversão completa e cancelamento.
