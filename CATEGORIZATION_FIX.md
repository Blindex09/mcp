> **Histórico (março/2026).** Descreve o sistema antigo de categorização por regras de nome (`CATEGORY_RULES`, `categorize_skills.py`, `categories.json`), **removido em 25/09/2026**. Hoje a categoria vem da pasta pai + classificação do modelo (`classify_skills`). Ver `README.md`.

# 🔧 Categorização - Plano de Correção

**Gerado:** 27 de março de 2026  
**Objetivo:** Reduzir 378 "other" para ~50-100 máximo

---

## 📋 Análise de Prefixes em "OTHER"

Mapeamos os **378 skills em "other"** e encontramos padrões reutilizáveis:

```
context             :   9 skills  ← Meta/Advisória
code                :   8 skills  ← Pode ser architecture/language
conductor           :   7 skills  ← Orquestração = automation/ai
error               :   7 skills  ← Tratamento = testing/security
cc                  :   6 skills  ← Clean Code = architecture/language
fal                 :   6 skills  ← Domain específico
hig                 :   6 skills  ← HIG = frontend/design
startup             :   6 skills  ← Empresarial/Advisory  
tdd                 :   6 skills  ← Test-Driven = testing
git                 :   5 skills  ← Git workflows = devops
skill                :   5 skills  ← Meta (skills sobre skills)
web                 :   5 skills  ← Web = frontend/backend (ambíguo)
wiki                :   5 skills  ← Documentação = content
frontend            :   4 skills  ← BUG: Should be in frontend!
incident            :   4 skills  ← Incident mgt = devops/security
obsidian            :   4 skills  ← Obsidian = application specific
documentation      :   3 skills  ← Documentation = content
file                :   3 skills  ← File handling = backend/devops
framework           :   3 skills  ← Framework = language/backend
internal            :   3 skills  ← Internal = meta/advisory
```

---

## 🛠️ AÇÕES RECOMENDADAS

### ACTION-1: Adicionar 5 Novas Categorias

Baseado em mercado 2026 e skills vistas:

```python
CATEGORY_RULES: dict[str, dict] = {
    # ... existentes ...
    
    # ✨ NOVO: Design & UI Systems
    "design": {
        "tokens": ["design", "ui", "ux", "figma", "component", "hig"],
        "substrings": [
            "design-system", "figma", "component-library",
            "hig-components", "design-tokens", "accessibility-design"
        ],
        "prefixes": ["design-", "hig-"],
        "excludes": [],
    },
    
    # ✨ NOVO: Documentação & Knowledge
    "documentation": {
        "tokens": ["documentation", "wiki", "docs", "content", "blog"],
        "substrings": [
            "documentation", "wiki", "obsidian", "knowledge-base",
            "developer-docs", "api-docs"
        ],
        "prefixes": ["documentation-", "wiki-", "docs-"],
        "excludes": [],
    },
    
    # ✨ NOVO: Código & Quality
    "code-quality": {
        "tokens": ["clean", "code", "quality", "refactor", "lint", "format"],
        "substrings": [
            "clean-code", "refactor", "lint", "code-quality",
            "best-practices", "code-review", "tdd-", "error-"
        ],
        "prefixes": ["clean-", "refactor-"],
        "excludes": [],
    },
    
    # ✨ NOVO: Workflow & DevEx
    "workflow": {
        "tokens": ["workflow", "git", "conductor", "orchestration"],
        "substrings": [
            "workflow", "git-", "github-", "ci-cd-", "conductor",
            "orchestration", "engine", "automation-workflow"
        ],
        "prefixes": ["workflow-", "git-"],
        "excludes": [],
    },
    
    # ✨ NOVO: Advisory & Meta
    "advisory": {
        "tokens": ["consulting", "consultant", "advisor", "strategy"],
        "substrings": [
            "consultant", "consulting", "strategy", "advisor",
            "mentorship", "coaching", "andruia", "meta-"
        ],
        "prefixes": ["consulting-", "advisor-", "00-", "10-", "20-"],
        "excludes": [],
    },
}
```

