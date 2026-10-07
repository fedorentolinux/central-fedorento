#!/usr/bin/env bash
#
# Pós-instalação do Fedora para uso doméstico (versão 4.5)
# Temas GTK/Shell: Orchis, Colloid, Graphite, WhiteSur e Yaru
# Ícones: Yaru, Papirus, Tela, Colloid e Kora
# AppImage: FUSE + AppImagePool (catálogo/loja via Flathub)
#
# Execute como usuário normal: bash fedora_pos_install.sh
# O script usa sudo somente nas operações administrativas.

set -Eeuo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
    echo "Não execute este script como root; execute como usuário normal com sudo disponível." >&2
    exit 1
fi

REAL_USER="${SUDO_USER:-${USER:-}}"
if [[ -z "$REAL_USER" ]]; then
    echo "Não foi possível determinar o usuário da sessão." >&2
    exit 1
fi
REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"
if [[ -z "$REAL_HOME" || ! -d "$REAL_HOME" ]]; then
    echo "Diretório pessoal inválido para $REAL_USER." >&2
    exit 1
fi
REAL_GROUP="$(id -gn "$REAL_USER")"

printf '%s\n' '------------------------------------------------------------------------------'
printf 'Instalador Dinâmico Fedora 4.5 para: %s\n' "$REAL_USER"
printf '%s\n' '------------------------------------------------------------------------------'
sudo -v

# 0. Análise dinâmica antes de instalar ou reconfigurar
printf '\n=== 0. Analisando sistema, pacotes e configurações existentes ===\n'
if [[ -r /etc/os-release ]]; then
    . /etc/os-release
else
    printf 'Erro: não foi possível identificar a distribuição pelo /etc/os-release.\n' >&2
    exit 1
fi
DISTRO_ID="${ID:-}"
DISTRO_LIKE="${ID_LIKE:-}"
case " ${DISTRO_ID,,} ${DISTRO_LIKE,,} " in
    *fedora*) printf 'Sistema detectado: %s (%s), Fedora %s, arquitetura %s.\n' "${NAME:-Fedora}" "${ID:-fedora}" "$(rpm -E %fedora)" "$(uname -m)" ;;
    *) printf 'Erro: este instalador é destinado ao Fedora ou derivado. Sistema encontrado: %s.\n' "${NAME:-desconhecido}" >&2; exit 1 ;;
esac
CHECK_PACKAGES=(dnf5 xdg-user-dirs curl cabextract xorg-x11-font-utils fontconfig gnome-tweaks samba samba-client cups cups-client cups-pk-helper system-config-printer hplip hplip-gui flatpak snapd fuse fuse-libs firewalld acl)
printf 'Pacotes existentes e ausentes (as etapas DNF seguintes tentam instalar os ausentes):\n'
for package in "${CHECK_PACKAGES[@]}"; do
    if rpm -q "$package" >/dev/null 2>&1; then
        printf '  [OK] %s\n' "$package"
    else
        printf '  [FALTA] %s\n' "$package"
    fi
done
printf 'Configurações atuais:\n'
if grep -Eq '^[[:space:]]*max_parallel_downloads[[:space:]]*=' /etc/dnf/dnf.conf 2>/dev/null; then
    printf '  [OK] max_parallel_downloads já está definido no DNF.\n'
else
    printf '  [FALTA] max_parallel_downloads; a etapa DNF irá defini-lo.\n'
fi
for unit in cups.socket cups.service smb.service nmb.service; do
    if systemctl is-enabled --quiet "$unit" 2>/dev/null || systemctl is-active --quiet "$unit" 2>/dev/null; then
        printf '  [ATIVO/CONFIGURADO] %s\n' "$unit"
    else
        printf '  [INATIVO/NÃO CONFIGURADO] %s\n' "$unit"
    fi
done
[[ -e /etc/polkit-1/rules.d/50-central-fedorento-printer-admin.rules ]] && printf '  [PRESENTE] Regra local de administração CUPS.\n' || printf '  [AUSENTE] Regra local de administração CUPS.\n'
[[ -e /etc/samba/smb.conf.d/central-fedorento-publico-users.conf ]] && printf '  [PRESENTE] Configuração Samba gerenciada pela Central.\n' || printf '  [AUSENTE] Configuração Samba gerenciada pela Central.\n'

