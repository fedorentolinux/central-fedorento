#!/usr/bin/python3
import os
import platform
import shutil
import subprocess
import tempfile

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

APP_ID = "org.fedorento.CentralFedorento"
VERSION = "1.13"

FULL_UPDATE = """set -e
printf '\n== Atualizando repositórios ==\n'
dnf makecache --refresh
printf '\n== Atualização completa do sistema ==\n'
dnf upgrade --refresh -y
printf '\n== Removendo dependências órfãs ==\n'
dnf autoremove -y
printf '\n== Limpando caches ==\n'
dnf clean all
printf '\n== Atualizando aplicativos Flatpak ==\n'
REAL_UID="${PKEXEC_UID:-0}"
REAL_USER="$(getent passwd "$REAL_UID" | cut -d: -f1)"
REAL_HOME="$(getent passwd "$REAL_UID" | cut -d: -f6)"
if command -v flatpak >/dev/null 2>&1; then
  flatpak update -y || true
  runuser -u "$REAL_USER" -- env HOME="$REAL_HOME" flatpak update --user -y || true
  flatpak uninstall --unused -y || true
fi
printf '\n== Atualizando aplicativos Snap ==\n'
if ! command -v snap >/dev/null 2>&1; then
  dnf install -y snapd || printf 'Snapd não está disponível nos repositórios configurados; etapa ignorada.\n'
  ln -sf /var/lib/snapd/snap /snap || true
  systemctl enable --now snapd.socket || true
fi
command -v snap >/dev/null 2>&1 && snap refresh || true
  printf '\n== Preparando suporte AppImage ==\n'
dnf install -y fuse fuse-libs || printf 'Suporte FUSE não está disponível; AppImages podem não abrir.\n'
mkdir -p "$REAL_HOME/Applications" "$REAL_HOME/.local/bin"
chown -R "$REAL_UID:$REAL_UID" "$REAL_HOME/Applications" "$REAL_HOME/.local/bin" || true
find "$REAL_HOME/Applications" -type f -name '*.AppImage' -exec runuser -u "$REAL_USER" -- {} --appimage-update \\; || true
printf '\n== Manutenção concluída ==\n'
"""

KERNEL_CLEANUP = r'''set -e
running="$(uname -r)"
printf 'Kernel atualmente em uso: %s\n' "$running"
printf 'Procurando kernels antigos mantendo o atual e o anterior...\n'
old="$(dnf repoquery --installonly --latest-limit=-2 --qf '%{name}-%{evr}.%{arch}' 2>/dev/null | grep -v "$running" || true)"
if [ -z "$old" ]; then
  printf 'Nenhum kernel antigo seguro para remover.\n'
else
  printf 'Serão removidos apenas estes pacotes:\n%s\n' "$old"
  printf '%s\n' "$old" | xargs -r dnf remove -y
fi
'''

APPIMAGE_SETUP = r'''set -e
dnf install -y fuse fuse-libs || printf 'Suporte FUSE não está disponível; AppImages podem não abrir.\n'
REAL_UID="${PKEXEC_UID:-0}"
REAL_HOME="$(getent passwd "$REAL_UID" | cut -d: -f6)"
mkdir -p "$REAL_HOME/Applications" "$REAL_HOME/.local/bin" "$REAL_HOME/.local/share/applications"
chown -R "$REAL_UID:$REAL_UID" "$REAL_HOME/Applications" "$REAL_HOME/.local" || true
printf 'Pasta preparada: %s/Applications\n' "$REAL_HOME"
printf 'Coloque seus arquivos .AppImage nessa pasta e marque-os como executáveis para abrir pelo gerenciador de arquivos.\n'
'''

UNIVERSAL_UPDATE = r'''set -e
printf '== Flatpak ==\n'
flatpak update -y || true
printf '== Snap ==\n'
if command -v snap >/dev/null 2>&1; then snap refresh; else printf 'Snapd não está instalado; use a ação de suporte Snap.\n'; fi
printf '== AppImage ==\n'
REAL_UID="${PKEXEC_UID:-0}"
REAL_USER="$(getent passwd "$REAL_UID" | cut -d: -f1)"
REAL_HOME="$(getent passwd "$REAL_UID" | cut -d: -f6)"
find "$REAL_HOME/Applications" -type f -name '*.AppImage' -exec runuser -u "$REAL_USER" -- {} --appimage-update \; || true
'''

