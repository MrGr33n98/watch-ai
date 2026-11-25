---
title: Referência de Transferência de Calor — Whats AI
version: 1.0
language: pt-BR
sources: [trocadores.pdf, conv_nat.pdf, latente.pdf]
source_pages: 137
math: LaTeX
---

# REFERÊNCIA TÉCNICA — TRANSFERÊNCIA DE CALOR

Base de conhecimento para resolução de exercícios de engenharia. Consolidação dos capítulos 4, 5 e 6 dos três PDFs fornecidos. As páginas citadas são as páginas físicas dos arquivos. As equações foram normalizadas em LaTeX; os complementos operacionais e as inconsistências dos slides são identificados explicitamente. Não confundir esta referência com uma tabela completa de propriedades termofísicas.

## 0. Protocolo de resolução do agente

**Instrução operacional (complemento, não transcrição dos slides):**

1. Transcrever o enunciado e identificar cada questão e subitem; preservar dados, unidades, sinais, geometria e temperaturas. Se houver imagem ilegível, indicar precisamente o dado duvidoso; não inventar.
2. Identificar o mecanismo: trocador de calor, convecção natural/mista, condensação em película ou ebulição em vaso. Distinguir coeficiente local de médio, fluxo de calor de potência e entalpia de coeficiente convectivo.
3. Organizar dados e incógnitas em SI. Declarar hipóteses, direção do calor, área de referência, comprimento característico, temperatura para propriedades e regime.
4. Buscar a equação desta referência por geometria e regime. Verificar faixa de validade ANTES de calcular. Citar arquivo/página e ID da seção. Não substituir correlações silenciosamente.
5. Calcular todas as grandezas intermediárias, com fórmula simbólica, substituição numérica, unidades e resultado. Mostrar manipulações algébricas necessárias, inclusive derivadas e integrais se pedidas. Não impor limite fixo de etapas; dividir a apresentação em partes legíveis, sem omitir etapas.
6. Quando faltar propriedade, buscar em tabela fornecida/autorizada e citar origem, temperatura e pressão. Se não houver, dar solução simbólica ou resultado condicional; nunca inventar constantes ou coeficientes.
7. Validar conservação de energia, dimensões, sinais, regime e limites físicos; arredondar só ao final. Se houver múltiplas superfícies, somar potências por face, não coeficientes sem ponderação.
8. Para resposta em WhatsApp ou visor pequeno: uma operação matemática por linha; usar notação matemática com subscritos e expoentes; se o cliente não renderizar LaTeX, oferecer Unicode legível ou texto linear com parênteses inequívocos. Separar cada questão e apresentar resultado final com unidade.

### 0.1 Convenções e relações auxiliares (complemento operacional)

| Símbolo | Significado | SI |
|---|---|---|
| $\dot Q$, $q$ | taxa de calor | W |
| $q''$ | fluxo de calor por área | W/m² |
| $h$, $\bar h$, $U$ | CTC local, médio e global | W/(m² K) |
| $h_{lv}$ | entalpia específica de vaporização | J/kg |
| $k$ | condutividade térmica | W/(m K) |
| $\rho$ | massa específica | kg/m³ |
| $\mu$, $\nu$ | viscosidade dinâmica e cinemática | Pa s; m²/s |
| $c_p$ | calor específico a pressão constante | J/(kg K) |
| $\alpha$ | difusividade térmica | m²/s |
| $\beta$ | expansão volumétrica (cap. 5) | K⁻¹ |
| $\beta$ | compacidade (cap. 4) | m⁻¹ |
| $\sigma$ | tensão superficial (cap. 6); fração de passagem (cap. 4) | N/m; adimensional |
| $g$ | aceleração gravitacional | m/s² |
| $\dot m$, $\dot M$ | vazão mássica | kg/s |
| $\Gamma$ | vazão de condensado por perímetro molhado; em NTU, parâmetro adimensional distinto | kg/(m s) ou adimensional |
| $L,D,R,A,P$ | comprimento, diâmetro, raio, área, perímetro (P também é parâmetro F-MLDT) | m, m, m, m², m |
| $T_s,T_\infty,T_{sat}$ | superfície, fluido distante, saturação | K ou °C |

$$\nu=\frac{\mu}{\rho},\qquad \alpha=\frac{k}{\rho c_p},\qquad Pr=\frac{\nu}{\alpha}=\frac{\mu c_p}{k}$$
$$Re_\ell=\frac{V\ell}{\nu},\qquad Nu_\ell=\frac{h\ell}{k},\qquad \bar Nu_\ell=\frac{\bar h\ell}{k}$$
$$\dot m=\rho\dot V,\qquad \dot Q=q''A,\qquad q''=h\Delta T,\qquad \dot Q=\bar h A\Delta T$$
$$T_f=\frac{T_s+T_\infty}{2}\quad\text{(convecção natural)},\qquad T_f=\frac{T_s+T_{sat}}{2}\quad\text{(condensação)}$$

Usar $T[K]=T[°C]+273,15$ quando a temperatura absoluta for necessária (por exemplo, $\beta=1/T$); diferenças em K e °C têm o mesmo valor numérico. $g=9,81$ m/s² se não especificado. Áreas usuais: placa $ab$, lateral de cilindro $\pi DL$, esfera $\pi D^2$, seção circular $\pi D^2/4$. Não incluir bases ou segunda face se não participarem da troca.

# 1. CAPÍTULO 4 — TROCADORES DE CALOR
Fonte: `trocadores.pdf`, 82 páginas.

## TC-01 — Classificação e geometria (p. 2–18)

Equipamentos de troca térmica entre duas ou mais correntes, com ou sem contato direto. Em geral não há troca de calor/trabalho com a vizinhança. Formas: tubulares (duplo-tubo, casco-e-tubos, casco-espiral, pipecoil); placas (placa-armação, soldado, espiral, platecoil); aletados (tubo-aleta, placa-aleta); regenerativos (matriz fixa/rotativa). TEMA: exemplos AES, BEM, AEP, CFU, AKT, AJW (p. 6). Chicanas sustentam tubos, reduzem flexão/vibração e guiam o fluxo transversal ao feixe (p. 8). Aletas ampliam área do lado de menor CTC, frequentemente o lado do ar (p. 12). Microcanais são compactos, mas a distribuição de fluxo pode ser problemática (p. 13).

Compacidade (p. 16–18):

$$\beta=\frac{A_s}{V}\quad [m^2/m^3]$$
$$\sigma=\frac{A_c}{A_f},\quad D_h=\frac{4A_c}{P}=\frac{4A_cL}{A_s},\quad \frac{A_s}{A_c}=\frac{4L}{D_h},\quad \beta=\frac{4\sigma}{D_h}$$

$A_s$: superfície de troca; $A_c$: seção livre mínima de passagem; $A_f$: área frontal; $V=A_f L$: envelope; $P$: perímetro molhado. Material caracteriza compacto por $\beta\sim1000$ m⁻¹, cerca de dez vezes o casco-e-tubos típico; não tratar como limite universal.

Na figura de compacidade (p. 18), para feixe tubular com passos relativos $X_l^*$ e $X_t^*$ (passos longitudinal e transversal divididos por D), a expressão ilustrada é:

$$\beta=\frac{2\pi}{X_l^*X_t^*D}$$

Para $X_l^*X_t^*=1,88$, a figura aproxima $\beta=3333/D_{(mm)}$ em m²/m³. Para a outra família de superfícies, $\beta=4\sigma/D_h$ com $\sigma=0,833$ resulta aproximadamente em $\beta=3333/D_{h,(mm)}$ em m²/m³. São relações da figura para as geometrias indicadas, não constantes universais.

## TC-02 — Primeira lei e capacidades térmicas (p. 19–21)

Hipóteses: (1) sem trabalho; (2) regime permanente; (3) variações de energia cinética/potencial desprezíveis; (4) propriedades uniformes; (5) perdas de calor para ambiente desprezíveis. Corrente 1 quente e 2 fria, calor positivo da 1 para 2.

$$\dot Q_T=\dot M_1(h_{1,in}-h_{1,out})=\dot M_2(h_{2,out}-h_{2,in})$$

Para (6) ausência de mudança de fase e (7) $c_p$ aproximadamente constante:

$$\Delta h=c_p\Delta T,\quad \dot C_i=\dot M_i c_{p,i}$$
$$\dot Q_T=\dot C_1(T_{1,in}-T_{1,out})=\dot C_2(T_{2,out}-T_{2,in})$$
$$T_{1,out}=T_{1,in}-\frac{\dot Q_T}{\dot C_1},\quad T_{2,out}=T_{2,in}+\frac{\dot Q_T}{\dot C_2}$$

A primeira lei não basta para dimensionar a área. Com mudança de fase, usar entalpias e não $c_p\Delta T$ para a parcela latente.

## TC-03 — Equação fundamental e diferença efetiva (p. 22–26)

$$\delta\dot Q=U(T_1-T_2)dA$$
$$A=\int_0^{\dot Q_T}\frac{\delta\dot Q}{U(T_1-T_2)},\quad \dot Q_T=\int_0^{A_T}U(T_1-T_2)dA$$
$$\overline{U(T_1-T_2)}=\frac{1}{A}\int_A U(T_1-T_2)dA,\quad \dot Q_T=A\overline{U(T_1-T_2)}$$

Para $U$ uniforme:

$$\Delta T_M=\overline{T_1-T_2}=\frac{1}{A}\int_A(T_1-T_2)dA,\quad \dot Q_T=AU\Delta T_M$$

Não separar médias se U variar significativamente.

## TC-04 — Condutância global, incrustação e aletas (p. 27–33)

$$\frac{1}{UA}=\sum R_T$$
$$\frac{1}{UA}=\frac{1}{\eta_{o,i}h_i A_i}+\frac{R''_{f,i}}{A_i}+R_w+\frac{R''_{f,o}}{A_o}+\frac{1}{\eta_{o,o}h_o A_o}$$

$R''_f$ é fator de incrustação [m² K/W]; $R_w$ em K/W; $A_i,A_o$ incluem área de base e de aletas do lado correspondente. A referência $A$ pode ser interna ou externa, mas deve ser consistente com $U$: $U_iA_i=U_oA_o=UA$ (relação decorrente da definição).

$$A_i=A_{f,i}+A_{b,i},\quad A_o=A_{f,o}+A_{b,o}$$
$$A_i=\pi D_iL,\quad A_o=\pi D_oL\quad\text{(tubo liso)}$$
$$R_{w,plana}=\frac{t_w}{k_w A},\qquad R_{w,cil}=\frac{\ln(d_o/d_i)}{2\pi L_T k_w}$$

$L_T$ é comprimento total de parede tubular correspondente à área (em feixes idênticos, soma dos comprimentos dos tubos). Paredes em um único material; incrustação varia com tempo, velocidade e temperatura.

$$\dot Q_T=(\eta_{f,i}A_{f,i}h_{f,i}+A_{b,i}h_{b,i})(T_1-T_{w,1})$$

Se $h_{f,i}=h_{b,i}=h_i$:

$$\dot Q_T=\eta_{o,i}h_iA_i(T_1-T_{w,1})$$
$$\eta_{o,i}=1-(1-\eta_{f,i})\frac{A_{f,i}}{A_i},\qquad \eta_{o,o}=1-(1-\eta_{f,o})\frac{A_{f,o}}{A_o}$$

$\eta_f$ é eficiência individual da aleta, $\eta_o$ eficiência global da superfície. Sem aleta, $\eta_o=1$; limpo, $R''_f=0$. O PDF remete ao capítulo de aletas de Incropera e DeWitt, não fornece correlação completa para $\eta_f$ nem tabelas de incrustação.

## TC-05 — MLDT/LMTD: paralelo e contracorrente (p. 34–46)

| Arranjo | $\Delta T_a$ | $\Delta T_b$ |
|---|---|---|
| Paralelo (CP) | $T_{1,in}-T_{2,in}$ | $T_{1,out}-T_{2,out}$ |
| Contracorrente (CC) | $T_{1,in}-T_{2,out}$ | $T_{1,out}-T_{2,in}$ |

Coordenada de área ao longo da corrente quente:

$$dT_1=-\frac{\delta\dot Q}{\dot C_1}$$
$$dT_2=+\frac{\delta\dot Q}{\dot C_2}\ (CP),\qquad dT_2=-\frac{\delta\dot Q}{\dot C_2}\ (CC)$$
$$d(T_1-T_2)=-\delta\dot Q\left(\frac1{\dot C_1}\pm\frac1{\dot C_2}\right)$$

Sinal superior para CP, inferior para CC. Substituindo a equação fundamental:

$$\frac{d(T_1-T_2)}{T_1-T_2}=-U\left(\frac1{\dot C_1}\pm\frac1{\dot C_2}\right)dA$$
$$\int_{\Delta T_a}^{\Delta T_b}\frac{d(T_1-T_2)}{T_1-T_2}=-U\left(\frac1{\dot C_1}\pm\frac1{\dot C_2}\right)\int_0^A dA$$
$$\ln\frac{\Delta T_b}{\Delta T_a}=-UA\left(\frac1{\dot C_1}\pm\frac1{\dot C_2}\right)$$
$$T_1-T_2=\Delta T_a\exp\left[-UA\left(\frac1{\dot C_1}\pm\frac1{\dot C_2}\right)\right]$$
$$\dot C_1=\frac{\dot Q_T}{T_{1,in}-T_{1,out}},\quad \dot C_2=\frac{\dot Q_T}{T_{2,out}-T_{2,in}}$$

Substituindo capacidades na relação logarítmica, obtém-se:

$$\boxed{\Delta T_{LM}=\frac{\Delta T_a-\Delta T_b}{\ln(\Delta T_a/\Delta T_b)}}$$
$$\dot Q_T=UA\Delta T_{LM},\quad A=\frac{\dot Q_T}{U\Delta T_{LM}},\quad U=\frac{\dot Q_T}{A\Delta T_{LM}}$$
$$L=\frac{A_o}{n\pi d_o}\quad\text{(n tubos lisos idênticos)}$$