# 1. Otimização do DNF5
printf '\n=== 1. Otimizando configurações do DNF ===\n'
if [[ -f /etc/dnf/dnf.conf ]] && ! grep -q '^max_parallel_downloads=' /etc/dnf/dnf.conf; then
    printf 'max_parallel_downloads=10\n' | sudo tee -a /etc/dnf/dnf.conf >/dev/null
fi

# 2. Atualização inicial
printf '\n=== 2. Atualizando o sistema ===\n'
sudo dnf upgrade --refresh -y

# 3. Pastas padrão em português
printf '\n=== 3. Configurando pastas padrão (PT-BR) ===\n'
sudo dnf install -y xdg-user-dirs
LANG=pt_BR.UTF-8 xdg-user-dirs-update --force

# 4. RPM Fusion
printf '\n=== 4. Habilitando RPM Fusion (Free e Nonfree) ===\n'
FEDORA_VERSION="$(rpm -E %fedora)"
if ! rpm -q rpmfusion-free-release >/dev/null 2>&1 || ! rpm -q rpmfusion-nonfree-release >/dev/null 2>&1; then
    sudo dnf install -y \
        "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-${FEDORA_VERSION}.noarch.rpm" \
        "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-${FEDORA_VERSION}.noarch.rpm"
fi
sudo dnf upgrade --refresh -y

# 5. Codecs multimídia
printf '\n=== 5. Instalando codecs multimídia ===\n'
sudo dnf swap -y ffmpeg-free ffmpeg --allowerasing || true
sudo dnf update -y @multimedia --setopt='install_weak_deps=False' --exclude=PackageKit-gstreamer-plugin || true
sudo dnf install -y --skip-unavailable \
    vlc rhythmbox lame \
    gstreamer1-plugins-bad-free gstreamer1-plugins-bad-free-extras \
    gstreamer1-plugins-bad-freeworld gstreamer1-plugins-ugly \
    gstreamer1-plugins-good-extras gstreamer1-libav

# Aceleração de vídeo, conforme o hardware
if command -v lspci >/dev/null 2>&1; then
    if lspci | grep -qi intel; then
        sudo dnf install -y --skip-unavailable intel-media-driver libva-intel-driver
    fi
    if lspci | grep -qi amd; then
        sudo dnf install -y --skip-unavailable mesa-va-drivers-freeworld mesa-va-drivers-freeworld.i686
    fi
    if lspci | grep -qi nvidia; then
        sudo dnf install -y --skip-unavailable libva-nvidia-driver libva-nvidia-driver.i686
    fi
fi

# 6. Fontes Microsoft Core
printf '\n=== 6. Instalando Microsoft Core Fonts ===\n'
sudo dnf install -y rpm cpio curl cabextract xorg-x11-font-utils fontconfig

# O RPM 2.6-1 é usado somente como arquivo: não instalamos o pacote nem executamos
# seus scriptlets. Conferimos o SHA-256 publicado no SourceForge antes de extrair.
FONT_RPM_URL='https://downloads.sourceforge.net/project/mscorefonts2/rpms/msttcore-fonts-installer-2.6-1.noarch.rpm'
FONT_RPM_SHA256='55d7f3a86533225634ff3ea2384b4356d9665a29cc7eeacff16602a1714afbb4'
FONT_TMP="$(mktemp -d)"
trap 'rm -rf -- "$FONT_TMP"' EXIT
FONT_RPM="$FONT_TMP/msttcore-fonts-installer-2.6-1.noarch.rpm"
FONT_EXTRACT="$FONT_TMP/extracted"
FONT_DEST='/usr/share/fonts/ms-cleartype'
mkdir -p "$FONT_EXTRACT"
if ! curl -fL --retry 3 --connect-timeout 15 --max-time 120 -o "$FONT_RPM" "$FONT_RPM_URL"; then
    printf 'Erro: não foi possível baixar o instalador de fontes Microsoft.\n' >&2
    exit 1
fi
if ! printf '%s  %s\n' "$FONT_RPM_SHA256" "$FONT_RPM" | sha256sum -c -; then
    printf 'Erro: SHA-256 do RPM não corresponde ao publicado pelo SourceForge; instalação cancelada.\n' >&2
    exit 1
fi
if ! command -v rpm2cpio >/dev/null 2>&1 || ! command -v cpio >/dev/null 2>&1; then
    printf 'Erro: rpm2cpio ou cpio não está disponível para extrair as fontes.\n' >&2
    exit 1
