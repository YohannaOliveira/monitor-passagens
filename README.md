# Monitor de Passagens Aéreas Baratas

Script em Python que procura passagens **de ida e volta** saindo de São Paulo (GRU e CGH) para as capitais brasileiras e avisa pelo **WhatsApp** quando encontra uma tarifa **confirmada** igual ou abaixo do preço máximo (padrão: R$ 1.000 por pessoa, ida e volta).

Ele roda sozinho: faz uma busca ao iniciar e repete 24 horas depois do fim de cada rodada.

## Sumário

1. [Como funciona](#1-como-funciona)
2. [Fontes de dados e suas limitações](#2-fontes-de-dados-e-suas-limitações)
3. [Instalação](#3-instalação)
4. [Credenciais](#4-credenciais)
5. [Configuração (.env)](#5-configuração-env)
6. [Executando](#6-executando)
7. [Mantendo rodando continuamente](#7-mantendo-rodando-continuamente)
8. [Mensagem recebida](#8-mensagem-recebida)
9. [Custos e limites das APIs](#9-custos-e-limites-das-apis)
10. [Testes](#10-testes)
11. [Estrutura do projeto](#11-estrutura-do-projeto)
12. [Como adicionar uma nova fonte ou notificador](#12-como-adicionar-uma-nova-fonte-ou-notificador)
13. [Segurança](#13-segurança)
14. [Solução de problemas](#14-solução-de-problemas)
15. [Pendências conhecidas](#15-pendências-conhecidas)

---

## 1. Como funciona

Cada rodada tem quatro fases:

1. **Descoberta (Travelpayouts, gratuita).** Consulta preços em *cache* para cada rota (origem × destino) e guarda as combinações de datas válidas cujo preço em cache está até `MAX_PRICE_BRL × DISCOVERY_MARGIN`. Esses preços são **estimativas**: nunca geram alerta.
2. **Amostragem rotativa.** O cache costuma estar vazio para datas distantes. Por isso, o que sobra do orçamento da rodada (`MAX_VALIDATIONS_PER_RUN`) é preenchido com combinações escolhidas em rodízio. Uma posição gravada no banco garante que cada rodada confira rotas e datas diferentes: todas as rotas são visitadas antes de repetir, e o par de datas avança a cada volta completa.
3. **Validação (Ignav, tempo real).** Cada combinação escolhida é consultada na API do Ignav, que devolve o preço total de ida e volta. Só ofertas **em BRL** e **dentro do limite** seguem adiante.
4. **Alerta (CallMeBot).** Se a oferta for inédita, ou se o preço caiu em relação ao último alerta daquela mesma oferta, a mensagem é enviada. Só depois do envio bem-sucedido a oferta é gravada como notificada.

Regras importantes:

- Duração da viagem entre `MIN_DAYS` (4) e `MAX_DAYS` (10); ida entre `DEPART_START` e `DEPART_END`; volta até `RETURN_BY`.
- Uma oferta é identificada por **origem + destino + data de ida + data de volta**.
- Preços em moedas diferentes de BRL são descartados. Nunca são tratados como reais.
- Se um destino falhar, a rodada continua com os demais.

---

## 2. Fontes de dados e suas limitações

| Fonte | Papel | Tipo de preço | Observações |
|---|---|---|---|
| **Ignav** | Validação | Tempo real (confirmado) | Primeiras 1.000 requisições grátis; depois US$ 2 por 1.000. Testado com rotas domésticas em BRL. |
| **Travelpayouts / Aviasales** | Descoberta | Cache (estimado) | Gratuita para parceiros. O cache só cobre datas relativamente próximas; para maio/2027 estava vazio em outubro/2026. |
| **SerpApi (Google Flights)** | Validação alternativa | Tempo real | Implementada, mas não testada com sucesso (a chave foi rejeitada). Usada só com `VALIDATION_PROVIDER=serpapi`. |
| **CallMeBot** | WhatsApp | , | Envia só para o número que o ativou. Serviço de terceiros, sem garantia de disponibilidade. |

Por que não há Amadeus, GOL, LATAM ou Decolar:

- A **Amadeus Self-Service foi desativada em 17/07/2026**; só resta a versão Enterprise, por contrato.
- Não há API pública de tarifas das companhias nem da Decolar, e o projeto **não faz scraping**.
- O **link** da mensagem é uma pesquisa no Google Flights montada com a rota e as datas da oferta. Não é um link de compra.

Mesmo um preço "confirmado" pode mudar ou sumir. Confira sempre antes de comprar.

---

## 3. Instalação

Requisitos: Python 3.10 ou superior (testado com 3.14).

```powershell
cd monitor-passagens
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

No Linux/macOS:

```bash
cd monitor-passagens
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Se o PowerShell bloquear a ativação do ambiente virtual, rode uma vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

---

## 4. Credenciais

Você precisa de três credenciais. Preencha-as direto no `.env`, nunca no código, no chat ou em commits.

### Ignav (validação)
1. Crie uma conta em <https://ignav.com>.
2. Copie a chave da API para `IGNAV_API_KEY`.

### Travelpayouts (descoberta)
1. Crie uma conta de parceiro em <https://www.travelpayouts.com>.
2. Em *Perfil → API token*, copie o token para `TRAVELPAYOUTS_TOKEN`.

### CallMeBot (WhatsApp)
1. Siga o passo a passo oficial: <https://www.callmebot.com/blog/free-api-whatsapp-messages/>. Em resumo: salve o contato do bot no celular e envie a frase de ativação indicada na página.
2. O bot responde com uma *apikey*. Coloque-a em `CALLMEBOT_APIKEY`.
3. Coloque seu número, com DDI, em `CALLMEBOT_PHONE` (ex.: `+5511999999999`), o mesmo que fez a ativação.

### SerpApi (opcional)
Só é necessária se você usar `VALIDATION_PROVIDER=serpapi`. A chave fica em <https://serpapi.com/manage-api-key> (campo "Your Private API Key").

---

## 5. Configuração (.env)

Todas as opções vêm de variáveis de ambiente ou do arquivo `.env`. O arquivo `.env.example` lista todas, sem valores reais.

| Variável | Padrão | Descrição |
|---|---|---|
| `IGNAV_API_KEY` | , | Chave do Ignav (obrigatória com `VALIDATION_PROVIDER=ignav`). |
| `TRAVELPAYOUTS_TOKEN` | , | Token do Travelpayouts (obrigatório). |
| `SERPAPI_API_KEY` | , | Chave do SerpApi (só com `VALIDATION_PROVIDER=serpapi`). |
| `CALLMEBOT_PHONE` | , | Seu número com DDI. Obrigatório quando `DRY_RUN=false`. |
| `CALLMEBOT_APIKEY` | , | Chave de ativação do CallMeBot. Obrigatória quando `DRY_RUN=false`. |
| `VALIDATION_PROVIDER` | `ignav` | `ignav` ou `serpapi`. |
| `ORIGINS` | `GRU,CGH` | Aeroportos de origem (códigos IATA separados por vírgula). |
| `DESTINATIONS` | 23 capitais | Todas as capitais, exceto Vitória, São Paulo, Rio de Janeiro e Maceió. Belo Horizonte usa CNF (Confins). |
| `DEPART_START` / `DEPART_END` | `2027-05-03` / `2027-05-12` | Janela de datas de ida (AAAA-MM-DD). |
| `RETURN_BY` | `2027-05-16` | Data limite da volta. |
| `MIN_DAYS` / `MAX_DAYS` | `4` / `10` | Duração mínima e máxima da viagem, em dias. |
| `MAX_PRICE_BRL` | `1000` | Preço máximo por pessoa (ida e volta), em reais. |
| `DISCOVERY_MARGIN` | `1.3` | Margem para aceitar candidatas do cache (preço em cache ≤ máximo × margem). |
| `MAX_VALIDATIONS_PER_RUN` | `10` | Quantas buscas em tempo real por rodada. Veja [custos](#9-custos-e-limites-das-apis). |
| `VALIDATION_MONTHLY_LIMIT` | `900` | Teto de buscas em tempo real por mês, contado no banco. |
| `MIN_NOTIFY_DROP_BRL` | `1` | Queda mínima (R$) para reenviar o alerta da mesma oferta. |
| `INTERVAL_HOURS` | `24` | Espera entre rodadas, contada a partir do **fim** da rodada anterior. |
| `DB_PATH` | `monitor.db` | Arquivo SQLite com o histórico. |
| `DRY_RUN` | `false` no seu `.env`; `true` no exemplo | `true` não envia WhatsApp: só registra no log o que enviaria. |
| `TRAVELPAYOUTS_BASE_URL`, `IGNAV_BASE_URL`, `SERPAPI_BASE_URL`, `CALLMEBOT_URL` | endereços oficiais | Só altere se a API mudar. |

A configuração é validada ao iniciar. Se algo estiver errado (data invertida, código IATA inválido, chave ausente), o programa mostra a mensagem e encerra, sem fazer nenhuma chamada.

---

## 6. Executando

Comece **sempre** com um teste sem envio:

```powershell
# no .env: DRY_RUN=true
python main.py --once
```

`--once` faz uma única rodada e encerra. Você verá no log quantas candidatas vieram do cache, quantas buscas foram feitas e, se houver oferta, o texto exato que seria enviado.

Quando estiver satisfeito:

```powershell
# no .env: DRY_RUN=false
python main.py
```

Sem `--once`, o programa roda para sempre: busca, espera `INTERVAL_HOURS` horas, busca de novo. `Ctrl+C` encerra.

Para testar só o WhatsApp, sem buscar passagens:

```powershell
python -c "from config import load_config; from services.notifiers.callmebot import CallMeBotNotifier as N; c=load_config(); N(c.callmebot_url,c.callmebot_phone,c.callmebot_apikey).send('Teste do monitor')"
```

---

## 7. Mantendo rodando continuamente

O programa precisa ficar ligado. Opções, da mais simples à mais robusta:

### 7.1 Deixar um terminal aberto (teste)
Simples, mas para se o computador dormir ou reiniciar. Desative a suspensão do Windows enquanto testa.

### 7.2 Agendador de Tarefas do Windows (uso pessoal)

Cria uma tarefa que inicia o monitor quando você entra no Windows. Ajuste os caminhos.

```powershell
$dir = "C:\caminho\para\monitor-passagens"
$py  = "$dir\.venv\Scripts\python.exe"
$action  = New-ScheduledTaskAction -Execute $py -Argument "main.py" -WorkingDirectory $dir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) -ExecutionTimeLimit ([TimeSpan]::Zero) -DontStopOnIdleEnd
Register-ScheduledTask -TaskName "MonitorPassagens" -Action $action -Trigger $trigger -Settings $settings
```

Pontos de atenção:
- O **diretório de trabalho** precisa ser a pasta do projeto, pois `DB_PATH` é relativo a ele.
- O computador precisa estar ligado e com internet. Se ele dormir, as rodadas ficam paradas.
- Para ver os logs, rode o comando manualmente ou redirecione a saída para um arquivo.
- Remover a tarefa: `Unregister-ScheduledTask -TaskName MonitorPassagens -Confirm:$false`.

### 7.3 Servidor Linux (systemd)

Arquivo `/etc/systemd/system/monitor-passagens.service` (ajuste usuário e caminhos):

```ini
[Unit]
Description=Monitor de passagens
After=network-online.target

[Service]
User=seu_usuario
WorkingDirectory=/opt/monitor-passagens
ExecStart=/opt/monitor-passagens/.venv/bin/python main.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now monitor-passagens
journalctl -u monitor-passagens -f   # acompanhar os logs
```

### 7.4 Hospedagem barata
Qualquer VPS pequena (1 vCPU, 512 MB) basta, pois o programa passa quase todo o tempo parado. Dê preferência a um servidor que não desligue sozinho. Copie a pasta (sem `.env` e sem `monitor.db`), crie o `.env` no servidor e use o systemd acima. Mantenha o `monitor.db` no servidor: é ele que evita alertas repetidos.

---

## 8. Mensagem recebida

Exemplo do formato (valores ilustrativos):

```
✈️ PASSAGEM BARATA ENCONTRADA!

Origem: Guarulhos (São Paulo) (GRU)
Destino: Palmas (PMW)
Ida: 09/05/2027
Volta: 16/05/2027
Duração: 7 dias
Preço total (ida e volta): R$ 757,00
Companhia: LATAM
Fonte: Ignav (confirmado)

Conferir: https://www.google.com/travel/flights?q=...

Preço e disponibilidade podem mudar. Confira as condições antes de comprar.
```

Quando você receberá outro alerta da mesma viagem: só se o preço cair pelo menos `MIN_NOTIFY_DROP_BRL` abaixo do último valor notificado. Para uma viagem diferente (outras datas ou outro destino), o alerta é independente.

---

## 9. Custos e limites das APIs

O gargalo é o número de buscas em tempo real. São `ORIGINS × DESTINATIONS` rotas (padrão 2 × 23 = 46) e cerca de 49 pares de datas por rota: **mais de 2.000 combinações**. Cada busca confere **uma** combinação, então é impossível cobrir tudo; a amostragem rotativa distribui a cobertura ao longo do tempo.

Estimativas (uma rodada a cada 24 h, ou cerca de 30 rodadas em 30 dias, preços da documentação do Ignav no momento da escrita):

| `MAX_VALIDATIONS_PER_RUN` | Buscas por mês | Custo aproximado |
|---|---|---|
| 10 (padrão) | ~300 | Cabe no teto padrão de 900/mês; as 1.000 gratuitas duram cerca de 3 meses (se valerem para a conta toda). |
| 46 (uma por rota) | ~1.400 | ~US$ 0,80 no primeiro mês (descontadas as 1.000 gratuitas). Exige subir `VALIDATION_MONTHLY_LIMIT` para ~1500. |

Cuidados:
- `VALIDATION_MONTHLY_LIMIT` (padrão 900) **interrompe** a validação quando atinge o teto no mês. Ajuste junto com o valor por rodada. Sem aumentá-lo, 46 buscas por rodada esgotam o teto de 900 em cerca de 20 rodadas (uns 20 dias).
- O contador é gravado em `monitor.db` por mês-calendário. Ele conta as requisições feitas pelo monitor; confirme o consumo real no painel do Ignav.
- A cota gratuita do Ignav parece valer para as primeiras 1.000 requisições da conta, não por mês. Confirme nos termos deles.
- Para acompanhar o gasto: painel do Ignav e linha "Validação: N buscas" no log de cada rodada.

---

## 10. Testes

```powershell
python -m pytest -q
```

Os 35 testes usam provedores falsos, HTTP simulado e um SQLite temporário: **não fazem chamadas reais nem enviam mensagens**. Cobrem cálculo de duração, validação de datas e da configuração, limite de preço, moedas diferentes, comparação de tarifas, notificações duplicadas, reenvio quando o preço cai, falhas de API (novas tentativas, 401, resposta inválida), falha no WhatsApp, limite mensal, amostragem rotativa e persistência do histórico.

---

## 11. Estrutura do projeto

```
monitor-passagens/
├── main.py                       # loop principal (--once para uma rodada)
├── config.py                     # leitura e validação do .env
├── models.py                     # Offer e PriceKind (CACHED | LIVE)
├── dates.py                      # duração e combinações de datas válidas
├── rules.py                      # limite de preço e decisão de notificar
├── airports.py                   # nomes dos aeroportos
├── services/
│   ├── search_service.py         # orquestra descoberta, validação e alerta
│   ├── http.py                   # timeout, retry com backoff, erros sem chaves
│   ├── link_builder.py           # link de pesquisa no Google Flights
│   ├── message.py                # texto do alerta
│   ├── providers/
│   │   ├── base.py               # interfaces DiscoveryProvider / ValidationProvider
│   │   ├── travelpayouts.py      # descoberta (cache)
│   │   ├── ignav_flights.py      # validação (tempo real)
│   │   └── serpapi_flights.py    # validação alternativa
│   └── notifiers/
│       ├── base.py               # interface Notifier
│       └── callmebot.py          # WhatsApp via CallMeBot
├── repositories/
│   ├── offers_repository.py      # interface de armazenamento
│   └── sqlite_repository.py      # implementação SQLite
├── tests/
├── .env.example
├── requirements.txt
└── pytest.ini
```

**Por que SQLite e não JSON:** as escritas são atômicas (uma queda no meio não corrompe o histórico), o mesmo arquivo guarda o histórico de alertas, o contador mensal de buscas e a posição da amostragem, e a consulta "último preço notificado desta oferta" é direta. A lógica de busca só conhece a interface `OffersRepository`, então trocar por outro armazenamento não exige mexer nela.

Tabelas do `monitor.db`: `notified_offers` (histórico de alertas), `api_usage` (buscas por provedor e mês) e `cursors` (posição da amostragem).

---

## 12. Como adicionar uma nova fonte ou notificador

**Nova fonte de preços:**
1. Crie uma classe em `services/providers/` que implemente `ValidationProvider` (`validate(origem, destino, ida, volta)` → `Offer` ou `None`) ou `DiscoveryProvider`.
2. Use `PriceKind.LIVE` apenas para preços retornados em tempo real; `CACHED` para estimativas.
3. Levante `ApiError` em falhas (e `AuthError` em credenciais rejeitadas), e use `services/http.py` para as chamadas.
4. Registre a opção em `config.py` (`VALIDATION_PROVIDER`) e em `main.py`.

**Novo canal de aviso** (ex.: API oficial do WhatsApp Business, Telegram): implemente `Notifier.send(texto)`, levantando `NotificationError` em caso de falha, e instancie-o em `main.py`.

---

## 13. Segurança

- Credenciais ficam só no `.env`, que está no `.gitignore` junto com `*.db`. Não copie o `.env` para repositórios, e-mails ou conversas.
- O logger do `httpx` está em nível WARNING porque, em nível INFO, ele escreve a URL completa (que pode conter chaves).
- As mensagens de erro do programa nunca incluem URLs completas nem chaves.
- Se uma chave vazar, **gere outra** no painel do serviço e atualize o `.env`.

---

## 14. Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `Variáveis de ambiente ausentes: ...` | Chave não preenchida | Preencha no `.env`. |
| `credenciais rejeitadas (HTTP 401)` | Chave errada, regenerada ou de outro tipo | Copie de novo a chave **privada** no painel do serviço. |
| `Descoberta: 0 candidatas` | Cache do Travelpayouts vazio para essas datas | Normal para datas distantes; a amostragem rotativa cobre a validação. |
| Nenhum alerta chega | Nenhuma oferta ≤ limite, ou `DRY_RUN=true` | Veja o log e o valor de `DRY_RUN`. |
| `Limite mensal de buscas atingido` | Teto `VALIDATION_MONTHLY_LIMIT` | Aumente o teto (observando o custo) ou espere o mês virar. |
| `Falha ao enviar alerta` | CallMeBot fora do ar ou ativação expirada | Refaça a ativação e atualize `CALLMEBOT_APIKEY`. A oferta será tentada de novo na próxima rodada. |
| Caracteres estranhos no terminal do Windows | Codificação do console | Só afeta a exibição; a mensagem de WhatsApp sai correta. Opcional: `chcp 65001`. |
| Quero zerar o histórico | , | Pare o programa e apague `monitor.db`. Alertas já enviados poderão ser reenviados. |

---

## 15. Pendências conhecidas

- O endpoint v3 do Travelpayouts e seus campos foram escritos a partir de fontes secundárias; a página oficial bloqueou a consulta automática. A chamada de teste funcionou (`success: true`), mas os campos de resposta só foram vistos de forma parcial. Confira com dados reais perto da data da viagem.
- O Ignav não documenta explicitamente BRL nem o Brasil; o teste real devolveu BRL em rotas domésticas. O monitor descarta qualquer oferta que não venha em BRL.
- O link do alerta é uma pesquisa no Google Flights, não um link de compra; o Ignav tem um endpoint de links de reserva que não foi integrado.
- O FAQ do Ignav pede para não guardar resultados em cache por muitas horas. O monitor só grava os alertas enviados, mas confirme com o suporte deles se o monitoramento a cada 24 horas é aceito.
- O CallMeBot não tem garantia de serviço e só envia ao próprio número. Para algo mais robusto, implemente um `Notifier` para a API oficial do WhatsApp Business.
- O programa não converte moedas: ofertas que não venham em BRL são descartadas.
