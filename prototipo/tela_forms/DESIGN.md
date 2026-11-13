---
name: RotaFácil ACS - UBS Partenon
colors:
  surface: '#f9f9ff'
  surface-dim: '#d4daea'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3ff'
  surface-container: '#e8eeff'
  surface-container-high: '#e3e8f9'
  surface-container-highest: '#dde2f3'
  on-surface: '#161c27'
  on-surface-variant: '#444651'
  inverse-surface: '#2a303d'
  inverse-on-surface: '#ecf0ff'
  outline: '#757682'
  outline-variant: '#c5c6d3'
  surface-tint: '#405aa9'
  primary: '#001549'
  on-primary: '#ffffff'
  primary-container: '#002776'
  on-primary-container: '#7992e5'
  inverse-primary: '#b5c4ff'
  secondary: '#006e29'
  on-secondary: '#ffffff'
  secondary-container: '#93f99d'
  on-secondary-container: '#00752d'
  tertiary: '#6d5e00'
  on-tertiary: '#ffffff'
  tertiary-container: '#c4ab00'
  on-tertiary-container: '#4a4000'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b5c4ff'
  on-primary-fixed: '#00174d'
  on-primary-fixed-variant: '#25428f'
  secondary-fixed: '#93f99d'
  secondary-fixed-dim: '#77dc84'
  on-secondary-fixed: '#002107'
  on-secondary-fixed-variant: '#00531d'
  tertiary-fixed: '#ffe243'
  tertiary-fixed-dim: '#e3c600'
  on-tertiary-fixed: '#211b00'
  on-tertiary-fixed-variant: '#524700'
  background: '#f9f9ff'
  on-background: '#161c27'
  surface-variant: '#dde2f3'
typography:
  headline-xl:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.005em
  headline-md:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 30px
  headline-sm:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 19px
    fontWeight: '700'
    lineHeight: 26px
  body-lg:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md-bold:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 16px
    fontWeight: '700'
    lineHeight: 24px
  label-lg:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 16px
    fontWeight: '700'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Atkinson Hyperlegible Next
    fontSize: 14px
    fontWeight: '700'
    lineHeight: 18px
    letterSpacing: 0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-desktop: 1.5rem
  margin: 1.5rem
  margin-desktop: 2.5rem
  space-xs: 0.5rem
  space-sm: 0.75rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

O sistema atende aos Agentes Comunitários de Saúde (ACS) vinculados à Unidade Básica de Saúde (UBS) Partenon, em Porto Alegre, atuando no planejamento operacional, sequenciamento de microáreas e mapeamento de visitas domiciliares sob relevo e condições urbanas complexas.

A identidade adota um viés **Funcional Institucional de Alto Desempenho** (High-Contrast / Utility-First):
- **Objetividade Pública e Confiabilidade**: Transmite a solidez do SUS sem fricção visual, priorizando legibilidade sob iluminação variável em telas de terminais e desktops institucionais.
- **Eficiência Operacional**: Reduz o desgaste cognitivo de profissionais em jornadas de planejamento logístico intenso.
- **Acessibilidade Universal Estrita (WCAG 2.2 AA / AAA)**: Foco incondicional em contraste, rastreabilidade de foco de teclado e alvos de interação generosos. A cor nunca transporta significado de forma isolada; todo indicador de estado carrega redundância semântica obrigatória (glifo + texto de apoio).

## Colors

A matriz cromática cumpre os critérios mais rigorosos de contraste da WCAG 2.2 (níveis AA e AAA):

- **Primária Institucional (`#002776`)**: Azul profundo representativo da seriedade do serviço de saúde pública. Garante contraste superior a 12:1 contra fundos brancos e claros, sendo a base estrutural de botões de ação principal, barras de navegação e cabeçalhos de rotas.
- **Sucesso / Ação Positiva (`#007A2F`)**: Verde equilibrado para status de visitas concluídas, rotas validadas e sincronização de dados bem-sucedida. Contraste mínimo de 4.6:1 contra branco.
- **Destaque / Alerta (`#FFDF00`)**: Amarelo ouro para marcação de microáreas prioritárias, pacientes acamados e alertas de terreno. **Regra mandatória**: Qualquer elemento com fundo `#FFDF00` deve ter tipografia aplicada obrigatoriamente no azul primário `#002776` (proibido o uso de texto branco ou cinza claro).
- **Superfícies e Neutros**:
  - Fundo geral da tela: `#F5F7FA` (antirreflexo e confortável para uso contínuo).
  - Superfícies de cartões e modais: `#FFFFFF`.
  - Texto principal (headings, corpo e rótulos de alta prioridade): `#1A202C` (quase preto, ratio > 14:1 contra branco).
  - Texto secundário/apoio: `#475569` (mantendo ratio superior a 4.5:1).
  - Linhas divisórias e bordas estruturantes: `#CBD5E1` (proporciona 3:1 de delimitação visual de containers e campos interativos).
- **Foco e Teclado**:
  - Contorno de foco duplo: anel interno branco `#FFFFFF` (2px) com anel externo azul royal de alto contraste `#0256D9` (3px) para navegação inequívoca via teclado (WCAG 2.2 critério 2.4.11 / 2.4.13).

## Typography

O sistema adota integralmente a família **Atkinson Hyperlegible Next**, desenhada especificamente para maximizar a distinção entre caracteres ambíguos (ex: I, l, 1, 0, O), essencial para identificação precisa de números de prontuários, logradouros de Porto Alegre e microáreas da UBS.