fi
if ! (cd "$FONT_EXTRACT" && rpm2cpio "$FONT_RPM" | cpio -id --quiet --no-absolute-filenames); then
    printf 'Erro: não foi possível extrair o RPM de fontes Microsoft.\n' >&2
    exit 1
fi
FONT_SOURCE="$FONT_EXTRACT/usr/share/fonts/msttcore"
if [[ ! -d "$FONT_SOURCE" ]]; then
    printf 'Erro: o RPM não contém o diretório esperado de fontes msttcore.\n' >&2
    exit 1
fi
mapfile -d '' FONT_FILES < <(find "$FONT_SOURCE" -maxdepth 1 -type f -name '*.ttf' -print0)
if (( ${#FONT_FILES[@]} == 0 )); then
    printf 'Erro: nenhum arquivo TTF foi encontrado no RPM extraído.\n' >&2
    exit 1
fi

# O diretório é dedicado às fontes copiadas por este método; substitui a cópia
# anterior sem instalar o RPM nem alterar o restante de /usr/share/fonts.
sudo rm -rf -- "$FONT_DEST"
sudo install -d -m 0755 "$FONT_DEST"
sudo install -m 0644 "${FONT_FILES[@]}" "$FONT_DEST/"
sudo fc-cache -fv
if ! fc-list | grep -iE 'arial|times|verdana|calibri|comic'; then
    printf 'Aviso: a instalação terminou, mas fc-list não encontrou as famílias esperadas.\n' >&2
fi
trap - EXIT
rm -rf -- "$FONT_TMP"

# 7. Aplicativos e utilitários do GNOME
printf '\n=== 7. Instalando aplicativos e extensões GNOME ===\n'
sudo dnf install -y --skip-unavailable \
    gedit dnfdragora \
    gnome-shell-extension-user-theme \
    gnome-tweaks gnome-extensions-app \
    gnome-shell-extension-dash-to-dock \
    gnome-shell-extension-dash-to-panel \
    gnome-shell-extension-appindicator \
    libreoffice libreoffice-langpack-pt-BR hunspell-pt-BR \
    firefox firefox-langpacks thunderbird \
    samba samba-client cifs-utils avahi nss-mdns \
    bluez bluez-tools gnome-bluetooth \
    file-roller unrar p7zip p7zip-plugins zip unzip \
    git wget curl rsync gparted remmina baobab gnome-disk-utility deja-dup \
    pavucontrol bash-completion fastfetch htop btop evince \
    yaru-theme papirus-icon-theme variety wine winetricks

# 8. Temas GTK/Shell e ícones
printf '\n=== 8. Instalando temas GTK/Shell e ícones ===\n'
THEME_TMP="$(mktemp -d)"
cleanup_themes() { rm -rf "$THEME_TMP"; }
trap cleanup_themes EXIT

install_theme_repo() {
    local checkout="$1" repo="$2"
    shift 2
    if ! git clone --depth=1 -- "$repo" "$THEME_TMP/$checkout"; then
        printf 'Aviso: não foi possível baixar %s; continuando com as demais etapas.\n' "$checkout" >&2
        return 0
    fi
    if ! (cd "$THEME_TMP/$checkout" && sudo bash ./install.sh "$@"); then
        printf 'Aviso: a instalação de %s falhou; continuando com as demais etapas.\n' "$checkout" >&2
    fi
    return 0
}

# Os instaladores upstream abaixo são executados como root para instalar em /usr/share.
# Revise/confie nas origens antes de executar este script; as branches remotas podem mudar.
install_theme_repo Orchis-theme https://github.com/vinceliuice/Orchis-theme.git \
    -d /usr/share/themes -t all -c dark -s standard --tweaks black -i fedora
install_theme_repo Colloid-gtk-theme https://github.com/vinceliuice/Colloid-gtk-theme.git \
    -d /usr/share/themes -t all -c dark -s standard --tweaks black
install_theme_repo Graphite-gtk-theme https://github.com/vinceliuice/Graphite-gtk-theme.git \
    -d /usr/share/themes -t all -c dark -s standard --tweaks black
install_theme_repo WhiteSur-gtk-theme https://github.com/vinceliuice/WhiteSur-gtk-theme.git \
    -d /usr/share/themes -c dark -t all --monterey

# Yaru e Papirus vêm dos pacotes Fedora instalados na seção 7.
install_theme_repo Tela-icon-theme https://github.com/vinceliuice/Tela-icon-theme.git \
    -d /usr/share/icons -a
install_theme_repo Colloid-icon-theme https://github.com/vinceliuice/Colloid-icon-theme.git \
    -s all -t all

if git clone --depth=1 -- https://github.com/bikass/kora.git "$THEME_TMP/kora"; then
    if sudo install -d -m 0755 /usr/share/icons \
        && sudo cp -a "$THEME_TMP/kora/kora" "$THEME_TMP/kora/kora-pgrey" /usr/share/icons/; then
        for icon_dir in /usr/share/icons/Tela* /usr/share/icons/Colloid* /usr/share/icons/kora /usr/share/icons/kora-pgrey; do
            [[ -d "$icon_dir" ]] && sudo gtk-update-icon-cache -f "$icon_dir" 2>/dev/null || true
        done
    else
        printf 'Aviso: não foi possível instalar os ícones Kora; continuando com as demais etapas.\n' >&2
    fi
else
    printf 'Aviso: não foi possível baixar Kora; continuando com as demais etapas.\n' >&2
fi
cleanup_themes
trap - EXIT
printf 'Temas e ícones instalados. Selecione-os em Ajustes/GNOME Tweaks.\n'

# 9. Drivers, impressão cotidiana e administração local de impressoras
printf '\n=== 9. Instalando suporte amplo a impressoras ===\n'
PRINTER_PACKAGES=(
    cups cups-client cups-pk-helper system-config-printer
    hplip hplip-gui gutenprint-cups foomatic-db-ppds printer-driver-brlaser
    cups-filters cups-filters-driverless
    sane-backends sane-airscan simple-scan
)
sudo dnf install -y "${PRINTER_PACKAGES[@]}"
sudo systemctl enable --now cups.service

# Regra idêntica à Central Fedorento 1.7. Somente ações cups-pk-helper
# necessárias à configuração de filas são liberadas para sessões locais ativas.
POLKIT_RULE=/etc/polkit-1/rules.d/50-central-fedorento-printer-admin.rules
POLICY_MARKER='// Managed by Central Fedorento: local printer administration v1'
POLICY_DISABLED=/var/lib/central-fedorento/printer-admin-disabled
PRINTER_ADMIN_ENABLED=0

enable_printer_admin_policy() {
    if sudo test -e "$POLKIT_RULE"; then
        if sudo grep -Fqx "$POLICY_MARKER" "$POLKIT_RULE"; then
            sudo rm -f -- "$POLICY_DISABLED"
            return 0
        fi
        printf 'Aviso: %s já existe e não pertence à Central; não será sobrescrito.\n' "$POLKIT_RULE" >&2
        return 1
    fi

    sudo install -d -o root -g root -m 0755 /etc/polkit-1/rules.d
    local policy_tmp
    policy_tmp="$(sudo mktemp /etc/polkit-1/rules.d/.central-fedorento-printer-admin.XXXXXX)"
    if ! sudo tee "$policy_tmp" >/dev/null <<'POLICY'
// Managed by Central Fedorento: local printer administration v1
polkit.addRule(function(action, subject) {
    var printerActions = [
        "org.opensuse.cupspkhelper.mechanism.all-edit",
        "org.opensuse.cupspkhelper.mechanism.class-edit",
        "org.opensuse.cupspkhelper.mechanism.devices-get",
        "org.opensuse.cupspkhelper.mechanism.printer-enable",
        "org.opensuse.cupspkhelper.mechanism.printer-local-edit",
        "org.opensuse.cupspkhelper.mechanism.printer-remote-edit",
        "org.opensuse.cupspkhelper.mechanism.printer-set-default",
        "org.opensuse.cupspkhelper.mechanism.printeraddremove"
    ];
    if (subject.local && subject.active && printerActions.indexOf(action.id) !== -1) {
        return polkit.Result.YES;
    }
});
POLICY
    then
        sudo rm -f -- "$policy_tmp"
        return 1
    fi
    sudo chmod 0644 "$policy_tmp"
    sudo chown root:root "$policy_tmp"
    sudo mv -f -- "$policy_tmp" "$POLKIT_RULE"
    sudo rm -f -- "$POLICY_DISABLED"
    return 0
}

disable_printer_admin_policy() {
    if sudo test -e "$POLKIT_RULE"; then
        if sudo grep -Fqx "$POLICY_MARKER" "$POLKIT_RULE"; then
            sudo rm -f -- "$POLKIT_RULE"
        else
            printf 'Aviso: regra externa de polkit mantida intacta em %s.\n' "$POLKIT_RULE" >&2
        fi
    fi
    sudo install -d -o root -g root -m 0700 /var/lib/central-fedorento
    sudo install -o root -g root -m 0600 /dev/null "$POLICY_DISABLED"
}

if sudo test -e "$POLICY_DISABLED"; then
    # Preserva uma escolha anterior feita pela Central ou por este script.
    if sudo grep -Fqx "$POLICY_MARKER" "$POLKIT_RULE" 2>/dev/null; then
        sudo rm -f -- "$POLKIT_RULE"
    fi
    printf 'Administração de impressoras sem senha permanece desativada por escolha anterior.\n'
else
    read -r -p 'Permitir que usuários com sessão local configurem impressoras sem senha? [S/n]: ' PRINTER_POLICY_ANSWER
    case "${PRINTER_POLICY_ANSWER,,}" in
        n|nao|não)
            disable_printer_admin_policy
            printf 'A política padrão de autenticação de impressoras será mantida.\n'
            ;;
        *)
            if enable_printer_admin_policy; then
                PRINTER_ADMIN_ENABLED=1
                printf 'Usuários locais com sessão ativa podem configurar impressoras pelas ferramentas Fedora sem senha.\n'
            else
                printf 'Não foi possível habilitar a regra; nenhuma política externa foi modificada.\n' >&2
            fi
            ;;
    esac
fi

printf '%s\n' 'A regra não libera sessões remotas, configurações globais do servidor CUPS nem trabalhos de outras pessoas.'
printf '%s\n' 'IPP-over-USB não é instalado automaticamente: ele pode conflitar com alguns drivers USB HPLIP/Gutenprint.'

if command -v hp-plugin >/dev/null 2>&1; then
    read -r -p 'Sua impressora HP pediu o plug-in proprietário? Abrir agora o instalador oficial (requer autorização e aceite da licença HP)? [s/N]: ' HP_PLUGIN_ANSWER
    case "${HP_PLUGIN_ANSWER,,}" in
        s|sim)
            if command -v pkexec >/dev/null 2>&1; then
                if ! pkexec hp-plugin; then
                    printf 'Aviso: o instalador HP não concluiu. Você pode tentar novamente pela Central Fedorento.\n' >&2
                fi
            else
                printf 'pkexec não está disponível; não foi iniciado o instalador do plug-in HP.\n' >&2
            fi
            ;;
        *) printf 'Plug-in proprietário HP não instalado; instale-o apenas se o seu modelo solicitar.\n' ;;
    esac
