# Central Fedorento 1.13 — edição doméstica

A **Central Fedorento** é um painel em português brasileiro para configurar um Fedora doméstico com poucos cliques. Foi pensada para famílias e pessoas sem experiência técnica. A interface usa GTK4 e libadwaita no GNOME; as tarefas administrativas do sistema continuam passando por `pkexec`/polkit.

**Desenvolvedor:** Fabio Dias Silveira · **Contato:** [fabio140185@gmail.com](mailto:fabio140185@gmail.com).

## Tela inicial e explicações

A página inicial reúne quatro ações: **Atualização completa**, **Limpar kernels não usados**, **Crie seu Sistema** e **Instalador Dinâmico**. Este último executa o pós-instalação 4.5, verifica a distribuição, pacotes e configurações e instala ou ajusta componentes. A frase do cartão é “Instale tudo que você precisa em um clique”. **Crie seu Sistema** também está em **Sistema e serviços**. Ações administrativas abrem uma confirmação antes de executar; o Instalador Dinâmico oferece **Confirmar e executar**, **Negar** e **Cancelar**.

> A primeira instalação já traz um conjunto amplo de drivers Fedora e habilita, por padrão, a configuração local de impressoras sem senha. A regra pode ser desligada pela própria Central.

## Instalação

No Fedora, instale o RPM:

```bash
    sudo dnf install ./central-fedorento-1.13-1.noarch.rpm
```

A instalação do RPM pede a autorização normal do gerenciador de pacotes e instala também as dependências listadas abaixo. Na primeira instalação, CUPS e Samba são ativados por padrão. A pasta `Público` será compartilhada sem senha, com leitura e gravação na rede local.

Depois, abra **Central Fedorento** pelo menu de aplicativos ou execute `central-fedorento` sem `sudo`. O arquivo de menu agora usa o mesmo identificador do GTK (`org.fedorento.CentralFedorento`), e seu campo `Icon` aponta para o ícone `central-fedorento` instalado no tema hicolor; isso permite ao GNOME Shell associar a janela ao ícone correto em vez de mostrá-la como uma aplicação genérica. Para fixar, procure **Central Fedorento** na visão de atividades, clique com o botão direito no ícone e escolha **Adicionar aos favoritos**.

## Impressoras e permissões

### Drivers que já vêm instalados

O RPM depende dos pacotes Fedora `hplip`, `hplip-gui`, `gutenprint-cups`, `foomatic-db-ppds`, `printer-driver-brlaser`, `cups-filters`, `cups-filters-driverless` e `system-config-printer`. Isso cobre HPLIP, muitos modelos de diversas marcas, impressoras Brother laser e impressão driverless em rede. Para esses drivers, conectar e configurar uma impressora pelas ferramentas gráficas do Fedora não deve exigir que o usuário instale dependências manualmente.

O conjunto cobre muitos dispositivos, mas **não existe um pacote universal que garanta suporte a todo modelo**. Alguns fabricantes distribuem drivers proprietários ou específicos fora dos repositórios Fedora; a Central não baixa nem instala software externo arbitrário sem uma escolha explícita.

### Administração local sem senha

Por padrão, a Central cria uma regra polkit gerenciada para `cups-pk-helper`. Qualquer usuário com **sessão local ativa** pode, pelas interfaces gráficas Fedora que usam `cups-pk-helper`, descobrir dispositivos e adicionar, editar, remover, ativar/desativar e escolher filas de impressão sem digitar senha.

A regra não autoriza sessões remotas, não libera a alteração das configurações globais do servidor CUPS nem o cancelamento/edição dos trabalhos de outras pessoas. Ela não concede acesso ao DNF ou a outros pacotes. Ferramentas que não usam `cups-pk-helper` — por exemplo, a interface web do CUPS — continuam sujeitas às próprias políticas de autenticação. Na categoria **Impressoras e periféricos**, desmarque **Configurar impressoras sem senha (polkit)** para restaurar a política padrão do Fedora. A alteração dessa regra do sistema pede autorização administrativa.

Usuários comuns já podem **enviar trabalhos para imprimir** no CUPS sem `sudo`; a caixa acima trata somente da administração de filas nas interfaces compatíveis.

### Plug-in HP

Alguns modelos HP precisam de um plug-in binário proprietário que não é incluído nos pacotes Fedora por questões de licença. Se o HP Device Manager disser que o modelo exige esse plug-in, use na Central **Instalar plug-in proprietário HP (uma vez)**. A Central abre o instalador oficial HPLIP como administrador; leia e aceite a licença HP apenas se concordar. A instalação é global e, depois dela, o HP Device Manager não deve voltar a pedir senha para instalar o mesmo plug-in em cada fila. A autorização administrativa da primeira instalação continua necessária; a Central não desativa a segurança geral do sistema nem aceita a licença automaticamente.