Regras de aplicação:
- **Tamanho Mínimo de Leitura**: Nenhum texto de fluxo contínuo ou formulário pode ser inferior a `16px` (`body-md`). O tamanho `14px` (`label-md`) é reservado estritamente a metadados secundários com caixa alta e espaçamento expandido.
- **Hierarquia Estrita**:
  - `headline-xl`: Títulos de visão macro (ex: "Painel de Território - Microárea 04").
  - `headline-lg`: Cabeçalhos de rota diária e seções de visualização de itinerário.
  - `headline-md`: Títulos de cartões de residência e fichas de família.
  - `body-lg` e `body-md`: Instruções de visita, notas do ACS e alertas clínicos.
- **Espaçamento e Legibilidade**: Line-height mínimo calibrado para 1.5x em blocos de texto (`24px` sobre `16px`), garantindo que usuários com baixa acuidade visual realizem leitura sem salto involuntário de linha.

## Layout & Spacing

A arquitetura de tela privilegia o desktop padrão de postos de saúde (1440px):
- **Grid de Trabalho**: Grid fluida assimétrica estruturada em 12 colunas com calhas (`gutter`) de `1.5rem` (24px) e margens externas de `2.5rem` (40px).
- **Layout de Divisão de Tela**:
  - **Coluna de Planejamento (4 colunas - ~420px fixos/proporcionais)**: Lista ordenada de domicílios, prioridades e tempo estimado.
  - **Coluna de Território/Mapa (8 colunas - restante da largura)**: Visualizador geoespacial interativo da encosta/morro do Partenon com rotas traçadas.
- **Áreas de Toque e Clique**: Rigorosamente respeitado o alvo interativo mínimo de **48x48px** para botões de controle, nós da rota e alternadores. Nenhum elemento clicável é inferior a 44px de altura efetiva.

## Elevation & Depth

Para garantir acessibilidade cognitiva e evitar distorções ópticas em monitores públicos de baixo contraste:
- **Ausência de Sombras Ambíguas**: Não são utilizadas sombras complexas ou difusas que possam confundir usuários com deficiência visual.
- **Bordas Estruturantes Claras**: A separação entre planos apoia-se em contornos geométricos nítidos de `1px` ou `2px` usando `#CBD5E1`.
- **Estratificação por Camadas Planas (Tonal Layers)**:
  - Nível 0: Base da tela `#F5F7FA`.
  - Nível 1: Cartão e painel de lista `#FFFFFF` com borda de 1px `#CBD5E1`.
  - Nível 2: Item selecionado ou foco ativo com borda de 2px no azul institucional `#002776`.
  - Nível 3 (Flutuante / Modal): Superfície `#FFFFFF` com contorno de 2px `#002776` e sombra sólida curta de alto contraste (`0px 4px 12px rgba(0, 39, 118, 0.15)`).

## Shapes

O sistema utiliza a escala de suavização controlada **Soft (nível 1)**:
- Raio padrão de botões, inputs e chips: `0.25rem` (4px).
- Raio de cartões e módulos de agrupamento: `0.5rem` (8px).
- A geometria quase ortogonal reforça a estabilidade institucional e facilita o alinhamento de guias e eixos de rota no mapa, prevenindo a perda de espaço útil nos cantos de cartões densos de informação do SUS.

## Components

### Botões e Controles de Rota
- **Botão Primário (Iniciar Rota / Salvar Planejamento)**: Altura mínima de 48px, preenchimento `#002776`, texto em branco `#FFFFFF` (Atkinson 16px Bold), cantos arredondados de 4px. No estado de foco: anel duplo (`2px branco + 3px #0256D9`).
- **Botão de Confirmação/Visita Efetuada**: Fundo `#007A2F`, texto `#FFFFFF`, acompanhado obrigatoriamente de ícone de verificação (Check) e rótulo "Concluir Visita".
- **Botão de Alerta/Atenção Especial**: Fundo `#FFDF00`, texto `#002776`, ícone de triângulo de exclamação e rótulo explícito "Prioridade Alta".

### Indicadores e Chips de Status (Indicadores Duplos Obrigatórios)
- Proibido o uso exclusivo de círculos coloridos para indicar status.
- **Pendente**: Chip com borda cinza `#CBD5E1`, ícone de relógio e texto "Não Visitado".
- **Em Andamento**: Chip com fundo azul claro (`#E6F0FA`), borda `#002776`, ícone de seta de itinerário e texto "Em Rota".
- **Realizada**: Chip com fundo verde claro (`#E7F7ED`), borda `#007A2F`, ícone de checagem preenchido e texto "Visita Concluída".

### Cartões de Domicílio / Paciente
- Fundo branco `#FFFFFF`, borda sólida de `1px #CBD5E1` (passando a `2px #002776` quando selecionado).
- Padding interno de `1rem` (16px).
- Cabeçalho do cartão contendo número de ordem da parada (em bloco contrastante 32x32px `#002776` com algarismo branco), endereço completo em `body-md-bold`, e chip de prioridade clínica com redundância visual.
- Área de clique do card inteiro unificada para seleção de itinerário, com suporte completo a atalhos numéricos de teclado.

### Campos de Entrada e Busca de Microárea
- Altura vertical de 48px.
- Fundo `#FFFFFF`, borda de `1.5px #1A202C` em repouso (para alta visibilidade de contorno, superando a norma de 3:1).
- Rótulo visível posicionado acima do campo em `body-md-bold` (proibido o uso exclusivo de placeholder).
- Mensagens de erro com texto explicativo em vermelho escuro `#990000`, ícone de alerta e contorno do campo de 2px.

### Caixas de Seleção (Checkboxes) e Radios
- Dimensão física de 24x24px, inscritos em uma área de clique de no mínimo 48x48px com espaçamento protetor.
- Borda de `2px #1A202C` quando desmarcado; fundo `#002776` e marcação branca grossa (3px) quando ativo.