fi

# 10. Pasta Público individual para todas as contas pessoais, sem senha na rede
printf '\n=== 10. Pastas Público individuais e compartilhamento doméstico ===\n'
printf '%s\n' 'Cada usuário terá sua própria ~/Público; apenas essa subpasta será compartilhada, não o restante da pasta pessoal.'
printf '%s\n' 'As pastas Público de todas as contas pessoais serão acessíveis para leitura e gravação, sem senha, a dispositivos na rede confiável.'
printf '%s\n' 'O mesmo será aplicado a novas contas criadas depois. Não guarde documentos privados nessas pastas.'
read -r -p 'Para ativar essa regra para todos os usuários, digite SIM (qualquer outra resposta cancela): ' PUBLIC_SHARE_CONFIRM
PUBLIC_SHARE_ENABLED=0
if [[ "${PUBLIC_SHARE_CONFIRM^^}" == "SIM" ]]; then
    PUBLIC_SHARE_ENABLED=1
    if [[ -x /usr/libexec/central-fedorento-rules ]]; then
        printf 'Usando o mesmo configurador Samba da Central Fedorento para evitar arquivos de configuração duplicados.\n'
        sudo /usr/libexec/central-fedorento-rules samba-enable
        printf 'A pasta ~/Público está configurada; o nome de rede Publico-usuário foi preservado para compatibilidade.\n'
    else
    sudo dnf install -y --skip-unavailable samba samba-client policycoreutils-python-utils firewalld acl
    sudo install -d -m 0755 /etc/samba/smb.conf.d
    sudo python3 - <<'PY'
