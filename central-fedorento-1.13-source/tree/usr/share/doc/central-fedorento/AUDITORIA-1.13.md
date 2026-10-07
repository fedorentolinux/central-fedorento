# Revisão técnica — Central Fedorento 1.13

**Desenvolvedor:** Fabio Dias Silveira · **Contato:** fabio140185@gmail.com  
**Data:** 2026-10-07

Esta é uma revisão estática da integração solicitada; não substitui testes em uma instalação Fedora real.

## Ícone e associação no GNOME Shell

O ID da aplicação GTK é `org.fedorento.CentralFedorento`, mas o pacote 1.11 instalava o lançador com o ID de desktop `central-fedorento.desktop`. Essa divergência podia impedir o GNOME Shell de associar a janela ao item do menu, resultando em ícone genérico ou impossibilidade de agrupar/fixar corretamente. Nesta versão, o desktop file é `org.fedorento.CentralFedorento.desktop`, declara `StartupWMClass=org.fedorento.CentralFedorento` como compatibilidade para X11 e mantém `Icon=central-fedorento`, cujo SVG continua instalado em `hicolor/scalable/apps/central-fedorento.svg`.

Assim o identificador do lançador corresponde ao `application_id` usado pela janela GTK; a pessoa pode localizar a Central na visão de atividades e usar o menu de contexto para **Adicionar aos favoritos**. Esta correção foi validada nos metadados e arquivos RPM; a associação visual ainda deve ser confirmada numa sessão GNOME real.

## Instalador Dinâmico e consentimento

A tela inicial agora oferece o cartão **Instalador Dinâmico**, com a descrição **“Instale tudo que você precisa em um clique”**. Antes de abrir o terminal, a Central explica que o script atualiza/instala pacotes, habilita RPM Fusion, pode trocar pacotes multimídia, executa instaladores de temas upstream com privilégios administrativos, ativa serviços e remove dependências órfãs. O diálogo separa **Confirmar e executar**, **Negar** e **Cancelar**; negar ou cancelar não inicia processo algum. Após confirmar, o script abre num terminal interativo, necessário porque pede senha `sudo` e respostas adicionais. O usuário ainda confirma separadamente o compartilhamento Samba digitando `SIM`; o plug-in HP é opcional.

O script empacotado é a versão 4.5, baseada no pós-instalação 4.4 já presente no workspace. O anexo recebido nesta tarefa era uma cópia 4.3 mais antiga que reinstalava o RPM externo de fontes com `--nodigest`; a versão 4.5 mantém o método de extração com SHA-256 e acrescenta um relatório inicial da distribuição, pacotes principais, serviços e configurações. O script completo não foi executado no ambiente de construção, pois alteraria o sistema.

## Pasta Samba `Público`

A pasta compartilhada e monitorada passou a ser `~/Público`, em linha com `xdg-user-dirs` no Fedora em português. Ao ativar o Samba, o sincronizador renomeia `~/Publico` para `~/Público` quando o destino não existe. Se ambas existirem, mescla as entradas sem sobrescrever nomes em conflito e acrescenta um sufixo aos itens migrados; links simbólicos não são seguidos. ACLs SELinux e restauração ao desativar foram atualizadas para o caminho acentuado.

O nome do compartilhamento na rede permanece `Publico-NOME_DO_USUARIO`, preservando links `smb://.../Publico-nome` já usados. Quando instalado com a Central, o pós-instalação 4.5 chama o mesmo helper Samba para evitar duplicar configuração e monitor; a implementação alternativa para uso autônomo também aponta para `Público`.

## Escopo da alteração

- A tela inicial mostra quatro cartões: **Atualização completa**, **Limpar kernels não usados**, **Crie seu Sistema** e **Instalador Dinâmico**. Os controles CUPS/Samba permanecem em suas categorias próprias.
- **Crie seu Sistema** também aparece em **Sistema e serviços**, como atalho contextual pedido. Ele abre a interface gráfica original do pacote fornecido; não foi criada uma nova tela nem substituída a GUI original.
- O topo da página inicial explica a finalidade da Central. Os botões de ação, controles de alternância, menu Sobre e botão de fechar a saída receberam tooltips descritivos.
- Se a interface e o motor não estiverem disponíveis, o botão apresenta uma confirmação, pede autorização polkit e chama uma ação fixa do helper para instalar os dois RPMs e suas dependências via DNF. Essa instalação é sob demanda; o RPM da Central não instala o motor nem a interface automaticamente.
- Depois da instalação, a Central inicia `/usr/bin/crie-seu-sistema` como o usuário da sessão, não como root. O atalho do aplicativo é ocultado com um override `NoDisplay=true` em `/usr/local/share/applications` e outro na conta que abriu a interface; o arquivo fornecido em `/usr/share/applications` é preservado. Assim, o acesso normal é pelo botão da Central.