### USB driverless

O suporte `ipp-usb` é opcional e fica fora da instalação automática. A documentação Fedora alerta que ele pode ocupar a conexão USB de algumas impressoras e conflitar com HPLIP/Gutenprint. Só use **Instalar suporte IPP-over-USB** se o modelo suportar esse protocolo e a instalação normal não funcionar.

### CUPS

- Na instalação inicial, o CUPS é habilitado; a caixa da categoria de impressoras permite desligá-lo. Desativar o serviço preserva filas e configurações.
- A configuração administrativa de impressoras sem senha é um controle separado do serviço CUPS.
- O suporte geral de scanner não instala `ipp-usb` automaticamente, para reduzir conflitos com impressoras USB.

## Compartilhamento doméstico Samba

- Na instalação inicial, a Central ativa o Samba e cria, para cada conta pessoal com diretório diretamente em `/home`, a pasta padrão do Fedora `~/Público`. O nome de rede continua `Publico-NOME_DO_USUARIO` para manter os endereços de rede compatíveis.
- Se existir uma pasta antiga `~/Publico`, a Central a renomeia para `~/Público` quando o destino não existe. Se ambas existirem, move o conteúdo antigo sem sobrescrever arquivos; itens com nomes em conflito recebem um sufixo “migrado de Publico”. Links simbólicos não são seguidos.
- O compartilhamento é **sem senha e com leitura/gravação**, limitado à pasta `Público`; não compartilha o restante da pasta pessoal. Ele fica disponível na zona de rede ativa do firewalld. Use somente uma rede doméstica confiável, não Wi‑Fi público.
- A Central instala um monitor systemd para incluir novas contas locais no mesmo esquema. Exemplo: `smb://nome-do-computador/Publico-nome`.
- Ao desativar, remove somente as definições e o monitor gerenciados pela Central, restaura permissões anteriores salvas e mantém pastas/arquivos. Shares Samba alheias são preservadas.
- Atualizações preservam escolhas que já tenham sido desligadas pelas caixas da Central.

## Instalador Dinâmico

O cartão **Instalador Dinâmico** abre um terminal do sistema para executar `fedora_pos_install.sh` como o usuário da sessão — não como root. A janela da Central pede consentimento primeiro; depois, o terminal lida com `sudo` e com perguntas específicas do script. A análise inicial identifica a distribuição, mostra pacotes presentes/ausentes e o estado de serviços e configurações; as instalações DNF são idempotentes e o script ajusta os componentes selecionados.

O instalador 4.5 pode atualizar o sistema, adicionar RPM Fusion, substituir componentes multimídia, baixar e executar instaladores de temas upstream com privilégios administrativos, preparar impressoras/fontes, ativar serviços e remover dependências órfãs. Isso altera o sistema e pode levar tempo; os repositórios e instaladores externos devem ser confiáveis. O script pede uma confirmação explícita para compartilhar `~/Público` sem senha (digite `SIM`) e mantém a instalação do plug-in proprietário HP opcional, condicionada à aceitação da licença. Ao desmarcar/negar/cancelar na confirmação da Central, nada é iniciado.

## Outros recursos

A Central reúne manutenção DNF/Flatpak/Snap/AppImage, AppImagePool, fontes Microsoft Core sob demanda, firmware, scanners, Bluetooth, áudio, temas e ícones (incluindo Yaru), contas, data/hora e ferramentas do GNOME. Cada ação administrativa tem confirmação; as ações comuns mostram a saída em um terminal integrado, e o Instalador Dinâmico usa um terminal interativo do sistema para suportar senha e perguntas.

### Fontes Microsoft Core

Na categoria **Aparência e extensões**, a ação **Instalar fontes Microsoft Core** instala Arial, Times New Roman, Verdana, Calibri, Comic e outras fontes Core. Ela é explícita e opcional: a Central não baixa o RPM ao ser instalada. A ação baixa o arquivo RPM de terceiros do SourceForge, confere o SHA-256 publicado e usa `rpm2cpio`/`cpio` para extrair somente os arquivos `.ttf` de `/usr/share/fonts/msttcore/`; depois copia as fontes para `/usr/share/fonts/ms-cleartype` com permissões `0644` e atualiza o cache.

O RPM de terceiros é antigo (versão 2.6-1, 2013) e não tem assinatura/digest interno. O hash fixado protege contra um arquivo diferente do publicado no SourceForge, mas não equivale a uma assinatura digital do publicador. **A Central não instala o RPM nem executa seus scriptlets**, portanto não usa `--nodigest`/`--nofiledigest` e não roda o instalador de CABs do pacote. As fontes são sujeitas à licença Microsoft incluída no RPM; revise-a antes de usar. A ação substitui somente o diretório dedicado `/usr/share/fonts/ms-cleartype` e não desinstala pacotes Noto/Liberation que já estejam no sistema.