import os

old = '/etc/skel/Publico'
new = '/etc/skel/Público'

def unique_name(parent, name):
    stem, extension = os.path.splitext(name)
    candidate = f'{stem} (migrado de Publico){extension}'
    index = 2
    while os.path.lexists(os.path.join(parent, candidate)):
        candidate = f'{stem} (migrado de Publico {index}){extension}'
        index += 1
    return candidate

def merge(source, destination):
    for name in os.listdir(source):
        old_item = os.path.join(source, name)
        new_item = os.path.join(destination, name)
        if not os.path.lexists(new_item):
            os.replace(old_item, new_item)
        elif (os.path.isdir(old_item) and not os.path.islink(old_item)
              and os.path.isdir(new_item) and not os.path.islink(new_item)):
            merge(old_item, new_item)
        else:
            os.replace(old_item, os.path.join(destination, unique_name(destination, name)))
    os.rmdir(source)

if os.path.isdir(old) and not os.path.islink(old):
    if not os.path.lexists(new):
        os.replace(old, new)
    elif os.path.isdir(new) and not os.path.islink(new):
        merge(old, new)
elif os.path.lexists(old):
    print(f'Entrada antiga em /etc/skel preservada, não é diretório: {old}')
if not os.path.lexists(new):
    os.makedirs(new, mode=0o755)