---

### ACTION-2: Corrigir Skills Específicas em "OTHER"

| Skill | Atual | Novo | Motivo |
|-------|-------|------|--------|
| `00-andruia-consultant` | other | advisory | Prefixo `00-` = meta |
| `10-andruia-skill-smith` | other | advisory | Prefixo `10-` = meta |
| `20-andruia-niche-intelligence` | other | advisory | Prefixo `20-` = meta |
| `frontend-mobile-development...` | other | frontend, mobile | Está bem ali no nome |
| `clean-code-*` | other | code-quality | Token `clean-code` |
| `tdd-*` | other | testing, code-quality | Token `tdd` = testing |
| `git-*` | other | devops, workflow | Token `git` = workflow |
| `web-accessibility` | other | frontend, accessibility | Token `web-accessibility` |
| `conductor-*` | other | automation | Token `conductor` = orquestração |
| `error-handling-*` | other | code-quality, testing | Token `error-handling` |
| `obsidian-*` | other | documentation | Obsidian = knowledge base |
| `wiki-*` | other | documentation | Token `wiki` = documentation |
| `hig-components` | other | design | Token `hig` = HIG design |
| `design-system-*` | other | design | Token `design-system` |
| `documentation-*` | other | documentation | Token `documentation` |

---

### ACTION-3: Domínios Nichados que Precisam Nova Categoria?

Analisando skills encontramos **domínios emergentes 2026:**

```
🔗 blockchain-developer           → Precisa "web3"?
🎮 bevy-ecs-expert               → Precisa "gamedev"?
⚡ arm-cortex-expert              → Precisa "embedded"?
🎬 video-streaming-*              → Precisa "media"?
🤖 ml-ops-*                       → Precisa "mlops"?
🔬 research-*                     → Precisa "research"?
```

**Recomendação:** Sim, adicione 6 categorias de nicho:

```python
# ✨ MUITO NOVO (2026 emergente)
"web3": {
    "tokens": ["web3", "blockchain", "solidity", "web3"],
    "substrings": ["blockchain", "web3", "solidity", "ethereum", "crypto"],
    "prefixes": ["web3-", "blockchain-"],
    "excludes": [],
},

"gamedev": {
    "tokens": ["game", "gamedev", "unity", "unreal", "godot"],
    "substrings": ["game-", "gamedev", "unity", "unreal", "godot", "game-engine"],
    "prefixes": ["gamedev-", "game-"],
    "excludes": [],
},

"embedded": {
    "tokens": ["embedded", "iot", "rtos", "arduino"],
    "substrings": ["embedded-", "iot-", "rtos-", "arduino", "microcontroller", "cortex"],
    "prefixes": ["embedded-", "iot-"],
    "excludes": [],
},

"media": {
    "tokens": ["video", "audio", "streaming", "media"],
    "substrings": ["video-", "audio-", "streaming-", "media-", "ffmpeg", "encoding"],
    "prefixes": ["video-", "media-"],
    "excludes": [],
},

"mlops": {
    "tokens": ["mlops", "ml-ops", "model-monitoring"],
    "substrings": ["mlops", "ml-ops", "model-monitoring", "hyperparameter", "experiment-tracking"],
    "prefixes": ["mlops-"],
    "excludes": [],
},

"research": {
    "tokens": ["research", "academic", "paper"],
    "substrings": ["research-", "academic-", "paper-", "thesis"],
    "prefixes": ["research-"],
    "excludes": [],
},
```

---

## 📊 Impacto Esperado

### Antes:
```
other      : 378 (39.0%)  🤯
devops     : 164 (16.9%)
ai         :  94 (9.7%)
automation :  93 (9.6%)
backend    :  66 (6.8%)
testing    :  57 (5.9%)
security   :  57 (5.9%)
language   :  47 (4.9%)
frontend   :  44 (4.5%)
architecture: 34 (3.5%)
content    :  25 (2.6%)
data       :  15 (1.5%)
mobile     :  15 (1.5%)
accessibility: 8 (0.8%)
```