Hipóteses: U uniforme, capacidades constantes, arranjos fundamentais em passe simples, balanço anterior. Diferenças terminais positivas; não tomar valores absolutos para mascarar cruzamento fisicamente inválido. Se $\Delta T_a=\Delta T_b$, usar o limite $\Delta T_{LM}=\Delta T_a$ (L'Hospital). Se próximas, calcular de forma estável. Se uma diferença tender a zero, área requerida tende a infinito para carga finita e U finito.

## TC-06 — Casos especiais e limites (p. 47–51)

- $\dot C_1\gg\dot C_2$, $\dot C_1\to\infty$: $T_{1,in}\approx T_{1,out}$, como condensação de substância pura a pressão constante.
- $\dot C_2\gg\dot C_1$, $\dot C_2\to\infty$: $T_{2,in}\approx T_{2,out}$, como ebulição de substância pura a pressão constante.
- $\dot C_1=\dot C_2$ em CC: $\Delta T_a=\Delta T_b=\Delta T_{LM}$.
- Para mesmas temperaturas terminais e U, em condições não degeneradas, $\Delta T_{LM,CC}>\Delta T_{LM,CP}$ e CC exige menor área. CC permite $T_{2,out}>T_{1,out}$; CP não.

## TC-07 — F-MLDT: arranjos não fundamentais (p. 52–57)

$$F=\frac{\Delta T_M}{\Delta T_{LM,CC}},\quad \dot Q_T=UA F\Delta T_{LM,CC},\quad A=\frac{\dot Q_T}{UF\Delta T_{LM,CC}}$$
$$P=\frac{\Delta T_2}{\Delta T_{max}}=\frac{T_{2,out}-T_{2,in}}{T_{1,in}-T_{2,in}},\quad R=\frac{\dot C_2}{\dot C_1}=\frac{T_{1,in}-T_{1,out}}{T_{2,out}-T_{2,in}}$$

$F=F(P,R,\text{configuração})$. CC ideal é referência $F=1$; outros arranjos em geral $F<1$. Se uma corrente isotérmica, $P=0$ ou $R=0$ no limite e $F=1$. Não selecionar F arbitrariamente; evitar região de elevada sensibilidade a P. O slide não determina um valor mínimo numérico obrigatório.

Gráficos originais (não há tabela numérica nos slides): p. 53 um passe casco/2N tubos; p. 54 dois passes casco/4N tubos; p. 55 cruzado ambos não misturados; p. 56 cruzado um misturado. Nos gráficos, os índices são s=casco e t=tubos: $P_t=(T_{t,out}-T_{t,in})/(T_{s,in}-T_{t,in})$, $R_t=(T_{s,in}-T_{s,out})/(T_{t,out}-T_{t,in})$. Alinhar as correntes com os índices do gráfico, e não presumir que tubo é sempre frio. Para leitura, localizar P no eixo horizontal, seguir até a curva R e ler F; interpolação é aproximada e não deve ultrapassar a curva física.

**Complemento operacional derivado do próprio método ε-NTU**, para dispensar leitura do gráfico quando houver relação analítica aplicável: obter $\varepsilon=\dot Q_T/[\dot C_{min}(T_{1,in}-T_{2,in})]$, inverter a relação apropriada da seção TC-09/10 para NTU, e então

$$F=\frac{\dot Q_T}{NTU\,\dot C_{min}\,\Delta T_{LM,CC}}$$

Isso não substitui a curva de dois passes no casco quando não houver modelo correspondente; nesse caso usar o gráfico do PDF (p. 54 ou 76) ou declarar falta de dado.

## TC-08 — Efetividade e número de unidades de transferência (p. 58–65)

$$\dot C_{min}=\min(\dot C_1,\dot C_2),\quad \dot C_{max}=\max(\dot C_1,\dot C_2),\quad C^*=\frac{\dot C_{min}}{\dot C_{max}}$$
$$\Delta T_{max}=T_{1,in}-T_{2,in},\quad \dot Q_{max}=\dot C_{min}\Delta T_{max}$$
$$\varepsilon=\frac{\dot Q_T}{\dot Q_{max}}=\frac{\dot C_1(T_{1,in}-T_{1,out})}{\dot C_{min}(T_{1,in}-T_{2,in})}=\frac{\dot C_2(T_{2,out}-T_{2,in})}{\dot C_{min}(T_{1,in}-T_{2,in})}$$
$$0\le\varepsilon\le1,\quad \dot Q_T=\varepsilon\dot C_{min}(T_{1,in}-T_{2,in})$$
$$NTU=\frac{UA_s}{\dot C_{min}},\quad A_s=\frac{NTU\,\dot C_{min}}{U}$$

$\varepsilon=f(NTU,C^*,\text{arranjo})$; corrente de menor capacidade sofre maior variação térmica. Usar $C_{max}$ em $\dot Q_{max}$ violaria limites físicos (p. 60).

Se $\dot C_{min}=\dot C_1$:

$$\varepsilon=\frac{T_{1,in}-T_{1,out}}{T_{1,in}-T_{2,in}},\quad C^*=\frac{T_{2,out}-T_{2,in}}{T_{1,in}-T_{1,out}}$$
$$\frac{T_{1,out}-T_{2,out}}{T_{1,in}-T_{2,in}}=e^{-NTU(1+C^*)}=1-\varepsilon(1+C^*)$$
$$\frac{T_{1,out}-T_{2,in}}{T_{1,in}-T_{2,out}}=e^{-NTU(1-C^*)}=\frac{1-\varepsilon}{1-\varepsilon C^*}$$

A última igualdade é obtida do balanço; p. 65 também escreve $1-\varepsilon[1-e^{-NTU(1-C^*)}]$ para a razão, o que não é consistente com p. 64/66. Usar a igualdade derivada acima.

## TC-09 — ε-NTU para configurações básicas (p. 66–70)

Paralelo:

$$\varepsilon=\frac{1-e^{-NTU(1+C^*)}}{1+C^*},\qquad NTU=-\frac{\ln[1-\varepsilon(1+C^*)]}{1+C^*}$$

Contracorrente:

$$\varepsilon=\frac{1-e^{-NTU(1-C^*)}}{1-C^*e^{-NTU(1-C^*)}},\qquad NTU=\frac{1}{C^*-1}\ln\frac{\varepsilon-1}{\varepsilon C^*-1}$$

Limites: $C^*=1$: CP $\varepsilon=(1-e^{-2NTU})/2$; CC $\varepsilon=NTU/(1+NTU)$ e $NTU=\varepsilon/(1-\varepsilon)$ (inversão algébrica). $C^*=0$: ambos $\varepsilon=1-e^{-NTU}$ e $NTU=-\ln(1-\varepsilon)$. Para $NTU\to\infty$, CP tende a $1/(1+C^*)$, CC a 1. Em condições não degeneradas CC é mais efetivo que CP para o mesmo NTU e $C^*$.

## TC-10 — ε-NTU: demais arranjos (p. 73–76, tabela 3.3)

Notação compacta desta seção: $x=NTU$, $c=C^*$. Todos os casos são para a configuração de mistura indicada, sem confundir mistura transversal com mistura das correntes entre si.

### Cruzado, ambos não misturados — série da tabela

$$\varepsilon=1-e^{-x}-e^{-(1+c)x}\sum_{n=1}^{\infty}c^n P_n(x)$$
$$P_n(y)=\frac{1}{(n+1)!}\sum_{j=1}^{n}\frac{n+1-j}{j!}y^{n+j}$$

Para $c=1$, mesma fórmula; $x\to\infty$: $\varepsilon\to1$. Para implementar a série, controlar convergência e estabilidade; não truncar sem avaliar erro.

### Cruzado, $C_{min}$ misturado e $C_{max}$ não misturado

$$\varepsilon=1-\exp\left[-\frac{1-e^{-xc}}{c}\right]$$
$$c=1:\ \varepsilon=1-\exp[-(1-e^{-x})],\quad x\to\infty:\ \varepsilon=1-e^{-1/c}$$

### Cruzado, $C_{max}$ misturado e $C_{min}$ não misturado

$$\varepsilon=\frac{1-\exp[-c(1-e^{-x})]}{c}$$
$$c=1:\ \varepsilon=1-\exp[-(1-e^{-x})],\quad x\to\infty:\ \varepsilon=\frac{1-e^{-c}}{c}$$

### Cruzado, ambos misturados

$$\varepsilon=\left[\frac{1}{1-e^{-x}}+\frac{c}{1-e^{-xc}}-\frac1x\right]^{-1}$$
$$c=1:\ \varepsilon=\left[\frac{2}{1-e^{-x}}-\frac1x\right]^{-1},\quad x\to\infty:\ \varepsilon=\frac1{1+c}$$

### Casco-e-tubos 1–2, casco misturado, TEMA E

$$\Gamma=x\sqrt{1+c^2},\quad \coth(\Gamma/2)=\frac{1+e^{-\Gamma}}{1-e^{-\Gamma}}$$
$$\varepsilon=\frac{2}{1+c+\sqrt{1+c^2}\coth(\Gamma/2)}$$
$$c=1:\ \Gamma=\sqrt2x,\quad \varepsilon=\frac{2}{2+\sqrt2\coth(\Gamma/2)}$$
$$x\to\infty:\ \varepsilon=\frac2{1+c+\sqrt{1+c^2}}$$

Para $c=0$ usar o limite $1-e^{-x}$ nas relações singulares. Para dois passes no casco/4N tubos, consultar p. 76; p. 75 contém curvas para cruzado com ambos não misturados ou um misturado. Para inverter numericamente $\varepsilon=f(x,c)$, buscar raiz física e checar se a efetividade desejada é alcançável; no caso ambos misturados, verificar possível não monotonicidade/mais de uma raiz. A tabela p. 74 imprime CP com $c=1$ como $(1-e^{-NTU})/2$, divergindo da expressão geral e da p. 67; usar $(1-e^{-2NTU})/2$.

## TC-11 — Seleção do método e exemplos de regressão (p. 43–45, 70–72, 77–79)

- Temperaturas terminais conhecidas (ou uma incógnita recuperável pelo balanço): MLDT/F-MLDT é direto para área.
- Duas temperaturas de entrada, área, U e vazões conhecidos, saídas desconhecidas: ε-NTU é direto; MLDT exigiria tentativa e erro.
- Dimensionamento por ε-NTU: balanço → $\dot C_{min}$ → $C^*$ → ε → NTU → área.

**Exemplo 1, p. 43–45:** solução etílica 6,93 kg/s, $c_p=3810$, 66→42 °C; água 6,3 kg/s, $c_p=4187$, entra a 10 °C; 72 tubos de $d_o=0,0254$ m, $U_o=568$. Resultados do slide: $\dot Q=633,7$ kW, água sai ~34 °C; CP MLDT 24,67 K, $A=45,2$ m², $L=7,87$ m; CC MLDT 32 K, $A=34,9$ m², $L=6,07$ m. P. 45 usa subscrito CP na expressão de área CC; aplicar CC.

**Exemplo 2, p. 71–72:** CP, $\dot C_1=10$ kW/K, $\dot C_2=20$ kW/K, entradas 150 e 40 °C; $A=30$ m², $U=500$; $C^*=0,5$, NTU=1,5, ε≈0,596, $\dot Q\approx655,6$ kW; saídas 84,44 e 72,78 °C com arredondamento do slide. P. 72 imprime sinal + para a saída quente, mas o resultado numérico usa −; aplicar TC-02.

**Exemplo 3, p. 77–79:** casco 1/tubos 2; óleo 10 kg/s, $c_p=2118$, 90→60 °C; água 4,082 kg/s, $c_p=4179$, entra a 20 °C; $U=262$. $\dot Q=635400$ W; $T_{2,out}=57,25$ °C; $C_{min}=17058,7$ W/K, $C^*=0,805$, ε=0,532, NTU=1,226, $A=79,8$ m². F-MLDT: MLDT CC=36,4 K; P=0,532, R=0,805; gráfico F≈0,85; A≈78,6 m². Diferença decorre principalmente de leitura/arredondamento do gráfico.

## TC-12 — Perda de carga e potência de bombeamento (p. 80–82)

$$\Delta p=\Delta p_{1-2}+\Delta p_{2-3}-\Delta p_{3-4}$$

Entrada (contração), núcleo e saída (recuperação por expansão); parcelas incluem variação reversível da seção e atrito irreversível.

$$A_cG\,du+A_c\,dp+\tau_s\,dA_s=0,\quad G=\frac{\dot m}{A_c},\quad u=\frac G\rho$$
$$G^2d(1/\rho)+dp+\tau_s\frac{P}{A_c}dz=0$$
$$G^2\int_i^o d(1/\rho)+\int_i^o dp+\frac P{A_c}\int_i^o\tau_s dz=G^2(1/\rho_o-1/\rho_i)+(p_o-p_i)+\frac{fG^2}{2}\left\langle\frac1\rho\right\rangle\frac{LP}{A_c}=0$$
$$\frac{PL}{A_c}=\frac{A_s}{A_c}=\frac{4L}{D_h}$$
$$\Delta p_{2-3}=p_2-p_3=\frac{G^2}{2\rho_i}\left[2\left(\frac{\rho_i}{\rho_o}-1\right)+f\rho_i\left\langle\frac1\rho\right\rangle\frac{4L}{D_h}\right]$$

$\langle1/\rho\rangle$ é média ao longo do núcleo. Se núcleo domina e densidade aproximadamente constante:

$$\Delta p\approx f\frac{G^2}{2\rho}\frac{4L}{D_h},\quad Re=\frac{GD_h}{\mu},\quad \dot W_p=\frac{\dot V\Delta p}{\eta_p}$$

O fator f é do tipo Fanning pela presença de $4L/D_h$; complemento: se dado Darcy, $f_D=4f$. Não usar fator sem saber a convenção. A curva do ventilador cruza a impedância do sistema no ponto de operação, $\Delta p_v=\Delta p_{t.c.}$ (figura p. 82). O PDF não fornece uma correlação numérica universal para f nem coeficientes de entrada/saída.

# 2. CAPÍTULO 5 — CONVECÇÃO NATURAL
Fonte: `conv_nat.pdf`, 20 páginas.

## CN-01 — Mecanismo, estabilidade e escoamentos (p. 2–6)

Diferença de temperatura $(T_s-T_\infty)$ causa variação de densidade (em geral $\partial\rho/\partial T<0$), que na presença da gravidade causa empuxo, movimento do fluido e transferência de energia. Escoamentos não confinados: plumas térmicas, jatos livres e camadas-limite. Confinados: canais e cavidades fechadas.

Estabilidade (p. 3): com x positivo para baixo, no sentido de g, $dT/dx>0$, $d\rho/dx<0$ (fluido mais denso acima do menos denso) pode produzir instabilidade/convecção; $dT/dx<0$, $d\rho/dx>0$ é estratificação estável, condução apenas na configuração ideal. A direção de g é essencial. Pluma aquecida: $T>T_\infty$, $\rho<\rho_\infty$; fluido ambiente inicialmente parado $u_\infty=0$.

## CN-02 — Equações de camada-limite (p. 7–12)

Hipóteses do modelo: escoamento laminar; regime permanente; bidimensional; força de corpo gravitacional; propriedades constantes exceto variação de densidade no empuxo. Para placa vertical, x positivo para cima, y normal à parede, velocidades u e v:

$$\frac{\partial u}{\partial x}+\frac{\partial v}{\partial y}=0$$
$$u\frac{\partial u}{\partial x}+v\frac{\partial u}{\partial y}=-\frac1\rho\frac{\partial p}{\partial x}-g+\nu\left(\frac{\partial^2u}{\partial x^2}+\frac{\partial^2u}{\partial y^2}\right)$$
$$u\frac{\partial v}{\partial x}+v\frac{\partial v}{\partial y}=-\frac1\rho\frac{\partial p}{\partial y}+\nu\left(\frac{\partial^2v}{\partial x^2}+\frac{\partial^2v}{\partial y^2}\right)$$

Na camada-limite, $v\ll u$, $\partial^2u/\partial x^2\ll\partial^2u/\partial y^2$, termos de inércia e viscosidade na equação de y desprezíveis, então:

$$\frac{\partial p}{\partial y}\approx0,\quad \frac{\partial p}{\partial x}=\frac{dp}{dx}=-\rho_\infty g$$
$$-\frac1\rho\frac{\partial p}{\partial x}-g=\frac{\rho_\infty}{\rho}g-g=g\frac{\rho_\infty-\rho}{\rho}=g\frac{\Delta\rho}{\rho}$$
$$u\frac{\partial u}{\partial x}+v\frac{\partial u}{\partial y}=g\frac{\Delta\rho}{\rho}+\nu\frac{\partial^2u}{\partial y^2}$$

Coeficiente de expansão volumétrica térmica (p. 10):

$$\beta\equiv\frac1V\left(\frac{\partial V}{\partial T}\right)_p=-\frac1\rho\left(\frac{\partial\rho}{\partial T}\right)_p$$

Aproximação de Boussinesq (p. 11), linearização de densidade:

$$\beta\approx-\frac1\rho\frac{\rho_\infty-\rho}{T_\infty-T},\quad \rho_\infty-\rho\approx\rho\beta(T-T_\infty)$$
$$\beta=\frac1T\quad\text{gás ideal, T absoluta}$$

Tabela p. 11, líquidos ~25 °C, 1 atm: mercúrio $1,81\times10^{-4}$ K⁻¹; água $2,47\times10^{-4}$; metanol $12,0\times10^{-4}$; óleo de máquina $7,0\times10^{-4}$.

Sistema final acoplado (p. 12):

$$\frac{\partial u}{\partial x}+\frac{\partial v}{\partial y}=0$$
$$u\frac{\partial u}{\partial x}+v\frac{\partial u}{\partial y}=g\beta(T-T_\infty)+\nu\frac{\partial^2u}{\partial y^2}$$
$$u\frac{\partial T}{\partial x}+v\frac{\partial T}{\partial y}=\alpha\frac{\partial^2T}{\partial y^2}$$

Termos na equação de movimento: inércia, empuxo (motriz), viscosidade (dissipação). Condições de contorno representadas nas figuras: parede sem deslizamento $u=v=0$, $T=T_s$; longe da parede $u\to0$, $T\to T_\infty$. Boussinesq requer variação de densidade suficientemente pequena (complemento: $|\beta\Delta T|\ll1$).

## CN-03 — Escalas, Rayleigh, Grashof, Nusselt (p. 13–14, 20)

Para $Pr\gtrsim1$, empuxo e viscosidade dominam inércia: $F_B\sim F_V\gg F_I$.

$$xg\delta\Delta\rho\sim\mu\frac U\delta\quad\Rightarrow\quad U\sim\frac g\nu\frac{\Delta\rho}{\rho}\delta^2$$
$$\rho c_p U\delta_t\frac{\Delta T}{x}\sim k\frac{\Delta T}{\delta_t}\quad\Rightarrow\quad U\sim\frac{\alpha x}{\delta_t^2}$$

Com $\delta\sim\delta_t$:

$$\frac{\alpha x}{\delta_t^2}\sim\frac g\nu\frac{\Delta\rho}{\rho}\delta^2\quad\Rightarrow\quad\frac{x}{\delta_t^4}\sim\frac g{\nu\alpha}\frac{\Delta\rho}{\rho}$$
$$\frac{\Delta\rho}{\rho}\approx\beta\Delta T,\quad\left(\frac x{\delta_t}\right)^4\sim\frac{g\beta\Delta T x^3}{\nu\alpha}=Ra_x$$
$$Ra_\ell=\frac{g\beta|T_s-T_\infty|\ell^3}{\nu\alpha}=Gr_\ell Pr,\qquad Gr_\ell=\frac{g\beta|T_s-T_\infty|\ell^3}{\nu^2}$$
$$Nu_x\sim\frac x{\delta_t}\sim Ra_x^{1/4}$$

Solução indicada no slide para o modelo de escalas:

$$Nu_x=0,5Ra_x^{1/4}$$

$$\bar h=\frac1L\int_0^L h(x)dx,\quad\bar Nu_L=\frac{\bar h L}{k}=\frac43 Nu_{x=L}\quad\text{(para a lei laminar de potência 1/4)}$$
$$\bar Nu_L=CRa_L^n,\quad n=1/4\ (laminar),\quad n=1/3\ (turbulento)$$

Transição da placa vertical: $Ra_{x_c}\approx10^9$. Complemento algébrico: $x_c=[10^9\nu\alpha/(g\beta|\Delta T|)]^{1/3}$. Avaliar propriedades na temperatura de filme.

## CN-04 — Placa vertical isotérmica (p. 14, 18)

Comprimento característico L é a altura ao longo da placa, não a largura ou área/perímetro. Fluido ambiente quiescente.

| Correlação simples (p. 14) | Faixa impressa |
|---|---|
| $\bar Nu_L=0,59Ra_L^{1/4}$ | $10^4$–$10^9$ |
| $\bar Nu_L=0,1Ra_L^{1/3}$ | slide imprime $10^{20}$–$10^{13}$ (intervalo impossível; provável erro tipográfico) |

Não usar a faixa impossível como validade. A transição em $10^9$ é dada na mesma página; para turbulência preferir a correlação de Churchill & Chu, ou explicitar hipótese ao usar a lei simples.

Churchill & Chu para $Ra_L<10^9$ (p. 18):

$$\bar Nu_L=0,68+\frac{0,670Ra_L^{1/4}}{[1+(0,492/Pr)^{9/16}]^{4/9}}$$

Forma de amplo alcance (p. 14; p. 18 a apresenta para $Ra_L>10^9$):

$$\boxed{\bar Nu_L=\left[0,825+\frac{0,387Ra_L^{1/6}}{[1+(0,492/Pr)^{9/16}]^{8/27}}\right]^2}$$

$$\bar h=\frac{k\bar Nu_L}{L}$$

## CN-05 — Placas horizontais (p. 15)

$$\ell=L=\frac{A_s}{P}\quad\text{(área de uma face / perímetro dessa face)}$$

| Orientação | Caso no slide | Correlação | Validade |
|---|---|---|---|
| Face superior de placa fria ($T_s<T_\infty$) | a | $\bar Nu_L=0,27Ra_L^{1/4}$ | $10^5<Ra_L<10^{10}$ |
| Face inferior de placa quente ($T_s>T_\infty$) | d | $\bar Nu_L=0,27Ra_L^{1/4}$ | $10^5<Ra_L<10^{10}$ |
| Face inferior fria ou superior quente | b, c | $\bar Nu_L=0,54Ra_L^{1/4}$ | $10^4<Ra_L<10^7$ |
| Face inferior fria ou superior quente | b, c | $\bar Nu_L=0,15Ra_L^{1/3}$ | $10^7<Ra_L<10^{11}$ |

Para ambas as faces, calcular separadamente. Complemento geométrico: retângulo $L=ab/[2(a+b)]$; quadrado $L=a/4$; disco $L=D/4$. Não extrapolar sem sinalizar. Em limites de faixas, declarar qual ramo adotado.

## CN-06 — Placas inclinadas (p. 16)

Ângulo θ medido a partir da vertical. Componente tangencial $g_x=g\cos\theta$. Recomendação do material: substituir $g$ por $g\cos\theta$ na correlação de placa vertical para $0<\theta<60°$.

Placa quente: face superior intensifica troca (plumas), inferior reduz. Placa fria: superior reduz, inferior intensifica. O slide não fornece correlação independente para intensificação; a projeção de g representa a redução da componente ao longo da placa. Não extrapolar para horizontal ($\cos90°=0$); usar CN-05. Declaração de qual face está sendo modelada é necessária.

## CN-07 — Formulação generalizada (p. 17)

$$\bar Nu_\ell=C\left(\frac{Ra_\ell}{1+C_0/Pr}\right)^n$$

A tabela usa $\Pi_N$ como parâmetro da faixa. O slide não imprime definição isolada de $\Pi_N$; leitura coerente com a expressão é $\Pi_N=Ra_\ell/(1+C_0/Pr)$ (interpretação declarada). Válido para qualquer Pr, temperatura prescrita, propriedades em $T_f$.

| Geometria | $\ell$ | Faixa de $\Pi_N$ | $C_0$ | C | n |
|---|---|---|---:|---:|---|
| Placa ou cilindro vertical | L | $10^4\le\Pi_N\le10^9$ | 0,492 | 0,670 | 1/4 |
| Placa ou cilindro vertical | L | $10^9<\Pi_N\le10^{12}$ | 0,492 | 0,150 | 1/3 |
| Cilindro horizontal | D | $10^4\le\Pi_N\le10^9$ | 0,559 | 0,518 | 1/4 |
| Cilindro horizontal | D | $10^9<\Pi_N\le10^{12}$ | 0,559 | 0,150 | 1/3 |
| Esfera | D | $10^6\le\Pi_N\le10^9$ | 0,469 | 0,589 | 1/4 |
| Esfera | D | $10^9<\Pi_N\le10^{12}$ | 0,469 | 0,150 | 1/3 |

Não combinar constantes da formulação generalizada com as de Churchill & Chu.

## CN-08 — Formas radiais, Churchill & Chu (p. 19)

Cilindro horizontal, $Ra_D<10^9$:

$$\bar Nu_D=0,36+\frac{0,518Ra_D^{1/4}}{[1+(0,559/Pr)^{9/16}]^{4/9}}$$

Cilindro horizontal, $Ra_D>10^9$, **transcrição literal do slide**:

$$\bar Nu_D=\left\{0,60+0,387\left[\frac{Ra_D}{[1+(0,559/Pr)^{9/16}]^{16/9}}\right]^{1/6}\right\}^2$$

O expoente interno 16/9 aparece assim no PDF. Não confundir com a expressão da placa vertical ou assumir correção não fornecida. Se o enunciado indicar versão diferente, registrar a divergência e usar a versão exigida.

Esfera, $Ra_D<10^{12}$, **transcrição do slide**:

$$\bar Nu_D=2+\frac{0,589Ra_D^{1/4}}{[1+(0,492/Pr)^{9/16}]^{4/9}}$$

A constante 0,492 está impressa na p. 19, enquanto 0,469 é da tabela generalizada p. 17. Usar o conjunto completo de uma única correlação, sem misturar. Propriedades em $T_f$.

## CN-09 — Convecção mista (p. 20)

$$\frac{F_B}{F_I}\sim\frac{F_B}{F_V}\frac{F_V}{F_I},\quad\frac{F_V}{F_I}\sim\frac\nu{U\ell}=\frac1{Re}$$
$$\frac{F_B}{F_V}\sim\frac{g\beta\Delta T\ell^2}{\nu U}=\frac{Gr}{Re},\quad Gr=\frac{g\beta\Delta T\ell^3}{\nu^2}=\frac{Ra}{Pr}$$
$$\frac{F_B}{F_I}\sim\frac{Gr}{Re^2}$$

| Critério | Regime | Relação |
|---|---|---|
| $Gr/Re^2\ll1$ | forçada dominante | $\bar Nu=f(Re,Pr)$ |
| $Gr/Re^2\gg1$ | natural dominante | $\bar Nu=f(Gr,Pr)$ |
| $Gr/Re^2\sim1$ | mista | $\bar Nu=f(Re,Gr,Pr)$ |

$$\bar Nu^n=\bar Nu_{CF}^n+\bar Nu_{CN}^n,\quad n\approx3$$

O PDF apresenta soma, não fornece regra específica para escoamento oposto. Não aplicar automaticamente a soma a toda orientação sem declarar hipótese. O capítulo não dá as correlações de convecção forçada necessárias para obter $\bar Nu_{CF}$; se faltarem, declarar necessidade de dado adicional.

# 3. CAPÍTULO 6 — TRANSFERÊNCIA DE CALOR LATENTE
Fonte: `latente.pdf`, 35 páginas.

## LT-01 — Classificação, condições físicas e CTC (p. 2–6)

Calor latente associado à mudança de fase. Faixas típicas de h (p. 2, W/m² K): convecção natural gases 2–25; líquidos 10–1000; forçada gases 25–250; líquidos 50–20000; ebulição/condensação 2500–100000. São ordens de grandeza, não coeficientes para substituir cálculos.

Condensação em gotas: baixa molhabilidade, superfície hidrofóbica, h elevado; revestimentos precisam ser renovados. Condensação em película: filme contínuo em superfície fria hidrofílica, caso industrial de foco. $T_s<T_{sat}$, liberação de $h_{lv}$ na interface, filme $\delta(x)$ cresce com x, não deslizamento na parede, continuidade das tensões cisalhantes na interface real. No modelo ideal, vapor estagnado, cisalhamento interfacial desprezado; $u$ máximo na interface e T linear no filme.

## LT-02 — Reynolds de condensado (p. 7)

$$Re=\frac{\rho_LV_LD_h}{\mu_L}=\frac{\rho_LV_L4A_c}{p\mu_L}=\frac{4\rho_LV_L\delta}{\mu_L}=\frac{4\dot m}{p\mu_L}=\frac{4\Gamma}{\mu_L}$$
$$D_h=4A_c/p=4\delta,\quad\Gamma=\dot m/p$$

$V_L$ velocidade média, $\delta$ espessura, p perímetro molhado, $A_c$ seção transversal do fluxo líquido. Figuras da p. 7: placa vertical de largura b: $p=b$, $A_c=b\delta$; cilindro vertical: $p=\pi D$, $A_c\approx\pi D\delta$; cilindro horizontal de comprimento L, drenagem pelos dois lados: $p=2L$, $A_c=2L\delta$. O PDF não traz tabela geral de transição laminar/ondulado/turbulento; não inventar faixa universal.

## LT-03 — Modelo de Nusselt para placa plana vertical (p. 8–13)

Hipóteses: (1) escoamento laminar; (2) propriedades constantes, sub-resfriamento desprezível; (3) inércia/aceleração desprezível; (4) vapor estagnado; (5) interface lisa sem atrito; (6) condução pura no filme, sem advecção de calor, perfil T linear. Placa comprimento L, largura b, x para baixo, y normal à parede. $\Delta T_c=T_{sat}-T_s>0$. Subscritos L e G significam líquido e gás/vapor, não comprimento.

Balanço de forças (p. 9):

$$dF_L+dF_I-(\rho_L-\rho_G)g\,dV=d(\dot m_Lu_L)$$

Desprezando força de interface e aceleração:

$$ (\delta-y)dx(\rho_L-\rho_G)g=\mu_Ldx\frac{du}{dy}$$

Integrar, com $u(0)=0$ e $du/dy|_{y=\delta}=0$:

$$u(y)=\frac{g(\rho_L-\rho_G)\delta^2}{\mu_L}\left[\frac y\delta-\frac12\left(\frac y\delta\right)^2\right]$$
$$\Gamma(x)\equiv\frac{\dot m(x)}b=\int_0^{\delta(x)}\rho_Lu(y)dy=\frac{g\rho_L(\rho_L-\rho_G)\delta^3}{3\mu_L}\tag{1}$$

Balanço de energia (p. 11):

$$dq=h_{lv}d\dot m,\quad d\dot m=b\,d\Gamma,\quad dq=q''dA=q''b\,dx$$
$$q''=h(T_{sat}-T_s),\quad\frac{d\Gamma}{dx}=\frac{h(T_{sat}-T_s)}{h_{lv}}$$
$$h=\frac{k_L}{\delta}\quad\Rightarrow\quad\frac{d\Gamma}{dx}=\frac{k_L(T_{sat}-T_s)}{\delta h_{lv}}\tag{2}$$

Combinando (1) e (2), e $\delta(0)=0$:

$$\delta(x)=\left[\frac{4k_L\mu_L(T_{sat}-T_s)x}{g\rho_L(\rho_L-\rho_G)h_{lv}}\right]^{1/4}\tag{3}$$
$$h(x)=\frac{k_L}{\delta(x)}=\left[\frac{k_L^3\rho_L(\rho_L-\rho_G)g h_{lv}}{4\mu_L(T_{sat}-T_s)x}\right]^{1/4}\tag{4}$$
$$\bar h=\frac1L\int_0^Lh(x)dx=\frac43h(x=L)$$
$$\boxed{\bar h=0,943\left[\frac{k_L^3\rho_L(\rho_L-\rho_G)g h_{lv}}{\mu_L(T_{sat}-T_s)L}\right]^{1/4}}\tag{5}$$

Avaliação de propriedades: líquido em $T_f=(T_s+T_{sat})/2$, exceto $h_{lv}$ e $\rho_G$ em $T_{sat}$ (p. 13). Produção de condensado no fundo:

$$\int_0^{\Gamma_L}d\Gamma=\int_0^L\frac{k_L(T_{sat}-T_s)}{\delta h_{lv}}dx$$
$$\Gamma_L=\frac{\bar h(T_{sat}-T_s)L}{h_{lv}},\quad\dot m_L=b\Gamma_L,\quad\dot Q=\bar h bL(T_{sat}-T_s)=\dot m_Lh_{lv}$$

Complemento por integração do perfil: $u_{max}=g(\rho_L-\rho_G)\delta^2/(2\mu_L)$, $V_L=g(\rho_L-\rho_G)\delta^2/(3\mu_L)$, $Re_L=4\Gamma_L/\mu_L$. Usar área total real de condensação; se há duas faces iguais, dobrar área e vazão total, mantendo Γ de cada face.

## LT-04 — Placa inclinada e correções de energia (p. 14–15)

Placa inclinada de ângulo θ com a vertical, θ<60°: substituir g por $g\cos\theta$ na expressão de Nusselt. Mantidas demais hipóteses, $\bar h_\theta=\bar h_{vertical}(\cos\theta)^{1/4}$ (derivação).

Vapor superaquecido ($T_G>T_{sat}$):

$$\bar h=\bar h_{Nu}\left[1+\frac{c_{pG}(T_G-T_{sat})}{h_{lv}}\right]^{1/4}$$

$\bar h_{Nu}$ é coeficiente com vapor saturado. Sub-resfriamento do condensado: substituir $h_{lv}$ pelo calor latente corrigido:

$$h_{lv}^*=h_{lv}\left[1+C\frac{c_{pL}(T_{sat}-T_s)}{h_{lv}}\right],\qquad C=0,683-\frac{0,228}{Pr_L}$$

O slide apresenta as correções separadamente; não presumir combinação ou substituir indiscriminadamente $h_{lv}$ no balanço de massa. Se houver calor sensível significativo, usar balanço de entalpias completo para vazão de condensado e explicitar modelagem.

## LT-05 — Cilindro e esfera, condensação laminar (p. 16)

Mesmas hipóteses de Nusselt; D diâmetro exterior:

$$\bar h=C\left[\frac{k_L^3\rho_L(\rho_L-\rho_G)g h_{lv}^*}{\mu_L(T_{sat}-T_s)D}\right]^{1/4}$$

C=0,826 para esfera e C=0,729 para cilindro. Para caso sem correção, $h_{lv}^*=h_{lv}$. Figura do cilindro inclinado: ângulo θ medido da horizontal, usar $g\cos\theta$, condição $L/D>1,8\tan\theta$. O slide também imprime $4\Gamma_L/(\mu_L\cos\theta)>3200$ como condição junto ao cilindro; a desigualdade é reproduzida como está, embora a associação a modelo laminar seja duvidosa. Não interpretar como limite geral de regime; verificar com material complementar se for decisiva.

## LT-06 — Fileira vertical de tubos, inundação por condensado (p. 17–18)

Idealização: vapor estagnado; filme laminar contínuo sem respingos; despreza transferência de calor e ganho de quantidade de movimento entre tubos; mesma $(T_{sat}-T_s)$ para todos. $\bar h_1$ coeficiente do primeiro tubo isolado, N número de tubos verticalmente sobrepostos.

$$\bar h_M=\bar h_1N^{-1/4},\qquad\frac{\bar h_N}{\bar h_1}=N^{3/4}-(N-1)^{3/4}$$

Condição mais próxima da real (drenagem em lâminas/gotas e respingos), menos conservativa:

$$\bar h_M=\bar h_1N^{-1/6},\qquad\frac{\bar h_N}{\bar h_1}=N^{5/6}-(N-1)^{5/6}$$

P. 18 imprime h sem índice no primeiro membro da expressão média; pela relação com o tubo N, interpreta-se como $\bar h_1$. Para tubos idênticos de comprimento L: $\dot Q_{fileira}=\bar h_M N\pi DL(T_{sat}-T_s)$ (complemento). Não tomar N como total de tubos distribuídos lado a lado sem avaliar número de tubos por coluna vertical.

## LT-07 — Evaporação, ebulição e regimes (p. 19–26, 32, 34)

Evaporação: mudança L–V em interface líquido-vapor existente, quando pressão do vapor é menor que a pressão de saturação na temperatura do líquido. Ebulição: formação de novas interfaces L–V por nucleação junto à superfície sólida superaquecida. Nucleação é localizada e depende de energia de excesso/supersaturação.

Pool boiling: líquido se move devido às bolhas; foco do capítulo. Flow boiling: escoamento independente por bombeamento ou circulação natural. Não usar Rohsenow de vaso automaticamente para escoamento interno bifásico.

$$\Delta T_e=T_s-T_{sat}>0,\quad q''=h\Delta T_e$$

Curva de Nukiyama, fluxo controlado: convecção natural → ebulição nucleada (bolhas isoladas, depois jatos/colunas) → fluxo crítico $q''_{max}$ → transição → fluxo mínimo $q''_{min}$ (Leidenfrost) → película de vapor. Histerese: aumento abrupto de temperatura após CHF e queda abrupta ao baixar do mínimo. P. 32/34, curva ilustrativa da água: início da nucleação por volta de 5 K; ponto crítico ~30 K, Leidenfrost ~120 K; valores gráficos indicativos, não universais.

Crescimento de bolha, p. 26:

$$R(t)\propto t\quad\text{inicial};\qquad R(t)\propto\sqrt t\quad\text{final}$$

A bolha absorve calor principalmente da microcamada, se desprende, líquido frio ocupa seu lugar e reinicia o ciclo. CTC depende de sítios ativos, frequência de bolhas, fluido e superfície.

## LT-08 — Rohsenow (1952), ebulição nucleada em vaso (p. 27–31)

Analogia com convecção forçada turbulenta monofásica. As bolhas induzem movimento de líquido. A é constante da analogia nas expressões de Nu; nas expressões de fluxo A é área (notação sobreposta nos slides).

$$Nu_B=\frac{hL_B}{k_L}=A Re_B^{1-r}Pr_L^{1-s}\tag{1}$$
$$Re_B=\frac{\rho_GU_BL_B}{\mu_L},\quad L_B\equiv C_b\theta\sqrt{\frac\sigma{g(\rho_L-\rho_G)}}$$
$$U_B=\frac{\dot m_G}{A\rho_G}=\frac{q/h_{lv}}{A\rho_G}=\frac{q''}{\rho_Gh_{lv}}$$

Reynolds reduzido conforme destaque do slide (p. 28, fatores de geometria absorvidos na constante):

$$Re_B=\frac{q''}{h_{lv}\mu_L}\sqrt{\frac\sigma{g(\rho_L-\rho_G)}}$$
$$\frac h{\rho_GU_Bc_{pL}}=\frac{Nu_B}{Re_BPr_L}=A Re_B^{-r}Pr_L^{-s}$$
$$\frac{\rho_GU_Bc_{pL}}h=\frac1A Re_B^rPr_L^s,\quad\frac1h=\frac{T_s-T_{sat}}{q''}$$

Relação empírica final (p. 30):

$$\boxed{\frac{c_{pL}(T_s-T_{sat})}{h_{lv}}=C_{sf}\left[\frac{q_s''}{\mu_Lh_{lv}}\sqrt{\frac\sigma{g(\rho_L-\rho_G)}}\right]^r\left(\frac{c_{pL}\mu_L}{k_L}\right)^s}$$

A página imprime $C_{sf}=\sqrt2 C_b\theta/A$ (fator empírico). Usar valor tabelado da combinação fluido-superfície, não reconstruir Csf pela analogia sem dados.

$$\boxed{q_s''=\frac{\mu_Lh_{lv}}{C_{sf}^{1/r}}\sqrt{\frac{g(\rho_L-\rho_G)}\sigma}\ Pr_L^{-s/r}\left[\frac{c_{pL}(T_s-T_{sat})}{h_{lv}}\right]^{1/r}}$$

Rohsenow observou $r\approx1/3$ independente da superfície (p. 31). Forma equivalente, se r=1/3:

$$q_s''=\mu_Lh_{lv}\sqrt{\frac{g(\rho_L-\rho_G)}\sigma}\left[\frac{c_{pL}\Delta T_e}{C_{sf}h_{lv}Pr_L^s}\right]^3$$

Complementos por inversão algébrica:

$$\Delta T_e=\frac{C_{sf}h_{lv}Pr_L^s}{c_{pL}}\left[\frac{q_s''}{\mu_Lh_{lv}}\sqrt{\frac\sigma{g(\rho_L-\rho_G)}}\right]^r,\quad T_s=T_{sat}+\Delta T_e,\quad h=q_s''/\Delta T_e$$

Usar propriedades das fases em saturação à pressão de operação, salvo instrução diferente (convenção operacional explicitada). Verificar se regime permanece nucleado e fluxo calculado não excede CHF. Não usar para transição ou película.

### Tabela Csf e s — transcrição da tabela 10-3, p. 31

Na tabela original o expoente aparece como n (corresponde a s nesta referência, não ao expoente de Rayleigh).

| Fluido — superfície | $C_{sf}$ | s |
|---|---:|---:|
| Água — cobre polido | 0,0130 | 1,0 |
| Água — cobre riscado | 0,0068 | 1,0 |
| Água — aço inox polido mecanicamente | 0,0130 | 1,0 |
| Água — aço inox retificado e polido | 0,0060 | 1,0 |
| Água — aço inox com cavidades de Teflon | 0,0058 | 1,0 |
| Água — aço inox atacado quimicamente | 0,0130 | 1,0 |
| Água — latão | 0,0060 | 1,0 |
| Água — níquel | 0,0060 | 1,0 |
| Água — platina | 0,0130 | 1,0 |
| n-pentano — cobre polido | 0,0154 | 1,7 |
| n-pentano — cromo | 0,0150 | 1,7 |
| Benzeno — cromo | 0,1010 | 1,7 |
| Álcool etílico — cromo | 0,0027 | 1,7 |
| Tetracloreto de carbono — cobre | 0,0130 | 1,7 |
| Isopropanol — cobre | 0,0025 | 1,7 |

## LT-09 — Fluxo crítico (Zuber, 1959), p. 32–33

Crise de ebulição: vapor cobre superfície, impede contato líquido-parede e pode elevar drasticamente a temperatura da parede. Correlação com coeficiente geométrico Ccr:

$$\boxed{q''_{max}=C_{cr}\rho_G^{1/2}h_{lv}[\sigma(\rho_L-\rho_G)g]^{1/4}}$$
$$L^*=L\sqrt{\frac{g(\rho_L-\rho_G)}\sigma},\qquad K_1=\frac\sigma{g(\rho_L-\rho_G)A_{heater}}$$

### Tabela 10-4 (p. 33)

| Geometria | $C_{cr}$ | L característico | Faixa |
|---|---|---|---|
| Aquecedor plano horizontal grande | 0,149 | largura ou diâmetro | $L^*>27$ |
| Aquecedor plano horizontal pequeno | $18,9K_1$ | largura ou diâmetro | $9<L^*<20$ |
| Cilindro horizontal grande | 0,12 | raio | $L^*>1,2$ |
| Cilindro horizontal pequeno | $0,12(L^*)^{-0,25}$ | raio | $0,15<L^*<1,2$ |
| Esfera grande | 0,11 | raio | $L^*>4,26$ |
| Esfera pequena | $0,227(L^*)^{-0,5}$ | raio | $0,15<L^*<4,26$ |

$A_{heater}$ é área do aquecedor. Não preencher a lacuna entre 20 e 27 da placa horizontal com interpolação não autorizada. Usar as constantes do material (não substituir 0,149 por outro valor padrão sem justificar). Complemento: $\dot Q_{max}=A q''_{max}$; verificar $q''_{oper}<q''_{max}$ para regime nucleado; margem de projeto se especificada. Temperatura no CHF pode ser estimada invertendo Rohsenow com $q''=q''_{max}$ sob as hipóteses dessa correlação.

## LT-10 — Fluxo mínimo de Leidenfrost (p. 34–35)

Fluxo mínimo marca recuperação de contato líquido-superfície ao diminuir calor. Placa plana:

$$\boxed{q''_{min,p}=0,09\rho_Gh_{lv}\left[\frac{\sigma g(\rho_L-\rho_G)}{(\rho_L+\rho_G)^2}\right]^{1/4}}$$

Cilindro horizontal:

$$L_B=\sqrt{\frac\sigma{g(\rho_L-\rho_G)}}$$
$$\boxed{q''_{min,c}=0,515\left\{\frac{18}{(R/L_B)^2[(R/L_B)^2+1]}\right\}^{1/4}q''_{min,p}}$$

R é raio do cilindro; $L_B$ aqui é comprimento capilar sem $C_b\theta$ (não confundir com definição p. 28). As equações fornecem fluxos-limite, não uma curva contínua de h na ebulição em película; PDF não inclui correlação de Bromley para esse regime. Não inventar temperatura de Leidenfrost a partir de q mínimo sem outra relação.

# 4. Roteiros de cálculo por tipo de problema

Complemento operacional: sequências derivadas das equações anteriores, não novas correlações empíricas dos PDFs.

| Problema | Sequência | Seções |
|---|---|---|
| Trocador: área/comprimento | balanço → temperatura faltante → U e área de referência → diferenças terminais → MLDT → F se necessário → A → L | TC-02, 04, 05, 07 |
| Trocador: potência e temperaturas de saída | capacidades → Cmin/Cmax → NTU → ε da geometria → potência → saídas | TC-08–10 |
| Trocador: U com incrustação e aletas | áreas → eficiência de superfície → resistências individuais → soma → U de referência | TC-04 |
| Trocador: ventilador/bomba | seção livre → G → Dh → Re → f consistente → Δp → potência | TC-01, 12 |
| Placa vertical natural | filme → propriedades → altura L → Ra/Pr → correlação → Nu → h → Q | CN-02–04 |
| Placa horizontal natural | identificar face e sinal de Ts−T∞ → área/perímetro → Ra → correlação por estabilidade → h → Q | CN-05 |
| Placa inclinada natural | ângulo da vertical → face → componente g → Ra → Nu → h | CN-06 |
| Cilindro/esfera natural | filme → D → Ra/Pr → família de correlações → Nu → h → área → Q | CN-07–08 |
| Natural e forçada | Re, Gr → Gr/Re² → regime → Nu dominante ou combinação | CN-09 |
| Condensação em placa | Tsat−Ts → filme → propriedades → h_lv ou correção → δ(x), h(x), h médio → Q, Γ, vazão e Re | LT-02–04 |
| Condensação radial/fileira | D, geometria e ângulo → C → h de tubo isolado → inundação N → h médio → Q | LT-05–06 |
| Ebulição nucleada | pressão/Tsat → propriedades → Csf e s da superfície → Rohsenow direto/inverso → h, Q → verificar CHF | LT-07–09 |
| Crise de ebulição | geometria → L* e Ccr → fluxo crítico → potência crítica | LT-09 |
| Leidenfrost | propriedades → placa ou cilindro → comprimento capilar → fluxo mínimo → potência mínima | LT-10 |

## 4.1 Validação antes da resposta final

- Trocador: verificar igualdade de calor cedido e recebido, $0\le C^*\le1$, $0\le\varepsilon\le1$, $NTU\ge0$, $\dot Q\le\dot Q_{max}$, $0<F\le1$ e limites próprios de cada arranjo.
- Convecção natural: Rayleigh não negativo para as correlações de módulo; sentido do fluxo pelo sinal de $T_s-T_\infty$; unidades de β, μ, ν e α; temperatura absoluta no β de gás ideal; comprimento da geometria correta.
- Condensação: $T_s<T_{sat}$, $\rho_L>\rho_G$, $h>0$, $\delta>0$ para $x>0$; $\bar h=(4/3)h(L)$ no modelo de Nusselt; condensado acumulado cresce com x.
- Ebulição: $T_s>T_{sat}$; $\sigma>0$; líquido e vapor da mesma condição de saturação; constante Csf da superfície exata; raio (não diâmetro) no CHF de cilindro/esfera; não extrapolar Rohsenow acima da crise.
- Em todos os casos: explicar dados ausentes, domínio de validade e correções; escrever resposta final com unidade e número de algarismos coerente.

## 4.2 Exemplo de apresentação matemática ao agente

Para uma placa vertical com $T_s,T_\infty,L,A,k,\nu,\alpha,\beta$ disponíveis:

1. $T_f=(T_s+T_\infty)/2$.
2. $\Delta T=|T_s-T_\infty|$.
3. $Pr=\nu/\alpha$.
4. $Ra_L=g\beta\Delta T L^3/(\nu\alpha)$.
5. Verificar regime e escolher correlação da seção CN-04, citar a página.
6. Substituir os valores de Ra e Pr, calcular $\bar Nu_L$.
7. $\bar h=k\bar Nu_L/L$.
8. $\dot Q=\bar h A\Delta T$.
9. Checar unidade W, direção do calor e área. Se for solicitado fluxo, $q''=\dot Q/A$.

Na resolução real, apresentar valores em cada etapa e detalhar álgebra ou cálculo numérico sempre que necessário. Este exemplo não limita o número de etapas.

# 5. Auditoria das fontes e limitações

| Arquivo | Páginas | Cobertura nesta referência |
|---|---:|---|
| `trocadores.pdf` | 1–82 | classificação, compacidade, balanço, U, MLDT/F, ε–NTU, tabela de arranjos, exemplos e perda de carga |
| `conv_nat.pdf` | 1–20 | estabilidade, hipóteses, equações diferenciais, escalas, Rayleigh/Grashof, placas, formas radiais, generalização e convecção mista |
| `latente.pdf` | 1–35 | condensação, hipóteses, derivação de Nusselt, correções, fileiras, ebulição, Rohsenow, tabela fluido-superfície, CHF e Leidenfrost |

## 5.1 Divergências e pontos que exigem atenção

- Trocadores p. 45: subscrito CP na fórmula da área CC; utilizar CC.
- Trocadores p. 65: expressão da razão de diferenças terminais de CC não corresponde ao balanço; usar TC-08 e p. 66.
- Trocadores p. 72: sinal positivo impresso na saída quente; usar sinal negativo.
- Trocadores p. 74: limite CP com C*=1 diverge da p. 67; usar o limite da equação geral.
- Convecção natural p. 14: intervalo de Rayleigh turbulento impresso com limites invertidos/incompatíveis; usar correlação válida ou registrar hipótese.
- Convecção natural p. 17: significado do parâmetro Π_N interpretado a partir da equação, não explicitado separadamente.
- Convecção natural p. 19: forma radial turbulenta e constante da esfera preservadas como impressas; não houve validação por fontes externas.
- Latente p. 16: condição com Reynolds >3200 junto à expressão laminar exige confirmação; preservada e sinalizada.
- Latente p. 18: h de referência sem índice interpretado como h do primeiro tubo.
- Latente p. 28–30: fatores geométricos são absorvidos na constante da correlação final; usar Csf tabelado e a equação final, não a analogia isolada.

## 5.2 O que o agente não deve presumir

Os gráficos de F (trocadores p. 53–56) e ε–NTU (p. 68, 75–76) estão descritos, mas suas curvas não foram integralmente digitalizadas em pares de pontos. A tabela analítica da p. 74 foi transcrita. Quando uma configuração exigir exclusivamente um gráfico, solicitar o gráfico/valor ou usar modelo explicitamente autorizado. Os PDFs também não contêm tabelas completas de propriedades de água, ar, óleos ou refrigerantes, correlações gerais de convecção forçada, eficiência individual de todas as aletas, atrito para todos os canais ou h de ebulição em película. Nenhum desses dados deve ser fabricado. Os diagramas ilustrativos não constituem novos limites quantitativos universais.

**Fim da referência.**