CATEGORIES = {
    "software": ("Software e atualizações", "package-x-generic-symbolic", [
        ("Atualizar repositórios", "view-refresh-symbolic", "Sincroniza os metadados dos repositórios DNF5.", "dnf makecache --refresh", True),
        ("Atualizar o sistema", "system-software-update-symbolic", "Instala as atualizações disponíveis.", "dnf upgrade --refresh -y", True),
        ("Atualizar Flatpak, Snap e AppImage", "view-refresh-symbolic", "Atualiza aplicativos dos três formatos suportados.", UNIVERSAL_UPDATE, True),
        ("Abrir GNOME Software", "application-x-executable-symbolic", "Navegue e instale aplicativos visualmente.", "gnome-software", False),
        ("Habilitar Flathub", "application-x-addon-symbolic", "Adiciona o repositório Flathub para aplicativos Flatpak.", "flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo", True),
    ]),
    "hardware": ("Hardware e drivers", "computer-symbolic", [
        ("Detectar placa gráfica", "video-display-symbolic", "Mostra a GPU encontrada neste computador.", "lspci | grep -Ei 'vga|3d|display' || true", False),
        ("Instalar driver NVIDIA", "video-display-symbolic", "Instala akmod-nvidia e CUDA, quando disponíveis.", "dnf install -y akmod-nvidia xorg-x11-drv-nvidia-cuda", True),
        ("Instalar suporte AMD", "video-display-symbolic", "Instala os drivers Mesa oficiais para aceleração AMD.", "true", True),
        ("Instalar suporte Intel", "video-display-symbolic", "Instala o driver de mídia Intel.", "dnf install -y intel-media-driver", True),
        ("Abrir Discos", "drive-harddisk-symbolic", "Gerencie discos e partições pelo GNOME Disks.", "gnome-disks", False),
        ("Abrir GParted", "drive-harddisk-symbolic", "Editor avançado de partições.", "gparted", False),
    ]),
    "network": ("Rede, Samba e firewall", "network-wired-symbolic", [
        ("Configurações de rede", "network-wired-symbolic", "Abre a configuração visual de rede do GNOME.", "gnome-control-center network", False),
        ("Ativar firewall", "security-high-symbolic", "Ativa o firewalld sem abrir automaticamente portas de compartilhamento ou impressão.", "true", True),
        ("Mostrar status do firewall", "security-high-symbolic", "Exibe as zonas e serviços ativos.", "firewall-cmd --state; firewall-cmd --list-all", True),
    ]),
    "peripherals": ("Impressoras e periféricos", "printer-symbolic", [
        ("Abrir impressoras", "printer-symbolic", "Abre o configurador gráfico de impressoras do Fedora.", "system-config-printer", False),
        ("Ver impressoras instaladas", "printer-symbolic", "Mostra impressoras configuradas e a impressora padrão.", "lpstat -p -d", False),
        ("Instalar suporte HP", "printer-symbolic", "Repara HPLIP e os drivers Fedora de impressão que já acompanham a Central.", "true", True),
        ("Instalar plug-in proprietário HP (uma vez)", "printer-symbolic", "Use se o HP Device Manager disser que o modelo exige o plug-in. A instalação global evita repetir a solicitação em cada fila.", "true", True),
        ("Instalar suporte a scanner", "scanner-symbolic", "Instala SANE, Simple Scan e AirScan. O suporte IPP-over-USB fica separado para evitar conflito com alguns drivers USB de impressora.", "true", True),
        ("Instalar suporte IPP-over-USB", "printer-symbolic", "Opcional: para modelos USB que suportam IPP-over-USB. Pode ocupar a conexão USB e conflitar com HPLIP/Gutenprint; use somente se o modelo exigir.", "true", True),
        ("Abrir Simple Scan", "scanner-symbolic", "Digitalize documentos sem configuração complicada.", "simple-scan", False),
        ("Detectar scanners", "scanner-symbolic", "Procura scanners USB e de rede compatíveis.", "scanimage -L", False),
        ("Abrir Bluetooth", "bluetooth-symbolic", "Abre a tela de dispositivos Bluetooth.", "gnome-control-center bluetooth", False),
        ("Reiniciar Bluetooth", "bluetooth-symbolic", "Reinicia o serviço Bluetooth.", "systemctl restart bluetooth", True),
        ("Abrir controle de áudio", "audio-volume-high-symbolic", "Abre o mixer PipeWire/PulseAudio.", "pavucontrol", False),
    ]),
    "appearance": ("Aparência e extensões", "applications-graphics-symbolic", [
        ("Abrir GNOME Tweaks", "applications-system-symbolic", "Ajuste fontes, janelas e comportamento do GNOME.", "gnome-tweaks", False),
        ("Abrir Extension Manager", "application-x-addon-symbolic", "Gerencie extensões GNOME pelo aplicativo visual.", "flatpak run com.mattjakeman.ExtensionManager", False),
        ("Instalar fontes Microsoft Core", "font-x-generic-symbolic", "Baixa o RPM externo, confere o SHA-256 e extrai os TTF com rpm2cpio/cpio sem instalar o RPM nem executar scriptlets. Fontes sujeitas à licença Microsoft.", "true", True),
        ("Instalar Orchis (GTK/Shell)", "applications-graphics-symbolic", "Instala Orchis Dark do projeto upstream em /usr/share/themes.", "true", True),
        ("Instalar Colloid (GTK/Shell)", "applications-graphics-symbolic", "Instala Colloid Dark do projeto upstream em /usr/share/themes.", "true", True),
        ("Instalar Graphite (GTK/Shell)", "applications-graphics-symbolic", "Instala Graphite Dark do projeto upstream em /usr/share/themes.", "true", True),
        ("Instalar WhiteSur (GTK/Shell)", "applications-graphics-symbolic", "Instala WhiteSur Dark do projeto upstream em /usr/share/themes.", "true", True),
        ("Instalar tema Yaru e ícones", "applications-graphics-symbolic", "Mantém o tema GTK/Shell e os ícones Yaru pelo pacote yaru-theme do Fedora.", "true", True),
        ("Instalar ícones Papirus", "applications-graphics-symbolic", "Instala Papirus pelo pacote dos repositórios Fedora.", "true", True),
        ("Instalar ícones Tela", "applications-graphics-symbolic", "Instala as variantes de ícones Tela do projeto upstream.", "true", True),
        ("Instalar ícones Colloid", "applications-graphics-symbolic", "Instala as variantes de ícones Colloid do projeto upstream.", "true", True),
        ("Instalar ícones Kora", "applications-graphics-symbolic", "Instala Kora e Kora Grey do projeto upstream.", "true", True),
        ("Instalar Wine e Winetricks", "wine-symbolic", "Instala suporte para executar aplicativos Windows.", "dnf install -y wine winetricks", True),
        ("Preparar suporte AppImage", "application-x-executable-symbolic", "Instala o suporte FUSE, cria Applications e adiciona o AppImagePool, uma loja com catálogo e busca de AppImages.", APPIMAGE_SETUP, True),
        ("Instalar extensões recomendadas", "application-x-addon-symbolic", "Instala extensões disponíveis nos repositórios Fedora.", "dnf install -y gnome-shell-extension-dash-to-dock gnome-shell-extension-appindicator gnome-shell-extension-user-theme", True),
    ]),
    "system": ("Sistema e serviços", "preferences-system-symbolic", [
        ("Crie seu Sistema", "media-optical-symbolic", "Abre a interface original para configurar e criar uma remasterização do Fedorento.", "true", False),
        ("Usuários e grupos", "system-users-symbolic", "Abre as configurações de contas do sistema.", "gnome-control-center user-accounts", False),
        ("Data e hora", "preferences-system-time-symbolic", "Ajuste data, fuso e sincronização automática.", "gnome-control-center datetime", False),
        ("Atualizar firmware", "hardware-symbolic", "Procura firmware novo com o fwupd.", "fwupdmgr refresh --force; fwupdmgr get-updates", True),
        ("Ativar atualizações automáticas", "system-software-update-symbolic", "Ativa o temporizador de atualizações do DNF5.", "true", True),
        ("Limpar o sistema", "edit-clear-all-symbolic", "Remove órfãos, caches DNF e Flatpaks não usados.", "dnf autoremove -y; dnf clean all; flatpak uninstall --unused -y || true", True),
    ]),
}

