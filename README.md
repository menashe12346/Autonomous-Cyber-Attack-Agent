# ⚔️ Cyber-AI Offensive Framework  

Welcome to a fully autonomous offensive AI system for cyber attacks, driven by reinforcement learning and language models.  

---

## 🔧 SETUP INSTRUCTIONS (ARCH LINUX)

### 📌 Requirements:
- 🐍 Python 3.9+
- 🧱 C++17 compiler (e.g., `g++`)
- ❗ Disk space: ~6GB minimum, 10GB+ recommended
- 🧠 RAM: 8GB minimum, 16GB+ recommended for larger context

---

## 🚀 STEP 1: Install All Dependencies

### 👉 Arch Linux:
```bash
sudo pacman -Syu --needed base-devel cmake git python-pip
pip install pexpect huggingface_hub
```

### (Optional) Login to HuggingFace if the model is gated:
```bash
huggingface-cli login  # ← paste your token
```

---

## 💾 STEP 2: Download the Model (GGUF Format)

> Download Nous-Hermes-2-Mistral-7B-DPO in quantized `.gguf` format (Q4_K_M recommended):

```bash
wget -P {your_project_directory}/code/models/nous-hermes/ \
https://huggingface.co/NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF/resolve/main/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf
```

---

## 🛠️ STEP 3: Clone & Build llama.cpp

```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build
cd build
cmake ..
cmake --build . --config Release -j$(nproc)
```

---

## 🧠 STEP 5: Run the Full Autonomous Framework

Once the model and dependencies are ready, launch the full AI system:

```bash
python main.py
```

The agent will:
- Initialize datasets (CVE, Exploits, OS, etc.)
- Encode the environment state
- Use the LLM to reason about reconnaissance and attacks
- Select and execute actions using reinforcement learning

---

## 📂 Directory Structure

```text
project/
├── code/
│   ├── agents/               # Recon, Vuln, Exploit agents
│   ├── blackboard/           # Shared knowledge base
│   ├── encoders/             # State/Action encoders
│   ├── models/               # Policy model, LLM wrapper
│   ├── orchestrator/         # Scenario manager
│   └── utils/                # Helpers and tools
├── datasets/                 # CVE, exploit, OS datasets
├── models/                   # Saved LLM and policy model
└── main.py                   # Entry point
```

---





























# ─────────────────────────────────────────────

 לפרוייקט:

    1. הוספת רקורסיה של פרומפטים המוודאת שמודל הllm באמת מילא את כל הקטגוריות
    
# ─────────────────────────────────────────────

TO DO:

 1. vectorized learning
 2. llama-simple-chat
 3. Tokenizer that fits my agents
 4. Meta-Reinforcement Learning
 5. Communication-Based RL
 6. Hierarchical Parallel Multi-Agent RL
 7. ייצוג actions כגרף וביצוע GNN כלמידה
 8. שילוב של Hierarchical Multi-Agent RL עם Meta-Reinforcement Learning ו־Self-Reflective Systems)

 שלב 1: שימוש ב־state ריק למילוי

    מאפשר ניצול מלא של ההקשר החדש מבלי להכביד על prompt tokens.

    אתה משאיר את הזיכרון אצלך (ב-blackboard) ומאפשר למודל רק להשלים חלקים חדשים – מצוין!

🔹 שלב 2: Fine-Tuning על הקידוד שלך

    אתה נותן למודל ללמוד איך לפענח בעצמו את השפה הסימבולית שלך (הוקטור), וזה יאפשר ביצועים מהירים בעתיד.

    שימוש ב־PCA / AutoEncoder / Sliding Window בשלב מאוחר יותר – מראה שאתה מתכנן לקנה מידה מראש 🧠

# ─────────────────────────────────────────────

שילוב בין:

    תכנון דינמי "מתוחכם" עם התפלגות תוצאות

    DQN שממשיך ללמוד מכל פרק מחדש

זה בעצם DYNA-Q משודרג, או מה שמכונה לפעמים:

    "Model-Based RL with Uncertainty-aware Planning"


  
   