elif os.path.isdir(new) and not os.path.islink(new):
    os.chmod(new, 0o755)
else:
    print(f'Não foi possível preparar o modelo ~/Público: {new} já existe e não é diretório.')
PY

    SMB_MAIN=/etc/samba/smb.conf
    SMB_SHARE=/etc/samba/smb.conf.d/fedorento-publico-users.conf
    if [[ ! -f "$SMB_MAIN" ]]; then
        printf '[global]\n' | sudo tee "$SMB_MAIN" >/dev/null
    fi
    if [[ ! -e "${SMB_MAIN}.fedorento-backup" ]]; then
        sudo cp -a "$SMB_MAIN" "${SMB_MAIN}.fedorento-backup"
    fi
    sudo semanage fcontext -a -t samba_share_t '/home/[^/]+/Público(/.*)?' \
        || sudo semanage fcontext -m -t samba_share_t '/home/[^/]+/Público(/.*)?'

    # Sincronizador: cria as pastas e shares de contas pessoais atuais e novas.
    sudo tee /usr/local/sbin/fedorento-publico-sync >/dev/null <<'SYNC_PY'
#!/usr/bin/env python3
import os
import pwd
import re
import stat
import subprocess
import tempfile
import time
from pathlib import Path

share_conf = Path('/etc/samba/smb.conf.d/fedorento-publico-users.conf')
share_conf.parent.mkdir(parents=True, exist_ok=True)
sections = []
for account in pwd.getpwall():
    if account.pw_uid < 1000 or not re.fullmatch(r'[A-Za-z0-9_.-]+', account.pw_name):
        continue
    home = os.path.realpath(os.path.normpath(account.pw_dir))
    if not home.startswith('/home/') or '/' in os.path.relpath(home, '/home'):
        continue
    # useradd pode atualizar /etc/passwd antes de terminar de criar a home.
    for _ in range(15):
        if os.path.isdir(home):
            break
        time.sleep(1)
    if not os.path.isdir(home) or any(c.isspace() for c in home):
        continue
    old_public = os.path.join(home, 'Publico')
    public = os.path.join(home, 'Público')
    if os.path.isdir(old_public) and not os.path.islink(old_public):
        if not os.path.lexists(public):
            os.replace(old_public, public)
            print(f'Pasta migrada: {old_public} -> {public}')
        elif os.path.isdir(public) and not os.path.islink(public):
            for entry in os.listdir(old_public):
                source = os.path.join(old_public, entry)
                target = os.path.join(public, entry)
                if os.path.lexists(target):
                    stem, extension = os.path.splitext(entry)
                    candidate = f'{stem} (migrado de Publico){extension}'
                    index = 2
                    while os.path.lexists(os.path.join(public, candidate)):
                        candidate = f'{stem} (migrado de Publico {index}){extension}'
                        index += 1
                    target = os.path.join(public, candidate)
                os.replace(source, target)
            os.rmdir(old_public)
            print(f'Conteúdo antigo de {old_public} mesclado em {public}; colisões foram renomeadas sem sobrescrever arquivos.')
    if os.path.islink(public):
        print(f'Pasta Público simbólica ignorada para {account.pw_name}: {public}')
        continue
    if os.path.lexists(public) and not os.path.isdir(public):
        print(f'Público já existe e não é diretório para {account.pw_name}: {public}; conta ignorada.')
        continue
    os.makedirs(public, exist_ok=True)
    os.chown(public, account.pw_uid, account.pw_gid, follow_symlinks=False)
    os.chmod(public, 0o1777, follow_symlinks=False)
    subprocess.run(['setfacl', '-m', 'u:nobody:--x', home], check=True)
    subprocess.run(['restorecon', '-RF', public], check=False)
    for root, dirs, files in os.walk(public, followlinks=False):
        for name in dirs + files:
            item = os.path.join(root, name)
            if os.path.islink(item):
                continue
            mode = stat.S_IMODE(os.stat(item, follow_symlinks=False).st_mode) | 0o666
            if os.path.isdir(item) or mode & 0o111:
                mode |= 0o111
            os.chmod(item, mode, follow_symlinks=False)
    sections.extend([
        f'[Publico-{account.pw_name}]',
        f'    path = {public}',
        '    browseable = yes',
        '    read only = no',
        '    guest ok = yes',
        '    guest only = yes',
        '    force user = nobody',
        '    follow symlinks = no',
        '    wide links = no',
        '    create mask = 0666',
        '    force create mode = 0666',
        '    directory mask = 0777',
        '    force directory mode = 0777',
        '',
    ])