ACTION_DEPENDENCIES = {
    "Rede e firewall": ["firewalld"],
    "Firmware": ["fwupd"],
    "Habilitar Flathub": ["flatpak"],
    "Abrir GNOME Software": ["gnome-software"],
    "Detectar placa gráfica": ["pciutils"],
    "Abrir Discos": ["gnome-disk-utility"],
    "Abrir GParted": ["gparted"],
    "Configurações de rede": ["gnome-control-center"],
    "Ativar firewall": ["firewalld"],
    "Mostrar status do firewall": ["firewalld"],
    "Abrir impressoras": ["system-config-printer"],
    "Ver impressoras instaladas": ["cups-client"],
    "Instalar suporte a scanner": ["sane-backends", "simple-scan", "sane-airscan"],
    "Abrir Simple Scan": ["simple-scan"],
    "Detectar scanners": ["sane-backends"],
    "Abrir Bluetooth": ["gnome-control-center", "bluez"],
    "Reiniciar Bluetooth": ["bluez"],
    "Abrir controle de áudio": ["pavucontrol"],
    "Abrir GNOME Tweaks": ["gnome-tweaks"],
    "Abrir Extension Manager": ["flatpak"],
    "Usuários e grupos": ["gnome-control-center"],
    "Data e hora": ["gnome-control-center"],
    "Atualizar firmware": ["fwupd"],
    "Ativar atualizações automáticas": ["dnf5-plugin-automatic"],
    "Instalar Wine e Winetricks": ["wine", "winetricks"],
}

OPTIONAL_TOOL_HELPERS = {
    "Abrir GNOME Software": "gnome-software",
    "Detectar placa gráfica": "pciutils",
    "Abrir Discos": "disks",
    "Abrir GParted": "gparted",
    "Configurações de rede": "control-center",
    "Usuários e grupos": "control-center",
    "Data e hora": "control-center",
    "Abrir impressoras": "printer-config",
    "Ver impressoras instaladas": "printer-status",
    "Abrir Bluetooth": "control-center-bluetooth",
    "Abrir controle de áudio": "pavucontrol",
    "Abrir GNOME Tweaks": "tweaks",
    "Abrir Simple Scan": "simple-scan",
    "Detectar scanners": "scanner-tools",
    "Abrir Extension Manager": "extension-manager",
}

PRIVILEGED_ACTIONS = {
    "Atualizar repositórios": "repo-refresh",
    "Atualizar o sistema": "system-update",
    "Atualização completa": "full-update",
    "Atualizar Flatpak, Snap e AppImage": "universal-update",
    "Habilitar Flathub": "flatpak",
    "Instalar driver NVIDIA": "nvidia",
    "Instalar suporte AMD": "amd",
    "Instalar suporte Intel": "intel",
    "Limpar kernels não usados": "kernel-cleanup",
    "Ativar firewall": "firewall",
    "Mostrar status do firewall": "firewall-status",
    "Rede e firewall": "firewall-status",
    "Instalar suporte HP": "printer-drivers",
    "Instalar plug-in proprietário HP (uma vez)": "hplip-plugin",
    "Instalar suporte a scanner": "scanner",
    "Instalar suporte IPP-over-USB": "ipp-usb",
    "Reiniciar Bluetooth": "bluetooth",
    "Instalar fontes Microsoft Core": "fonts",
    "Instalar Wine e Winetricks": "wine",
    "Preparar suporte AppImage": "appimage",
    "Instalar Orchis (GTK/Shell)": "theme-orchis",
    "Instalar Colloid (GTK/Shell)": "theme-colloid-gtk",
    "Instalar Graphite (GTK/Shell)": "theme-graphite",
    "Instalar WhiteSur (GTK/Shell)": "theme-whitesur",
    "Instalar tema Yaru e ícones": "theme-yaru",
    "Instalar ícones Papirus": "theme-papirus",
    "Instalar ícones Tela": "theme-tela-icons",
    "Instalar ícones Colloid": "theme-colloid-icons",
    "Instalar ícones Kora": "theme-kora-icons",
    "Instalar extensões recomendadas": "extensions",
    "Atualizar firmware": "firmware",
    "Firmware": "firmware",
    "Ativar atualizações automáticas": "dnf-automatic",
    "Limpar o sistema": "cleanup",
}


