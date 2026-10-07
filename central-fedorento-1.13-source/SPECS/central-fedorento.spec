Name:           central-fedorento
Version:        1.13
Release:        1%{?dist}
Summary:        Central de configuração doméstica Fedorento para GNOME
License:        GPL-3.0-or-later
URL:            https://fedorentolinux.github.io/
Packager:       Fabio Dias Silveira <fabio140185@gmail.com>
BuildArch:      noarch
Requires:       bash
Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       polkit
Requires:       dnf5
Requires:       util-linux
Requires:       rpm
Requires:       hicolor-icon-theme
Requires:       cups
Requires:       cups-client
Requires:       samba
Requires:       samba-client
Requires:       samba-common-tools
Requires:       acl
Requires:       policycoreutils-python-utils
Requires:       firewalld
Requires:       cups-pk-helper
Requires:       cups-filters
Requires:       cups-filters-driverless
Requires:       foomatic-db-ppds
Requires:       gutenprint-cups
Requires:       hplip
Requires:       hplip-gui
Requires:       printer-driver-brlaser
Requires:       system-config-printer

%description
Central de configuração doméstica em português brasileiro para Fedorento baseado em Fedora.
Inclui controles visuais reversíveis para impressão CUPS e compartilhamento da pasta Público via Samba, instalador dinâmico de pós-instalação, drivers de impressão comuns do Fedora, administração local de filas sem senha, extração das Microsoft Core Fonts sem instalar o RPM externo e um botão para abrir Crie seu Sistema com penguins-eggs.

%prep

%build

%install
mkdir -p %{buildroot}
cp -a %{_sourcedir}/tree/usr %{buildroot}/

%post
systemctl daemon-reload >/dev/null 2>&1 || :
/usr/libexec/central-fedorento-printer-policy default || printf 'Aviso: não foi possível configurar a política local de impressoras; abra a Central para revisar.\n' >&2
if [ ! -f /var/lib/central-fedorento/rules-initialized ]; then
    printf '\nAVISO: a configuração doméstica padrão ativará CUPS e Samba. O compartilhamento da pasta Público é sem senha e permite leitura/gravação na rede local; desligue a caixa Samba na Central se não quiser isso.\n'
    /usr/libexec/central-fedorento-rules household-defaults 1 1 || printf 'Aviso: a ativação padrão não terminou; abra a Central para revisar as caixas de Impressão e Samba.\n' >&2
fi
update-desktop-database &>/dev/null || :
/usr/bin/gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor &>/dev/null || :

%preun
if [ "$1" -eq 0 ]; then
    /usr/libexec/central-fedorento-printer-policy uninstall || :
fi
if [ "$1" -eq 0 ] && [ -f /etc/samba/smb.conf.d/central-fedorento-publico-users.conf ]; then
    /usr/libexec/central-fedorento-rules samba-disable || :
fi

%postun
systemctl daemon-reload >/dev/null 2>&1 || :
update-desktop-database &>/dev/null || :
/usr/bin/gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor &>/dev/null || :

%files
%defattr(-,root,root,-)
/usr/bin/central-fedorento
/usr/libexec/central-fedorento-helper
/usr/libexec/central-fedorento-rules
/usr/libexec/central-fedorento-publico-sync
/usr/libexec/central-fedorento-printer-policy
/usr/lib/systemd/system/central-fedorento-publico-sync.path
/usr/lib/systemd/system/central-fedorento-publico-sync.service
/usr/share/applications/org.fedorento.CentralFedorento.desktop
/usr/share/central-fedorento/central_fedorento.py
/usr/share/central-fedorento/fedora_pos_install.sh
%dir /usr/share/central-fedorento/remaster-packages
/usr/share/central-fedorento/remaster-packages/crie-seu-sistema-1.0.0-1.noarch.rpm
/usr/share/central-fedorento/remaster-packages/penguins-eggs-26.9.15-1.x86_64.rpm
%doc /usr/share/doc/central-fedorento/README.md
%doc /usr/share/doc/central-fedorento/AUDITORIA-1.13.md
%license /usr/share/licenses/central-fedorento/LICENSE
/usr/share/icons/hicolor/scalable/apps/central-fedorento.svg