new_text = '\n'.join(sections) or '# Nenhuma conta pessoal em /home ainda.\n'
old_text = share_conf.read_text(encoding='utf-8') if share_conf.exists() else None
if old_text != new_text:
    fd, tmp_name = tempfile.mkstemp(dir=str(share_conf.parent), prefix='.fedorento-publico-')
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(new_text)
    os.chmod(tmp_name, 0o644)
    os.replace(tmp_name, share_conf)
    try:
        subprocess.run(['testparm', '-s'], stdout=subprocess.DEVNULL, check=True)
    except Exception:
        if old_text is None:
            share_conf.unlink(missing_ok=True)
        else:
            share_conf.write_text(old_text, encoding='utf-8')
        raise
    subprocess.run(['systemctl', 'try-reload-or-restart', 'smb.service'], check=False)
SYNC_PY
    sudo chmod 0755 /usr/local/sbin/fedorento-publico-sync

    sudo python3 - "$SMB_MAIN" "$SMB_SHARE" <<'PY'
from pathlib import Path
import re
import sys

main = Path(sys.argv[1])
share = sys.argv[2]
text = main.read_text(encoding='utf-8')
if not re.search(r'(?im)^\s*\[global\]\s*$', text):
    text = '[global]\n' + text
sections = list(re.finditer(r'(?im)^\s*\[([^\]\r\n]+)\]\s*$', text))
global_section = next(m for m in sections if m.group(1).strip().lower() == 'global')
next_section = next((m for m in sections if m.start() > global_section.start()), None)
end = next_section.start() if next_section else len(text)
block = text[global_section.end():end]
additions = []
map_pattern = re.compile(r'(?im)^(\s*map\s+to\s+guest\s*=\s*).*$')
if map_pattern.search(block):
    block = map_pattern.sub(r'\1Bad User', block, count=1)
else:
    additions.append('    map to guest = Bad User')
if not re.search(r'(?im)^\s*include\s*=\s*' + re.escape(share) + r'\s*$', block):
    additions.append(f'    include = {share}')
if additions:
    text = text[:global_section.end()] + block.rstrip() + '\n' + '\n'.join(additions) + '\n' + text[end:]
main.write_text(text, encoding='utf-8')
PY

    sudo tee /etc/systemd/system/fedorento-publico-sync.service >/dev/null <<'SERVICE_EOF'
[Unit]
Description=Atualiza pastas Publico e compartilhamentos Samba de usuários locais

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/fedorento-publico-sync
SERVICE_EOF
    sudo tee /etc/systemd/system/fedorento-publico-sync.path >/dev/null <<'PATH_EOF'
