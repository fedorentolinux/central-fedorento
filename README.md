# Central Fedorento

> **Um painel simples para configurar, manter e personalizar o Fedora.**

Projeto de alguns meses: criei uma Central de configurações para o Fedora, que chamo de **Fedorento** por causa da minha ISO customizada. A ideia é reunir em um só lugar as principais tarefas de preparação e manutenção do sistema, com uma interface visual em português e explicações para quem prefere resolver as coisas com poucos cliques, sem depender do terminal no uso cotidiano.

A Central foi pensada para o uso doméstico: ajudar a instalar e atualizar programas, preparar impressoras e periféricos, configurar compartilhamento de arquivos, ajustar a aparência e facilitar a criação de uma remasterização do sistema. As operações administrativas pedem autorização; ações que alteram bastante o sistema também apresentam explicações e confirmações.

**Desenvolvedor:** Fabio Dias Silveira  
**Contato:** [fabio140185@gmail.com](mailto:fabio140185@gmail.com)  
**Projeto:** [fedorentolinux.github.io](https://fedorentolinux.github.io/)

---

## Sobre o projeto

O **Fedorento** é uma ISO personalizada baseada no Fedora. A **Central Fedorento** é o painel de controle visual criado para reunir ferramentas que normalmente ficam espalhadas por vários aplicativos, configurações e comandos. Ela não substitui o Fedora nem tenta esconder o que as ações fazem: a interface apresenta nomes, descrições e confirmações para que o usuário possa decidir o que deseja habilitar.

O projeto é voltado principalmente a computadores domésticos e a pessoas que querem um Fedora pronto para tarefas comuns, como navegar, instalar aplicativos, imprimir, digitalizar documentos, compartilhar arquivos em casa e personalizar o ambiente GNOME.

## Recursos

### Tela inicial

A página inicial oferece quatro ações principais:

- **Atualização completa** — executa a rotina de atualização do sistema e de componentes suportados.
- **Limpar kernels não usados** — remove kernels antigos elegíveis, preservando o kernel em execução e o anterior conforme a rotina do aplicativo.
- **Crie seu Sistema** — abre a interface gráfica de remasterização integrada à Central.
- **Instalador Dinâmico** — executa o script de pós-instalação que verifica o sistema e pode instalar ou ajustar componentes selecionados.

Os controles e botões incluem textos explicativos ao passar o ponteiro. As operações administrativas são encaminhadas pelos mecanismos de autorização do sistema, como polkit/`pkexec` e `sudo`, de acordo com a tarefa.

### Software e atualizações

A Central ajuda com tarefas de software como atualizar os metadados e pacotes do DNF5, atualizar aplicativos Flatpak e Snap, habilitar o Flathub e abrir o GNOME Software. Também inclui atalhos para operações de manutenção.

### Hardware, impressoras e periféricos

O painel reúne atalhos para identificar a placa gráfica e instalar componentes de vídeo disponíveis nos repositórios do Fedora, abrir as ferramentas de discos e partições e acessar opções de impressoras, scanners, Bluetooth e áudio.

O RPM inclui dependências de impressão do Fedora para uma variedade de dispositivos, incluindo HPLIP, Gutenprint, Foomatic, brlaser e ferramentas de configuração do CUPS. Isso cobre muitos modelos, mas **não garante compatibilidade com toda impressora**. Alguns modelos HP podem pedir um plug-in proprietário; a instalação é opcional, administrativa e exige que o usuário revise e aceite a licença do fabricante.

A administração de filas de impressão pode ser configurada para sessões locais sem senha por meio de uma regra específica de polkit para `cups-pk-helper`. Essa regra não concede acesso ao DNF, a pacotes nem à administração remota do CUPS. O envio cotidiano de trabalhos de impressão é separado da administração das filas. A Central permite desativar a regra e também controlar o serviço CUPS.

O suporte IPP-over-USB é opcional: em alguns dispositivos USB ele pode conflitar com HPLIP ou Gutenprint, então não é instalado automaticamente.

### Compartilhamento doméstico de arquivos

A Central pode configurar o Samba para compartilhar a pasta padrão `~/Público` de cada conta local. O nome de rede `Publico-NOME_DO_USUARIO` é mantido para compatibilidade com endereços já utilizados.

> **Atenção:** o compartilhamento configurado é sem senha e permite leitura e gravação a dispositivos que alcancem o computador pela rede. Guarde em `Público` somente arquivos que você aceita compartilhar e use essa opção apenas em uma rede doméstica confiável — nunca em uma rede pública.

Se houver uma pasta antiga `~/Publico`, o sincronizador tenta migrá-la para `~/Público`. Se as duas pastas já existirem, mescla os conteúdos sem sobrescrever os arquivos que já estão no destino; conflitos de nome recebem um sufixo. Links simbólicos não são seguidos. Um monitor do systemd prepara o compartilhamento para novas contas pessoais. O controle pode ser desativado na Central; pastas e arquivos são preservados.

### Instalador Dinâmico

O **Instalador Dinâmico** é o pós-instalação incluído com a Central. Antes de iniciá-lo, a interface apresenta uma confirmação com opções para **Confirmar e executar**, **Negar** ou **Cancelar**. Se o usuário negar ou cancelar, o script não é iniciado.

Após a confirmação, o instalador abre em um terminal interativo, pois algumas tarefas precisam da senha `sudo` ou de respostas específicas. A versão 4.5 faz um inventário inicial da distribuição, de pacotes importantes, de serviços e de configurações. Conforme as etapas do script, pode:

- atualizar o Fedora;
- habilitar RPM Fusion e instalar componentes multimídia;
- preparar suporte de impressão, fontes e outros recursos;
- instalar temas e ícones selecionados;
- habilitar Flatpak/Flathub, Snap e suporte AppImage, incluindo o AppImagePool quando disponível;
- oferecer a configuração Samba, que exige uma confirmação específica no terminal;
- remover dependências não utilizadas e limpar caches ao final.

Esse script **faz alterações abrangentes no sistema**, pode baixar software de repositórios e projetos externos e pode levar algum tempo. Leia as mensagens, confirme somente as ações com as quais concorda e execute-o apenas em uma instalação Fedora confiável. A configuração de compartilhamento Samba é opcional e requer confirmação própria, mesmo depois de autorizar a abertura do instalador.

### Aparência, fontes e extensões

A categoria de aparência contém atalhos para GNOME Tweaks, Extension Manager, temas e conjuntos de ícones. Entre os temas disponíveis estão Orchis, Colloid, Graphite, WhiteSur e Yaru; Yaru é mantido como opção. Há também opções como Papirus, Tela, Colloid e Kora para ícones.

A instalação das Microsoft Core Fonts é uma ação separada e opcional. A Central baixa o RPM de terceiros, verifica um SHA-256 fixado e extrai os arquivos de fonte sem instalar o RPM nem executar seus scriptlets. As fontes estão sujeitas à licença Microsoft; revise os termos antes de usar. Um hash ajuda a verificar se o arquivo corresponde ao esperado, mas **não comprova a identidade do publicador**.

### Crie seu Sistema

A integração de **Crie seu Sistema** permite abrir a interface original de remasterização pela tela inicial ou pela categoria **Sistema e serviços**. Se os pacotes ainda não estiverem instalados, a Central oferece a instalação sob demanda após confirmação e autorização administrativa.

Os RPMs incluídos não têm assinatura digital; a Central confere hashes fixados para detectar alterações nos arquivos, mas isso não autentica o publicador. O motor fornecido foi preparado para **Fedora 44 x86_64**, e a Central restringe a instalação nessa funcionalidade a essa versão e arquitetura. A Central não executa a remasterização automaticamente: o usuário configura e inicia o processo pela interface própria.

A interface original contém uma opção administrativa avançada relacionada a regras `sudo`/polkit amplas. Ela vem desmarcada. Mantenha-a desmarcada, salvo se compreender e desejar explicitamente os efeitos. Revise também configurações e arquivos pessoais antes de criar ou distribuir uma ISO.

## Instalação

### Instalar o RPM

Baixe o RPM compatível na área **Releases** do repositório e, no Fedora, execute no diretório onde ele foi salvo:

```bash
sudo dnf install ./central-fedorento-1.13-1.noarch.rpm
```

Depois, abra **Central Fedorento** no menu de aplicativos. Também é possível iniciar pelo terminal com:

```bash
central-fedorento
```

**Não execute a interface com `sudo`.** As operações administrativas são solicitadas pela própria aplicação quando necessário.

> **Importante na primeira instalação:** o pacote habilita CUPS e Samba por padrão. O compartilhamento Samba usa `~/Público`, sem senha e com leitura e gravação na rede ativa. Se não quiser esse comportamento, desative a opção Samba na Central e evite colocar arquivos privados na pasta compartilhada.

O RPM é `noarch`, mas algumas funções têm requisitos específicos da versão do Fedora e da arquitetura, em especial a integração de remasterização descrita acima.

## Construir o RPM a partir do código-fonte

A árvore deste repositório usa o diretório `tree/` para representar os arquivos que serão instalados no sistema e `SPECS/central-fedorento.spec` para as instruções do RPM. Em Fedora, instale as ferramentas de empacotamento:

```bash
sudo dnf install rpm-build
```

Na raiz do repositório, construa o pacote:

```bash
TOP="$HOME/rpmbuild-central-fedorento"
mkdir -p "$TOP"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
cp -a tree "$TOP/SOURCES/"
cp SPECS/central-fedorento.spec "$TOP/SPECS/"
rpmbuild --define "_topdir $TOP" -ba "$TOP/SPECS/central-fedorento.spec"
```

O RPM binário será criado em:

```text
$HOME/rpmbuild-central-fedorento/RPMS/noarch/
```

## Verificações de sintaxe

Antes de construir o pacote, é possível conferir os arquivos principais:

```bash
python3 -m py_compile \
  tree/usr/share/central-fedorento/central_fedorento.py \
  tree/usr/libexec/central-fedorento-publico-sync

bash -n \
  tree/usr/libexec/central-fedorento-rules \
  tree/usr/share/central-fedorento/fedora_pos_install.sh
```

Essas verificações não substituem testes de instalação numa sessão Fedora real, testes em diferentes modelos de impressora ou validação do comportamento do GNOME Shell no computador de destino.

## Estrutura do projeto

```text
.
├── README.md
├── SPECS/
│   └── central-fedorento.spec
└── tree/
    └── usr/
        ├── bin/                 # comando de inicialização
        ├── libexec/             # helpers administrativos e sincronizador Samba
        ├── lib/systemd/system/  # monitor de novas contas para o Samba
        └── share/
            ├── applications/    # lançador do GNOME
            ├── central-fedorento/ # interface GTK e pós-instalação
            ├── doc/             # documentação e auditoria
            └── icons/           # ícone do aplicativo
```

## Privacidade, segurança e limitações

- O projeto foi pensado para Fedora com GNOME e utiliza GTK4, libadwaita, PyGObject, DNF5, polkit, systemd e ferramentas de rede/serviços do Fedora.
- A configuração doméstica padrão ativa serviços selecionados, incluindo impressão e Samba. Revise os avisos antes de instalar ou usar a Central.
- O Samba compartilha a pasta `Público` sem autenticação e permite gravação na rede configurada. Não use em rede pública.
- A regra opcional de administração de impressoras sem senha aplica-se às operações locais compatíveis com `cups-pk-helper`; ela não equivale a uma liberação geral de privilégios.
- O plug-in HP é proprietário e sua licença não é aceita automaticamente.
- O instalador dinâmico pode fazer atualizações, instalar pacotes e remover dependências não utilizadas. Leia a saída e mantenha cópias de segurança dos arquivos importantes.
- Hashes de RPMs ou de fontes detectam alterações em relação ao valor esperado, mas não substituem assinatura digital nem auditoria da origem.
- A compatibilidade de hardware depende dos pacotes disponíveis no Fedora e do modelo específico. Nem todo dispositivo tem suporte garantido.
- A remasterização não foi testada em todo hardware ou cenário de uso; confira espaço livre e conteúdo da imagem antes de distribuir uma ISO.

## Remover

Para remover o aplicativo:

```bash
sudo dnf remove central-fedorento
```

A desinstalação remove a regra polkit de impressora criada pela Central e, quando aplicável, desativa a configuração Samba gerenciada por ela. A remoção preserva arquivos pessoais, pastas compartilhadas e filas de impressão. O serviço CUPS não é desativado automaticamente apenas por remover o RPM.

## Como contribuir

Sugestões, relatos de erro e melhorias são bem-vindos. Ao abrir uma issue, informe:

1. a versão da Central e do Fedora;
2. o ambiente gráfico e a arquitetura do computador;
3. qual ação estava sendo executada;
4. o texto completo da mensagem de erro, ocultando nomes de usuário, caminhos privados e outros dados pessoais;
5. se o problema é reproduzível após reiniciar ou numa conta de teste.

Antes de enviar uma alteração, descreva seu objetivo e teste a sintaxe dos arquivos modificados. Não inclua senhas, chaves, logs com dados pessoais ou arquivos de configuração privados.

## Licença

O pacote Central Fedorento declara licença **GPL-3.0-or-later**. Consulte o arquivo `tree/usr/share/licenses/central-fedorento/LICENSE` para o texto da licença. Componentes de terceiros incluídos ou instalados podem ter licenças próprias; elas continuam aplicáveis.