### Depois (Projetado):
```
devops       : 184 (19.0%)  [+20 de "other" + git/workflow]
ai           :  94 (9.7%)   [mesmo]
automation   :  93 (9.6%)   [mesmo]
backend      :  66 (6.8%)   [mesmo]
testing      :  63 (6.5%)   [+6 de tdd]
security     :  57 (5.9%)   [mesmo]
language     :  47 (4.9%)   [mesmo]
frontend     :  48 (5.0%)   [+4 fixed]
architecture :  40 (4.1%)   [+6 clean-code]
content      :  28 (2.9%)   [+3 documentation]
workflow     :  25 (2.6%)   [novo]
advisory     :  25 (2.6%)   [novo]
web3         :  18 (1.9%)   [novo]
design       :  20 (2.1%)   [novo]
code-quality :  20 (2.1%)   [novo]
data         :  15 (1.5%)   [mesmo]
mobile       :  15 (1.5%)   [mesmo]
documentation: 15 (1.5%)   [novo]
gamedev      :  12 (1.2%)   [novo]
embedded     :  11 (1.1%)   [novo]
media        :   8 (0.8%)   [novo]
mlops        :   6 (0.6%)   [novo]
accessibility: 8 (0.8%)     [mesmo]
research     :   5 (0.5%)   [novo]
other        :  50 (5.2%)   ✅ 87% reduction!
```

---

## 🎯 Implementação (Passo a Passo)

### Step 1: Backup
```bash
cp c:\mcp\categories.json c:\mcp\categories.json.backup
cp c:\mcp\mcp_server.py c:\mcp\mcp_server.py.backup
```

### Step 2: Update CATEGORY_RULES

Adicione as 11 novas categorias no `mcp_server.py`:
- 5 novas: design, documentation, code-quality, workflow, advisory
- 6 nicho: web3, gamedev, embedded, media, mlops, research

### Step 3: Validar

```bash
python categorize_skills.py
# Esperar: other < 100
```

### Step 4: Verificar Overlaps

```python
# script to verify
data = json.load(open('categories.json'))
multi_cat = [k for k,v in data.items() if len(v) > 2]
print(f"Skills com 3+ categorias: {len(multi_cat)}")
# Esperar: < 10% do total
```

### Step 5: Deploy & Test

```bash
python test.py
# Esperar: todos os testes passarem
```

---

## 🔍 Exemplos Concretos

### Exemplo 1: TDD Skills

**Antes:**
```json
{
  "tdd-101": ["other"],
  "tdd-testing": ["other"],
  "tdd-patterns": ["other"]
}
```

**Depois:**
```json
{
  "tdd-101": ["testing", "code-quality"],
  "tdd-testing": ["testing", "code-quality"],
  "tdd-patterns": ["code-quality", "testing"]
}
```

---

### Exemplo 2: Frontend mal categorizado

**Antes:**
```json
{
  "frontend-mobile-development-component-scaffold": ["other"]
}
```

**Depois:**
```json
{
  "frontend-mobile-development-component-scaffold": ["frontend", "mobile"]
}
```

---

### Exemplo 3: Novo domínio (gamedev)

**Antes:**
```json
{
  "bevy-ecs-expert": ["other"],
  "unity-performance": ["other"],
  "godot-tips": ["other"]
}
```

**Depois:**
```json
{
  "bevy-ecs-expert": ["gamedev"],
  "unity-performance": ["gamedev"],
  "godot-tips": ["gamedev"]
}
```

---

## 📈 Métricas de Sucesso

| Métrica | Alvo | Atual | Prazo |
|---------|------|-------|-------|
| **"other" < 100** | 100 | 378 | Semana 1 |
| **Overlaps < 10** | 10 | ? | Semana 1 |
| **Novas categorias** | 11 | 13 | Semana 1 |
| **Market alignment** | 95%+ | 91.7% | Semana 2 |

---

**Próxima ação:** Implementar ACTION-1 (novas categorias) e executar categorize_skills.py novamente.