[Unit]
Description=Detecta criação de novas contas locais para preparar suas pastas Publico

[Path]
PathChanged=/etc/passwd
Unit=fedorento-publico-sync.service

[Install]
WantedBy=multi-user.target
PATH_EOF

    sudo /usr/local/sbin/fedorento-publico-sync
    sudo testparm -s >/dev/null
    sudo systemctl daemon-reload
    sudo systemctl enable --now fedorento-publico-sync.path
    sudo systemctl enable --now smb.service nmb.service
    printf 'Exemplo de acesso à pasta do usuário atual: smb://%s/Publico-%s\n' "$(hostname)" "$REAL_USER"
    printf '%s\n' 'Os compartilhamentos das outras contas aparecem como Publico-NOME_DO_USUARIO.'

    # Abre o serviço somente na zona ativa após a confirmação da rede confiável.
    sudo systemctl enable --now firewalld.service
    ACTIVE_ZONE="$(sudo firewall-cmd --get-active-zones | awk 'NF {print $1; exit}')"
    if [[ -n "$ACTIVE_ZONE" ]]; then
        sudo firewall-cmd --permanent --zone="$ACTIVE_ZONE" --add-service=samba --add-service=mdns
        sudo firewall-cmd --reload
        printf 'Compartilhamentos Publico-* ativos na zona de firewall %s.\n' "$ACTIVE_ZONE"
    else
        printf 'Não encontrei uma zona de firewall ativa; o Samba foi configurado, mas o acesso pela rede ainda não foi aberto.\n'
    fi
    fi
else
    printf 'Compartilhamentos públicos cancelados; CUPS e as demais configurações continuam.\n'
fi

# 11. Flatpak, Snap e Extension Manager
printf '\n=== 11. Habilitando Flatpak, Snapd, Snap Store e Extension Manager ===\n'
sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
sudo flatpak install --system -y flathub com.mattjakeman.ExtensionManager
sudo dnf install -y snapd
sudo ln -sfn /var/lib/snapd/snap /snap
sudo systemctl enable --now snapd.socket snapd.service
printf 'Aguardando o serviço Snapd inicializar...\n'
sleep 5
sudo snap install snap-store || true

# 12. AppImage: suporte de execução e loja com catálogo
printf '\n=== 12. Preparando AppImage e instalando a loja AppImagePool ===\n'
sudo dnf install -y --skip-unavailable fuse fuse-libs flatpak
sudo install -d -o "$REAL_USER" -g "$REAL_GROUP" \
    "$REAL_HOME/Applications" "$REAL_HOME/.local/bin" "$REAL_HOME/.local/share/applications"
sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
if [[ "$(uname -m)" == "x86_64" ]]; then
    sudo flatpak install --system -y flathub io.github.prateekmedia.appimagepool
    printf 'AppImagePool instalado: catálogo e busca de AppImages disponíveis no menu.\n'
else
    printf 'O AppImagePool do Flathub está empacotado para x86_64; a pasta Applications e o suporte FUSE foram preparados, mas a loja não foi instalada nesta arquitetura (%s).\n' "$(uname -m)"
fi

# 13. Limpeza e finalização
printf '\n=== 13. Limpando caches e dependências não utilizadas ===\n'
sudo dnf autoremove -y
sudo dnf clean all
printf '%s\n' '------------------------------------------------------------------------------'
printf '%s\n' 'Instalador Dinâmico 4.5 concluído.'
if [[ "$PRINTER_ADMIN_ENABLED" == "1" ]]; then
    printf '%s\n' 'Administração local de filas de impressão sem senha habilitada via polkit/cups-pk-helper.'
else
    printf '%s\n' 'A política de administração de impressoras permanece protegida por autenticação.'
fi
if [[ "$PUBLIC_SHARE_ENABLED" == "1" ]]; then
    printf '%s\n' 'As pastas Público estão abertas sem senha somente na zona de rede atual; não conecte a redes públicas.'
    printf '%s\n' 'Novas contas pessoais em /home receberão Público e seu compartilhamento Publico-usuário automaticamente.'
else
    printf '%s\n' 'O compartilhamento público foi cancelado; CUPS, temas e demais etapas continuam configurados.'
fi
printf '%s\n' 'Reinicie a sessão para atualizar grupos e carregar extensões/temas do GNOME.'
printf '%s\n' '------------------------------------------------------------------------------'