## Pacotes embutidos

| Pacote | NEVRA | Licença declarada | SHA-256 do arquivo embutido |
|---|---|---|---|
| Interface Crie seu Sistema | `crie-seu-sistema-1.0.0-1.noarch` | MIT | `44036bd033cd2be193e8c2b567d183689d3d5c046264e69edd3857ed3ba9d992` |
| Motor penguins-eggs | `penguins-eggs-26.9.15-1.fc44.x86_64` | GPLv3 | `c4bb3301dea40b4e14d0ac7b5d32210eb677db4ee8bf4a28900f256f25a21541` |

Os dois RPMs foram inspecionados e não contêm scriptlets. Nenhum deles tem assinatura digital. Os hashes estão fixados para detectar alteração dos bytes incluídos na Central, mas **não autenticam a identidade do publicador**. O motor fornecido é específico para Fedora 44 x86_64; a Central recusa instalar esses arquivos em outra versão ou arquitetura. O DNF continua responsável por resolver dependências dos repositórios configurados.

## Privilégios e efeitos da interface original

O helper original da interface não foi alterado. A caixa `Configurar sudo/polkit sem senha para o usuário live` começa desmarcada. Se a pessoa a marcar, o helper escreve `/etc/sudoers.d/99-live-nopasswd` com `NOPASSWD: ALL` para o usuário live e os grupos `wheel`/`sudo`, e cria uma regra polkit que autoriza `adm` e qualquer ação polkit. **As regras são gravadas na máquina atual e o helper não as remove ao terminar; elas podem também ser copiadas para a ISO.** Isso é amplo; a Central alerta explicitamente e não marca a caixa nem cria essas regras por conta própria.

Ao iniciar a remasterização, o helper original grava os parâmetros em `/etc/penguins-eggs.d/custom.yaml` e não restaura automaticamente um arquivo anterior. O botão da Central somente abre a interface; esse comportamento da aplicação fornecida permanece inalterado.

## Validações executadas

- `python3 -m py_compile` na interface da Central e no sincronizador, `bash -n` no helper e no script 4.5, e compilação de três blocos Python embutidos no shell script.
- Conferência de NEVRA, licença, arquitetura, hashes e ausência de scriptlets nos RPMs embutidos.
- Teste simulado do helper com `rpm` e DNF mock: confirmou o envio dos dois pacotes e a geração do override de menu preservando o comando de execução.
- Teste negativo: um byte adicionado ao RPM de teste fez o helper rejeitá-lo pelo SHA-256 antes de chamar DNF.
- Teste da função de menu em diretório temporário: escreveu `NoDisplay=true`, preservou os campos da entrada e foi idempotente.
- Revisão estática confirmou quatro ações na tela inicial, Crie seu Sistema em Sistema e serviços, tooltips nos botões visíveis, as três respostas do consentimento e execução externa do script em terminal interativo.
- Testes isolados em diretórios temporários confirmaram a migração `Publico` → `Público`, fusão recursiva e renomeação de colisões sem sobrescrever o conteúdo atual.
- Teste de associação: o nome-base de `/usr/share/applications/org.fedorento.CentralFedorento.desktop` corresponde exatamente ao `APP_ID` da aplicação GTK; `Icon=central-fedorento` corresponde ao SVG incluído e `StartupWMClass` corresponde ao mesmo ID.
- O RPM `noarch` 1.13-1 foi construído. `rpm -Kv` confirmou os digests do cabeçalho e payload; o pacote não tem assinatura digital. A lista e extração do payload confirmaram o script 4.5, desktop file, documentação e ícone. Os arquivos extraídos passaram novamente por `python3 -m py_compile` e `bash -n`.
- Nenhum RPM foi instalado no Sandbox e nenhum processo de remasterização/ISO foi executado.

## Limitações e referências

- A instalação efetiva com DNF, a autenticação polkit e a abertura em sessão GNOME não foram testadas em Fedora 44 real.
- Não foi criada uma ISO; armazenamento, tempo e compatibilidade do sistema real ainda precisam de teste.
- O hash fixado não substitui assinatura digital nem auditoria de código; use os RPMs somente se confiar no arquivo fornecido.
- Código-fonte upstream do motor: [penguins-eggs v26.9.15](https://github.com/pieroproietti/penguins-eggs/tree/v26.9.15); notas da [release v26.9.15](https://github.com/pieroproietti/penguins-eggs/releases/tag/v26.9.15).