def label(text, style=None, wrap=False):
    widget = Gtk.Label(label=text)
    widget.set_xalign(0)
    widget.set_wrap(wrap)
    if style:
        widget.add_css_class(style)
    return widget


def icon(name, size=32):
    image = Gtk.Image.new_from_icon_name(name)
    image.set_pixel_size(size)
    return image


def command_exists(command):
    first = command.strip().split()[0] if command.strip() else ""
    return shutil.which(first) is not None or first in {"dnf", "systemctl", "firewall-cmd", "flatpak", "rpm", "lspci"}


def is_shell_script(command):
    return any(marker in command for marker in ("\n", ";", "&&", "||", "if ", "set -e"))


class CentralFedorento(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.connect("activate", self.on_activate)
        self.window = None
        self.content = None
        self.rows = {}
        self.quick_rules_status = None

    def on_activate(self, _app):
        if self.window:
            self.window.present()
            return
        self.window = Adw.ApplicationWindow(application=self)
        self.window.set_title("Central Fedorento")
        self.window.set_default_size(1180, 760)
        self.install_css()
        self.build_ui()
        self.window.present()

    def install_css(self):
        css = Gtk.CssProvider()
        css.load_from_data(b"""
        .hero { background: linear-gradient(135deg, #2463a5, #3f8fc7); color: white; border-radius: 18px; padding: 24px; }
        .hero-title { font-size: 26px; font-weight: 700; color: white; }
        .hero-subtitle { color: rgba(255,255,255,.88); }
        .panel-title { font-size: 22px; font-weight: 700; }
        .action-card { background: alpha(@card_bg_color, .88); border: 1px solid alpha(@borders, .55); border-radius: 14px; padding: 14px; }
        .action-card:hover { background: @card_bg_color; border-color: @accent_color; }
        .action-title { font-weight: 700; }
        .terminal { background: #101218; color: #e8edf5; font-family: monospace; padding: 12px; }
        .status-ok { color: #2ec27e; }
        """)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header = Adw.HeaderBar()
        header.set_title_widget(label("Central Fedorento", "heading"))
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", lambda *_: self.show_about())
        self.add_action(about_action)
        menu = Gio.Menu()
        menu.append("Sobre / ajuda", "app.about")
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        menu_button.set_tooltip_text("Sobre a Central, ajuda e informações de versão.")
        header.pack_end(menu_button)
        root.append(header)

        split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        split.set_position(280)
        sidebar = Gtk.ListBox()
        sidebar.add_css_class("navigation-sidebar")
        sidebar.set_selection_mode(Gtk.SelectionMode.SINGLE)
        items = [("home", "Início", "go-home-symbolic")] + [(key, data[0], data[1]) for key, data in CATEGORIES.items()]
        for key, title, icon_name in items:
            row = Gtk.ListBoxRow()
            row.set_name(key)
            box = Gtk.Box(spacing=12)
            box.set_margin_top(11); box.set_margin_bottom(11); box.set_margin_start(14); box.set_margin_end(14)
            box.append(icon(icon_name, 22)); box.append(label(title))
            row.set_child(box); sidebar.append(row); self.rows[key] = row
        sidebar.connect("row-selected", self.on_row_selected)
        split.set_start_child(sidebar)

        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.content.set_margin_top(28); self.content.set_margin_bottom(28); self.content.set_margin_start(32); self.content.set_margin_end(32)
        scroll.set_child(self.content); split.set_end_child(scroll)
        root.append(split)
        self.window.set_content(root)
        sidebar.select_row(self.rows["home"])

    def clear_content(self):
        child = self.content.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.content.remove(child)
            child = next_child

    def on_row_selected(self, _list, row):
        if not row:
            return
        key = row.get_name()
        self.clear_content()
        if key == "home":
            self.render_home()
        else:
            title, icon_name, actions = CATEGORIES[key]
            self.render_category(key, title, icon_name, actions)

    def render_home(self):
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hero.add_css_class("hero")
        hero.append(label("Central Fedorento", "hero-title"))
        hero.append(label("A Central Fedorento é um painel visual para manter o sistema, configurar serviços e periféricos, preparar o Fedora e criar remasterizações. Escolha uma ação principal ou uma categoria à esquerda. Ao passar o ponteiro sobre os botões, veja a explicação; operações administrativas pedem confirmação.", "hero-subtitle", True))
        self.content.append(hero)

        self.content.append(label("Ações principais", "panel-title"))
        grid = Gtk.Grid(column_spacing=14, row_spacing=14)
        cards = [
            ("Atualização completa", "system-software-update-symbolic", "Atualiza repositórios e aplicativos, remove dependências órfãs e limpa caches.", FULL_UPDATE, True, "Atualizar agora", None),
            ("Limpar kernels não usados", "software-update-urgent-symbolic", "Remove somente kernels antigos elegíveis e preserva o kernel atual e o anterior.", KERNEL_CLEANUP, True, "Limpar kernels", None),
            ("Crie seu Sistema", "media-optical-symbolic", "Abre o criador de remasterização; a instalação necessária é oferecida sob demanda.", "true", False, "Abrir criador", self.start_crie_seu_sistema),
            ("Instalador Dinâmico", "system-software-install-symbolic", "Instale tudo que você precisa em um clique. Verifica o sistema e executa o pós-instalação, instalando o que faltar e ajustando configurações.", "true", False, "Iniciar instalador", self.start_dynamic_installer),
        ]
        for index, (title, icon_name, desc, command, privileged, button_label, callback) in enumerate(cards):
            card = self.action_card(title, icon_name, desc, command, privileged, button_label, callback)
            grid.attach(card, index % 2, index // 2, 1, 1)
        self.content.append(grid)
        self.content.append(label("Para outras configurações, selecione uma categoria no menu à esquerda.", "dim-label", True))

    def start_dynamic_installer(self):
        script = "/usr/share/central-fedorento/fedora_pos_install.sh"
        if not os.path.isfile(script):
            self.show_message("Instalador Dinâmico ausente", "O script de pós-instalação não foi encontrado no pacote da Central.")
            return
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Autorizar o Instalador Dinâmico?",
            body=("O script verifica o Fedora e as configurações, atualiza o sistema e instala/configura componentes que podem faltar. "
                  "Ele pode adicionar RPM Fusion, trocar pacotes multimídia, instalar temas baixados do GitHub com privilégios administrativos, "
                  "instalar fontes e drivers, ativar serviços e remover dependências órfãs. Será aberto um terminal para a senha sudo e as confirmações específicas. "
                  "A configuração Samba só será ativada se você confirmar no próprio script; ela compartilha ~/Público com leitura e gravação sem senha na rede. "
                  "Use apenas uma rede doméstica confiável. Confirme somente se concordar com essas alterações.")
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("deny", "Negar")
        dialog.add_response("run", "Confirmar e executar")
        dialog.set_response_appearance("run", Adw.ResponseAppearance.SUGGESTED)

        def response(d, choice):
            d.close()
            if choice == "run":
                self.launch_dynamic_installer(script)

        dialog.connect("response", response)
        dialog.present()

    def launch_dynamic_installer(self, script):
        shell_command = (
            f"bash {self.quote(script)}; result=$?; printf '\\n'; "
            "read -r -p 'Instalador concluído. Pressione Enter para fechar este terminal...' _; exit \"$result\""
        )
        terminals = (
            ("ptyxis", ["--", "bash", "-lc", shell_command]),
            ("kgx", ["--", "bash", "-lc", shell_command]),
            ("gnome-terminal", ["--", "bash", "-lc", shell_command]),
            ("konsole", ["-e", "bash", "-lc", shell_command]),
            ("x-terminal-emulator", ["-e", "bash", "-lc", shell_command]),
            ("xterm", ["-e", "bash", "-lc", shell_command]),
        )
        errors = []
        for name, arguments in terminals:
            executable = shutil.which(name)
            if not executable:
                continue
            try:
                subprocess.Popen([executable, *arguments], start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError as exc:
                errors.append(f"{name}: {exc}")
        detail = "\n".join(errors)
        body = "Não encontrei um terminal compatível (Ptyxis, GNOME Console/Terminal, Konsole ou XTerm). Instale/abra um terminal e execute: bash /usr/share/central-fedorento/fedora_pos_install.sh"
        if detail:
            body += "\n\n" + detail
        self.show_message("Não foi possível abrir o instalador", body)

    def start_crie_seu_sistema(self):
        app = "/usr/bin/crie-seu-sistema"
        if os.path.isfile(app) and os.access(app, os.X_OK) and shutil.which("eggs"):
            self.launch_crie_seu_sistema()
            return
        try:
            fedora_version = subprocess.run(["rpm", "-E", "%fedora"], capture_output=True, text=True, timeout=5, check=False).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            fedora_version = ""
        if platform.machine() != "x86_64" or fedora_version != "44":
            self.show_message("Pacote não compatível", "Os RPMs fornecidos foram preparados para Fedora 44 x86_64. A Central não instalará esses pacotes nesta versão ou arquitetura.")
            return
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Preparar Crie seu Sistema",
            body="A Central instalará os dois RPMs fornecidos e as dependências pelos repositórios DNF; os arquivos só serão instalados após sua confirmação. Os RPMs não têm assinatura digital. A Central confere SHA-256 fixados para detectar alterações, mas isso não autentica o publicador. A caixa administrativa avançada vem desmarcada; se marcada, o helper original grava regras amplas NOPASSWD: ALL e polkit na máquina atual e não as remove ao terminar; elas também podem entrar na ISO. Mantenha-a desmarcada salvo se realmente quiser esse efeito. Ao criar a imagem, a interface pode substituir /etc/penguins-eggs.d/custom.yaml. O atalho próprio será ocultado e a interface abrirá por este botão.",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("install", "Instalar e abrir")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        def response(d, answer):
            d.close()
            if answer == "install":
                self.run_action(
                    "Instalar Crie seu Sistema",
                    "true",
                    True,
                    named_helper="remaster-tools",
                    on_complete=lambda ok: self.launch_crie_seu_sistema() if ok else None,
                )
        dialog.connect("response", response)
        dialog.present()

    def launch_crie_seu_sistema(self):
        app = "/usr/bin/crie-seu-sistema"
        if not (os.path.isfile(app) and os.access(app, os.X_OK) and shutil.which("eggs")):
            self.show_message("Crie seu Sistema não está pronto", "A instalação não deixou o aplicativo e o motor penguins-eggs disponíveis. Consulte a saída da instalação e tente novamente.")
            return
        if not self.hide_crie_seu_sistema_menu_entry():
            self.show_message("Atalho do menu", "A interface será aberta, mas a Central não conseguiu ocultar o atalho do menu para esta conta.")
        try:
            subprocess.Popen([app], start_new_session=True)
        except OSError as exc:
            self.show_message("Não foi possível abrir Crie seu Sistema", str(exc))

    @staticmethod
    def hide_crie_seu_sistema_menu_entry():
        system_entry = "/usr/share/applications/crie-seu-sistema.desktop"
        if not os.path.isfile(system_entry):
            return True
        user_apps = os.path.join(GLib.get_user_data_dir(), "applications")
        user_entry = os.path.join(user_apps, "crie-seu-sistema.desktop")
        source_entry = user_entry if os.path.isfile(user_entry) else system_entry
        temporary = None
        try:
            with open(source_entry, "r", encoding="utf-8") as source:
                lines = source.readlines()
            updated = []
            in_desktop_entry = False
            display_value_written = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("[") and stripped.endswith("]"):
                    if in_desktop_entry and not display_value_written:
                        updated.append("NoDisplay=true\n")
                        display_value_written = True
                    in_desktop_entry = stripped == "[Desktop Entry]"
                if in_desktop_entry and stripped.startswith("NoDisplay="):
                    if not display_value_written:
                        updated.append("NoDisplay=true\n")
                        display_value_written = True
                    continue
                updated.append(line)
            if in_desktop_entry and not display_value_written:
                updated.append("NoDisplay=true\n")
            os.makedirs(user_apps, mode=0o755, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".crie-seu-sistema-", dir=user_apps, text=True)
            with os.fdopen(fd, "w", encoding="utf-8") as target:
                target.writelines(updated)
            os.chmod(temporary, 0o644)
            os.replace(temporary, user_entry)
            temporary = None
            if shutil.which("update-desktop-database"):
                subprocess.run(["update-desktop-database", user_apps], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            return True
        except OSError:
            if temporary:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
            return False

    @staticmethod
    def unit_is_enabled_or_active(unit):
        for mode in ("is-active", "is-enabled"):
            try:
                result = subprocess.run(["systemctl", mode, unit], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                if result.returncode == 0:
                    return True
            except OSError:
                return False
        return False

    def feature_is_enabled(self, feature):
        if feature == "cups":
            return any(self.unit_is_enabled_or_active(unit) for unit in ("cups.socket", "cups.path", "cups.service"))
        if feature == "samba":
            central_config = "/etc/samba/smb.conf.d/central-fedorento-publico-users.conf"
            legacy_configs = (
                "/etc/samba/smb.conf.d/central-fedorento-publico.conf",
                "/etc/samba/smb.conf.d/central-fedorento-guest.conf",
                "/etc/samba/smb.conf.d/fedorento-publico-users.conf",
                "/etc/samba/smb.conf.d/fedorento-publico.conf",
            )
            if os.path.isfile(central_config):
                return True
            return any(os.path.isfile(path) for path in legacy_configs)
        if feature == "printer-admin":
            path = "/etc/polkit-1/rules.d/50-central-fedorento-printer-admin.rules"
            try:
                with open(path, "r", encoding="utf-8") as policy:
                    return policy.readline().strip() == "// Managed by Central Fedorento: local printer administration v1"
            except OSError:
                return False
        return False

    def render_rule_toggle(self, feature):
        if feature == "cups":
            title = "Impressão cotidiana (CUPS)"
            description = "Ativa ou desativa o serviço de impressão. Enviar trabalhos continua disponível para usuários comuns; a administração das filas é controlada separadamente abaixo."
        elif feature == "samba":
            title = "Compartilhamento Público por usuário (Samba)"
            description = "Ativa ou desativa compartilhamentos sem senha para cada ~/Público, inclusive de novas contas locais. Somente essa pasta é compartilhada; o nome de rede Publico-usuário é mantido. Use uma rede doméstica confiável."
        else:
            title = "Configurar impressoras sem senha (polkit)"
            description = "Permite a qualquer usuário com sessão local ativa adicionar, editar, remover, ativar e escolher impressoras CUPS sem senha. Não libera sessões remotas, instalação de RPMs nem administração do servidor CUPS."
        enabled = self.feature_is_enabled(feature)
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        panel.add_css_class("action-card")
        check = Gtk.CheckButton(label=title)
        check.set_active(enabled)
        check.set_tooltip_text(description)
        panel.append(check)
        panel.append(label(description, "dim-label", True))
        state = {"enabled": enabled, "busy": False}
        check.connect("toggled", lambda widget: self.on_rule_toggle(widget, feature, state))
        self.content.append(panel)

    def on_rule_toggle(self, check, feature, state):
        if state["busy"]:
            return
        target = check.get_active()
        if target == state["enabled"]:
            return
        is_samba = feature == "samba"
        is_printer_admin = feature == "printer-admin"
        if is_printer_admin and target:
            body = "Qualquer usuário com sessão local ativa poderá adicionar, alterar, remover, ativar e escolher filas de impressão sem senha. A regra não permite administrar remotamente o servidor CUPS nem instalar pacotes de terceiros."
        elif is_printer_admin:
            body = "A regra da Central será removida e as operações administrativas das filas voltarão a usar a autenticação padrão do Fedora. A impressão cotidiana continuará disponível."
        elif is_samba and target:
            body = "Cada conta pessoal em /home terá sua própria pasta ~/Público, acessível sem senha para leitura e gravação na zona de rede ativa. O compartilhamento conserva o nome de rede Publico-usuário. Isso não compartilha o restante da pasta pessoal. Use somente uma rede confiável."
        elif is_samba:
            body = "A Central removerá seus compartilhamentos da pasta Público e o monitor de novas contas. Os arquivos e as pastas serão preservados; outros compartilhamentos Samba fora da Central não serão removidos."
        elif target:
            body = "A Central instalará/ativará CUPS. Usuários comuns poderão enviar trabalhos de impressão sem sudo; a configuração administrativa continua protegida pelo polkit oficial do desktop."
        else:
            body = "A Central desativará os serviços de impressão CUPS. Nenhuma regra ampla do polkit será criada ou removida."
        heading = "Administração de impressoras" if is_printer_admin else ("Compartilhamento Samba" if is_samba else "Impressão CUPS")
        dialog = Adw.MessageDialog(transient_for=self.window, heading=heading, body=body)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("apply", "Ativar" if target else "Desativar")
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        state["busy"] = True
        check.set_sensitive(False)
        def response(d, choice):
            d.close()
            if choice != "apply":
                check.set_active(state["enabled"])
                check.set_sensitive(True)
                state["busy"] = False
                return
            if is_printer_admin:
                helper = "printer-policy-enable" if target else "printer-policy-disable"
                title = "Permitir administração local das impressoras" if target else "Restaurar proteção administrativa das impressoras"
            elif is_samba:
                helper = "samba-enable" if target else "samba-disable"
                title = "Ativar compartilhamento Samba" if target else "Desativar compartilhamento Samba"
            else:
                helper = "cups-enable" if target else "cups-disable"
                title = "Ativar impressão CUPS" if target else "Desativar impressão CUPS"
            def completed(ok):
                if ok:
                    state["enabled"] = target
                else:
                    check.set_active(state["enabled"])
                check.set_sensitive(True)
                state["busy"] = False
            self.run_action(title, "true", True, helper, [], on_complete=completed)
        dialog.connect("response", response)
        dialog.present()

    def action_card(self, title, icon_name, description, command, privileged, button_label=None, on_clicked=None):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("action-card")
        card.set_hexpand(True); card.set_size_request(210, 190)
        top = Gtk.Box(spacing=12); top.append(icon(icon_name, 34)); top.append(label(title, "action-title"))
        card.append(top); card.append(label(description, "dim-label", True))
        button = Gtk.Button(label=button_label or ("Executar" if privileged else "Abrir"))
        button.set_halign(Gtk.Align.START); button.add_css_class("suggested-action")
        button.set_tooltip_text(f"{title}. {description}")
        if on_clicked:
            button.connect("clicked", lambda _b: on_clicked())
        else:
            button.connect("clicked", lambda _b: self.confirm_action(title, command, privileged))
        card.append(button)
        return card

    def render_category(self, key, title, icon_name, actions):
        heading = Gtk.Box(spacing=14)
        heading.append(icon(icon_name, 42))
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info.append(label(title, "panel-title"))
        info.append(label("Clique em uma ação para abrir uma janela com explicação, comandos e saída em tempo real.", "dim-label", True))
        heading.append(info); self.content.append(heading)
        if key == "network":
            self.render_rule_toggle("samba")
        elif key == "peripherals":
            self.render_rule_toggle("cups")
            self.render_rule_toggle("printer-admin")
        grid = Gtk.Grid(column_spacing=14, row_spacing=14)
        for index, (name, action_icon, description, command, privileged) in enumerate(actions):
            if name == "Crie seu Sistema":
                card = self.action_card(name, action_icon, description, command, privileged, "Abrir criador", self.start_crie_seu_sistema)
            else:
                card = self.action_card(name, action_icon, description, command, privileged)
            grid.attach(card, index % 2, index // 2, 1, 1)
        self.content.append(grid)

    def confirm_action(self, name, command, privileged):
        body = "A ação abrirá um terminal integrado e exibirá o resultado em tempo real."
        if "plug-in proprietário hp" in name.lower():
            body += " O instalador oficial HP será aberto como administrador para instalação global do plug-in HPLIP. A HP exige que você leia e aceite a licença do componente proprietário. Essa autorização única substitui o pedido de senha repetido do HP Device Manager para esse plug-in; não remove a proteção administrativa geral do sistema."
        if "ipp-over-usb" in name.lower():
            body += " O Fedora documenta que ipp-usb pode ocupar a porta USB e impedir que HPLIP, Gutenprint ou outro driver clássico use o mesmo dispositivo. Use apenas se o modelo suportar impressão driverless por IPP-over-USB; se necessário, desinstale a fila antiga antes de ativá-lo."
        if "instalar " in name.lower() and ("gtk/shell" in name.lower() or "ícones" in name.lower()):
            body += " A instalação altera arquivos de tema do sistema; para temas obtidos do GitHub, o helper baixa o repositório upstream selecionado e executa seu instalador com privilégios administrativos. Use apenas se confiar na origem."
        if "kernel" in name.lower():
            body += " O kernel em uso será preservado e apenas versões antigas elegíveis serão consideradas."
        if "convidado" in name.lower():
            body += " Este modo libera uma pasta limitada sem senha para dispositivos da rede local. Use somente em uma rede doméstica confiável."
        elif "compartilhamento protegido" in name.lower():
            body += " Este modo limita o acesso aos usuários locais autorizados e preserva os arquivos após reinicializações."
        elif "samba" in name.lower():
            body += " O compartilhamento será configurado somente para usuários locais autorizados."
        if privileged:
            body += " O Fedorento poderá solicitar sua senha pelo polkit."
        dialog = Adw.MessageDialog(transient_for=self.window, heading=name, body=body)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("run", "Abrir terminal e executar")
        dialog.set_response_appearance("run", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", lambda d, response: (d.close(), self.run_action(name, command, privileged)) if response == "run" else d.close())
        dialog.present()

    def run_action(self, name, command, privileged, named_helper=None, helper_arguments=None, on_complete=None):
        dependencies = ACTION_DEPENDENCIES.get(name, [])
        tool_helper = OPTIONAL_TOOL_HELPERS.get(name)
        needs_tool_install = bool(tool_helper and (name == "Abrir Extension Manager" or not command_exists(command)))
        if not command_exists(command) and not dependencies and not is_shell_script(command) and not tool_helper:
            self.show_message("Componente não encontrado", "O programa necessário não está instalado. Você pode instalar o pacote pela categoria Software e atualizações.")
            return
        helper_id = named_helper or (PRIVILEGED_ACTIONS.get(name) if privileged else None)
        if helper_id:
            script = f"pkexec /usr/libexec/central-fedorento-helper {helper_id}"
        elif needs_tool_install:
            script = f"pkexec /usr/libexec/central-fedorento-helper {tool_helper} && exec {command}"
        else:
            script = self.build_script(name, command, privileged)
        terminal = Adw.Window(transient_for=self.window, modal=False)
        terminal.set_title(name)
        terminal.set_default_size(900, 560)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_margin_top(14); outer.set_margin_bottom(14); outer.set_margin_start(14); outer.set_margin_end(14)
        bar = Gtk.Box(spacing=10)
        bar.append(icon("utilities-terminal-symbolic", 28)); bar.append(label(name, "panel-title"))
        spinner = Gtk.Spinner(); spinner.start(); bar.append(spinner)
        outer.append(bar)
        view = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        view.add_css_class("terminal")
        view.set_vexpand(True)
        buffer = view.get_buffer()
        buffer.set_text("Preparando a ação:\n$ " + script + "\n\n")
        scroll = Gtk.ScrolledWindow(vexpand=True); scroll.set_child(view); outer.append(scroll)
        status = label("Executando...", "dim-label")
        outer.append(status)
        close = Gtk.Button(label="Fechar")
        close.set_tooltip_text("Fecha esta janela de saída; não interrompe uma ação em andamento.")
        close.set_sensitive(False); close.set_halign(Gtk.Align.END); outer.append(close)
        terminal.set_content(outer); terminal.present()

        try:
            if helper_id:
                argv = ["pkexec", "/usr/libexec/central-fedorento-helper", helper_id] + list(helper_arguments or [])
            elif needs_tool_install:
                argv = ["sh", "-c", script]
            elif not privileged:
                argv = ["sh", "-c", script]
            else:
                argv = ["pkexec", "sh", "-c", script]
            process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            os.set_blocking(process.stdout.fileno(), False)
        except Exception as exc:
            buffer.insert(buffer.get_end_iter(), "\nFalha ao iniciar: " + str(exc) + "\n")
            status.set_text("Falha ao iniciar")
            close.set_sensitive(True)
            if on_complete:
                on_complete(False)
            return

        def poll_output():
            try:
                while True:
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        break
                    buffer.insert(buffer.get_end_iter(), chunk.decode("utf-8", errors="replace"))
                    view.scroll_to_iter(buffer.get_end_iter(), 0.0, False, 0.0, 1.0)
            except BlockingIOError:
                pass
            except Exception:
                pass
            result = process.poll()
            if result is None:
                return True
            spinner.stop()
            status.set_text("Concluído com sucesso" if result == 0 else f"A operação terminou com código {result}")
            close.set_sensitive(True)
            close.connect("clicked", lambda *_: terminal.close())
            if on_complete:
                on_complete(result == 0)
            return False

        GLib.timeout_add(100, poll_output)

    @staticmethod
    def build_script(name, command, privileged):
        packages = ACTION_DEPENDENCIES.get(name, [])
        if not packages:
            return command
        package_list = " ".join(packages)
        installer = "dnf install -y " + package_list if privileged else "pkexec dnf install -y " + package_list
        check = "missing=''; for package in " + package_list + "; do rpm -q \"$package\" >/dev/null 2>&1 || missing=\"$missing $package\"; done; "
        return check + "if [ -n \"$missing\" ]; then printf '\\n== Dependências ausentes: %s ==\\n' \"$missing\"; " + installer + "; else printf '\\n== Dependências já instaladas ==\\n'; fi; " + command

    @staticmethod
    def quote(value):
        return "'" + value.replace("'", "'\\''") + "'"

    def show_message(self, heading, body):
        dialog = Adw.MessageDialog(transient_for=self.window, heading=heading, body=body)
        dialog.add_response("ok", "OK"); dialog.present()

    def show_about(self):
        about = Adw.AboutWindow(transient_for=self.window, application_name="Central Fedorento", application_icon="central-fedorento", version=VERSION, developer_name="Fabio Dias Silveira", comments="Central de configuração visual para o Fedorento com GNOME.\nContato: fabio140185@gmail.com", website="https://fedorentolinux.github.io/")
        about.present()


if __name__ == "__main__":
    CentralFedorento().run(None)
