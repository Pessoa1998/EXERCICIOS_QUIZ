# Quiz Interativo com Streamlit

Este é um projeto de um quiz interativo e multijogador desenvolvido em Python com a biblioteca Streamlit. A aplicação permite que um moderador controle o fluxo de um quiz, enquanto múltiplos participantes respondem às perguntas em tempo real através de uma interface web.

## 🎯 Finalidade

O objetivo deste projeto é fornecer uma ferramenta simples e engajadora para a realização de quizzes em grupo, como em encontros de jovens, células de estudo, eventos de igreja ou simplesmente entre amigos. O tema das perguntas no arquivo `questions.json` é voltado para dilemas éticos e de fé sob uma perspectiva cristã, mas pode ser facilmente adaptado para qualquer outro assunto.

## ✨ Funcionalidades

- **Dois Papéis de Usuário**:
  - **Moderador**: Controla o início do jogo, a liberação de novas perguntas, o fim de uma rodada e o avanço para a próxima questão.
  - **Participante**: Entra no quiz com um nome, responde às perguntas dentro de um tempo limite e acompanha as respostas.
- **Tempo Real**: As ações do moderador são refletidas quase que instantaneamente na tela dos participantes.
- **Contagem de Pontos**: O sistema calcula e exibe a pontuação dos jogadores em tempo real no painel do moderador.
- **Perguntas Customizáveis**: As perguntas, opções, respostas corretas e explicações são carregadas a partir de um arquivo `questions.json`, permitindo fácil edição e personalização do conteúdo do quiz.
- **Persistência de Estado**: O estado do jogo (jogadores, pontuações, pergunta atual) é salvo no arquivo `game_state.json`, permitindo que o jogo resista a atualizações de página.

## 🛠️ Como Funciona

O `app2.py` utiliza o Streamlit para criar a interface de usuário. A aplicação gerencia dois painéis principais:

1.  **Painel do Moderador**: Apresenta botões para controlar o fluxo do jogo e exibe um ranking atualizado dos jogadores.
2.  **Painel do Participante**: Permite que o usuário insira um nome para entrar no jogo. Uma vez dentro, ele vê a pergunta atual, as opções de resposta e um cronômetro. Após a pergunta ser encerrada pelo moderador, a resposta correta e a base bíblica (explicação) são exibidas.

A aplicação usa um sistema de arquivos (`game_state.json` e um arquivo de lock) para gerenciar o estado compartilhado entre todas as sessões de usuário.

## 🚀 Como Executar o Projeto

### Pré-requisitos

- Ter o [Python](https://www.python.org/downloads/) instalado (versão 3.7 ou superior).

### 1. Instalação de Dependências

Abra o terminal ou prompt de comando e instale a biblioteca `streamlit`:

```bash
pip install streamlit
```

### 2. Execução da Aplicação

Navegue até a pasta do projeto pelo terminal e execute o seguinte comando:

```bash
streamlit run app2.py
```

Após executar o comando, o Streamlit abrirá uma nova aba no seu navegador com a aplicação em funcionamento. Para que o modo multijogador funcione, outras pessoas na mesma rede podem acessar o "Network URL" fornecido pelo Streamlit no seu terminal.

## 📂 Estrutura dos Arquivos

-   `app.py`: O código-fonte principal da aplicação Streamlit.
-   `questions.json`: O banco de dados de perguntas do quiz. Você pode editar este arquivo para criar seu próprio quiz.
-   `game_state.json` (gerado em tempo de execução): Arquivo que armazena o estado atual do jogo (jogadores, pontuações, etc.).
-   `README.md`: Este arquivo.

## ✏️ Como Personalizar as Perguntas

Para criar seu próprio quiz, basta editar o arquivo `questions.json`. Cada pergunta é um objeto JSON com a seguinte estrutura:

```json
{
  "id": 1,
  "tema": "Seu Tema Aqui",
  "pergunta": "O texto da sua pergunta?",
  "opcoes": [
    "Opção A",
    "Opção B",
    "Opção C",
    "Opção D"
  ],
  "correta": 2,
  "base_biblica": "Uma breve explicação ou referência para a resposta correta."
}
```

-   `id`: Um identificador numérico único para a pergunta.
-   `tema`: O tema ou categoria da pergunta.
-   `pergunta`: O texto da pergunta.
-   `opcoes`: Uma lista de strings com as opções de resposta.
-   `correta`: O índice (começando em 0) da resposta correta na lista `opcoes`.
-   `base_biblica`: A explicação que aparecerá após a pergunta ser respondida.