### Crie seu Sistema

O botão **Crie seu Sistema**, disponível na tela inicial e em **Sistema e serviços**, abre a interface gráfica original fornecida no ZIP. Se os pacotes ainda não estiverem instalados, a Central pede confirmação e autorização pelo polkit, confere os SHA-256 fixados dos dois RPMs e instala-os com suas dependências via DNF. Os RPMs fornecidos não têm assinatura digital; os hashes fixados detectam alteração dos arquivos incluídos, mas não autenticam o publicador. A interface é noarch, mas o motor está empacotado para Fedora 44 x86_64, então a Central só oferece essa instalação nessa plataforma. A Central não os instala junto com a própria instalação.

O atalho do aplicativo é ocultado no menu por um override local do sistema e por uma cópia `NoDisplay=true` da conta atual; a interface continua sendo aberta pelo botão da Central. A instalação não executa scriptlets RPM do aplicativo (os dois pacotes examinados não os contêm). A interface original inclui uma caixa opcional que, se marcada, grava `/etc/sudoers.d/99-live-nopasswd` com `NOPASSWD: ALL` para a conta live e os grupos `wheel`/`sudo`, além de uma regra polkit ampla que também autoriza o grupo `adm`. **Essas regras são escritas na máquina atual, não são removidas ao terminar e podem ser incluídas na ISO.** A caixa vem desmarcada; mantenha-a assim salvo se quiser deliberadamente esse efeito e entender o risco. A Central não ativa essa opção por conta própria.

A interface grava os parâmetros em `/etc/penguins-eggs.d/custom.yaml`; ela pode substituir uma configuração anterior e não a restaura automaticamente. A remasterização pode levar vários minutos e usa `/home/eggs` como diretório padrão para a ISO. Reserve espaço livre e revise se a imagem contém configurações ou dados pessoais antes de compartilhá-la. O pacote gráfico declara MIT; o motor declara GPLv3. O [código-fonte correspondente do penguins-eggs 26.9.15](https://github.com/pieroproietti/penguins-eggs/tree/v26.9.15) está disponível no projeto upstream.

## Remoção

```bash
sudo dnf remove central-fedorento
```

Na remoção final do RPM, a Central remove somente a regra polkit de impressora que ela própria criou e restaura a política padrão do Fedora. Se o compartilhamento Samba da Central estiver ativo, o pacote executa a desativação e preserva os arquivos. A remoção **não desativa CUPS** nem apaga filas de impressão ou arquivos pessoais.

## Construção do RPM

Em Fedora com `rpm-build`:

```bash
TOP="$HOME/rpmbuild"
mkdir -p "$TOP"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
cp -a tree "$TOP/SOURCES/"
cp SPECS/central-fedorento.spec "$TOP/SPECS/"
rpmbuild --define "_topdir $TOP" -ba "$TOP/SPECS/central-fedorento.spec"
```

O RPM noarch aparece em `RPMS/noarch/`.

## Validação, limites e referências

A entrega foi validada estaticamente no ambiente de construção; não foi instalada em uma sessão Fedora com dispositivos reais. Confira as limitações de modelo e teste em uma máquina doméstica antes de distribuir amplamente.

- [Documentação HP: instalação do plug-in binário HPLIP e licença](https://developers.hp.com/hp-linux-imaging-and-printing/howtos/install)
- [Fedora: ferramenta de configuração de impressoras e cups-pk-helper](https://fedoraproject.org/wiki/Printing/ConfigurationTool)
- [cups-pk-helper: projeto upstream](https://www.freedesktop.org/wiki/Software/cups-pk-helper/)
- [Fedora: problemas conhecidos do CUPS/HPLIP/ipp-usb](https://docs.fedoraproject.org/en-US/quick-docs/cups-known-issues/)
- [Pacotes Fedora: hplip-gui](https://packages.fedoraproject.org/pkgs/hplip/hplip-gui/), [Gutenprint](https://packages.fedoraproject.org/pkgs/gutenprint/gutenprint-cups/), [Foomatic PPDs](https://packages.fedoraproject.org/pkgs/foomatic-db/foomatic-db-ppds/), [brlaser](https://packages.fedoraproject.org/pkgs/printer-driver-brlaser/printer-driver-brlaser/)
- [Projeto Microsoft Core Fonts no SourceForge](https://mscorefonts2.sourceforge.net/), [arquivo RPM com SHA-256 publicado](https://sourceforge.net/projects/mscorefonts2/files/rpms/msttcore-fonts-installer-2.6-1.noarch.rpm/download) e [documentação oficial rpm2cpio](https://rpm.org/docs/4.20.x/man/rpm2cpio.8.html).

## Licença

GPL-3.0-or-later. O texto completo acompanha o pacote em `LICENSE`.
