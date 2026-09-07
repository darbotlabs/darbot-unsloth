<h1 align="center" style="margin:0;">
  <a href="https://unsloth.ai/docs"><picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/unslothai/unsloth/main/images/unsloth%20logo%20white%20text.png">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/unslothai/unsloth/main/images/unsloth%20logo%20black%20text.png">
    <img alt="Unsloth logo" src="https://raw.githubusercontent.com/unslothai/unsloth/main/images/unsloth%20logo%20black%20text.png" height="80" style="max-width:100%;">
  </picture></a>
</h1>
<h3 align="center" style="margin: 0; margin-top: 0;">
Unsloth is the first desktop app to run and train models.
</h3>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-get-started">Quickstart</a> •
  <a href="#-free-notebooks">Notebooks</a> •
  <a href="https://unsloth.ai/docs">Documentation</a>
</p>

<p align="center">
  <a href="https://unsloth.ai/docs/desktop">
    <img height="400" alt="unsloth desktop" src="https://unsloth.ai/cgi/image/unsloth_qwen3.8_final_ut2eqWnYJ-SLmu0s7x522.png?format=raw" />
  </a>
</p>

## ⚡ Get started

### This fork's platform policy

This is **[darbotlabs/darbot-unsloth](https://github.com/darbotlabs/darbot-unsloth)**,
not an upstream release. Use a checkout and **`--local`** to install this code.
Upstream desktop downloads, Docker images and hosted notebooks below do **not**
contain this fork's changes; no fork release artifacts are assumed published.
Windows non-local installation downloads a commit-qualified GitHub source
archive, not upstream PyPI, and does not require Git. The remote source must
contain this migration's helper and vendored companion. Default remote installs
track fork `main` for updates while repairs use their recorded immutable snapshot.
Explicit local/CI sources are not advanced to a remote ref; use `--local` for
uncommitted changes in the current checkout.

| Component | Fork target |
| --- | --- |
| Python | **Standard, GIL-enabled CPython >=3.14.7,<3.15**; default 3.14.7 |
| PyTorch / NVIDIA wheels | **2.14.0 / cu130** |
| TorchVision / TorchAudio | **0.29.0 / 2.11.0** (TorchAudio 2.14 is not published) |
| Triton | CUDA: **3.8.0** / NVIDIA Windows **3.8.0.post28**; XPU: **triton-xpu 3.8.0**; ROCm: **triton-rocm 3.8.0** |
| datasets / scikit-learn | **5.0.1 / 1.9.0** |
| Transformers | **5.16.1**, with the compatible framework constraints in this checkout |
| CI / frontend build Node | **26.8.1** (current stable) |

Python 3.12/3.13, Python 3.14 before 3.14.7, 3.15, PyPy, prereleases and
free-threaded `3.14t` builds are unsupported, including `--no-torch` installs.
Full installs resolve the vendored Zoo companion **before** local Core; do not
replace it with upstream Zoo or manually override incompatible dependency caps.
GGUF-only `--no-torch` installs defer Zoo, whose dependencies require Torch, and
resolve local `unsloth[studio]` plus the Torch-free runtime normally. Studio setup also
resolves its Data Designer packages and plugins without training dependencies.
This does not install an inconsistent Zoo package using `--no-deps`.
Dedicated GGUF constraints reject accidental transitive Torch/Zoo/compiler
dependencies without changing the supported CPU-ML or CUDA profiles.

Python compatibility is not GPU/backend certification. NVIDIA CUDA 13 needs a
compatible 580-series-or-newer driver. **Ampere / sm_80 or newer** remains the
primary accelerated-training target, but **Turing / sm_75 is not blanket-rejected**.
On Windows, **both physical NVIDIA T1000 GPUs (sm_75)** passed the offline
[tiny-Llama qualification](tests/test_python314_gpu_smoke.py) using CPython
3.14.7, Torch 2.14/cu130 and Triton-Windows 3.8.0.post28:

- **FP32 manual LoRA SFT** on attention Q/K/V/O and MLP projections.
- **Default 4-bit QLoRA** with seven genuinely packed CUDA `Linear4bit` layers;
  forward/backward and optimizer steps changed adapter weights.
- **FP32 and 4-bit adapter save/reload**, preserving weights and logits within
  their precision tolerances, plus real TensorBoard write/read roundtrips.

Compiled elementwise forward/backward tests also passed. These are demonstrated
tiny-model paths, not certification of every model, precision, backend, or
Linux/Docker image. Published upstream Turing support policy remains separate
from this fork's measured results; native BF16 acceleration is unavailable.
CPU/GGUF, Apple Silicon MLX, AMD/ROCm, Intel/XPU, vLLM, Flash Attention and
compiled extensions require their own compatible wheels and runtime validation;
this migration does not claim every upstream backend is enabled.
All installers and Docker select `cu130` for NVIDIA. Although a `cu126` wheel
trio exists, this fork's canonical policy does not enable it or silently switch
to it for older drivers. Upgrade the NVIDIA driver for CUDA 13, or explicitly
select CPU/GGUF mode.
Other selected indexes are `cpu`, `xpu`, and Linux `rocm7.2`. Unsupported explicit
families such as `cu128` fail rather than silently changing the requested family.
Wheel availability alone does not qualify a GPU, driver, or training backend.
Hugging Face FP8/FP4 compressed export through current stable LLMCompressor 0.13
and compressed-tensors 0.18 is blocked by their Torch compatibility requirements;
this fork does not downgrade Torch 2.14 to enable it. GGUF export and other
quantization paths are separate capabilities, not substitutes for that qualification.

Fork desktop automatic updates and production publication are disabled until
real fork signing keys, updater configuration and release artifacts exist.
Release workflows additionally require the repository variable
`UNSLOTH_DESKTOP_PUBLISH=true`; setting it alone does not supply signing keys or
enable an unconfigured updater.

Upstream native application downloads (not this fork):
<table>
  <tr>
    <td><b>Platform</b></td>
    <td><b>Link</b></td>
  </tr>
  <tr>
    <td><b>Windows</b></td>
    <td><a href='https://github.com/unslothai/unsloth/releases/latest/download/Unsloth-Desktop-Windows.exe'>Download</a></td>
  </tr>
  <tr>
    <td><b>macOS</b></td>
    <td><a href='https://github.com/unslothai/unsloth/releases/latest/download/Unsloth-Desktop-MacOS.dmg'>Download</a></td>
  </tr>
  <tr>
    <td><b>Linux / Ubuntu (deb)</b></td>
    <td><a href='https://github.com/unslothai/unsloth/releases/latest/download/Unsloth-Desktop-Ubuntu.deb'>Download</a></td>
  </tr>
  <tr>
    <td><b>Linux (AppImage)</b></td>
    <td><a href='https://github.com/unslothai/unsloth/releases/latest/download/Unsloth-Desktop-Linux.AppImage'>Download</a></td>
  </tr>
</table>

Download from [Unsloth](https://unsloth.ai/download) or [GitHub Releases](https://github.com/unslothai/unsloth/releases).

Or if you prefer to install manually:

#### macOS, Linux, WSL:
```bash
git clone https://github.com/darbotlabs/darbot-unsloth unsloth
cd unsloth
bash install.sh --local
```
#### Windows:
```powershell
git clone https://github.com/darbotlabs/darbot-unsloth unsloth
Set-Location unsloth
.\install.ps1 --local
```
#### Community:

- [Discord](https://discord.gg/unsloth)
- [𝕏 (Twitter)](https://x.com/UnslothAI)
- [Reddit](https://reddit.com/r/unsloth)

## ⭐ Features
Upstream features span **Windows, Linux, WSL** and **macOS**. This fork retains
those integrations subject to the narrower [platform policy](#this-forks-platform-policy);
their presence is not a claim that each backend passes the new stack's runtime tests.

### Run & Build with AI
* Run and train LLMs, MLX, GGUF, diffusion, embedding, audio models: [Qwen3.8](https://unsloth.ai/docs/models/qwen3.8), [GLM-5.3-Flash](https://unsloth.ai/docs/models/glm-5.3-flash), [Kimi K3](https://unsloth.ai/docs/models/kimi-k3), MiniMax-H3, [DeepSeek-V4](https://unsloth.ai/docs/models/deepseek-v4), [Gemma 4](https://unsloth.ai/docs/models/gemma-4).
* **Agents & Tools:** Use local models with [Claude Code](https://unsloth.ai/docs/basics/claude-code), [Codex](https://unsloth.ai/docs/basics/codex), and [MCP](https://unsloth.ai/docs/basics/mcp), including tool calling and code execution.
* **Search & RAG:** Use private and unlimited web search, deep research, auto-compaction (rolling context window) and RAG.
* **Image and video:** Run and train [image](https://unsloth.ai/docs/basics/diffusion-image) and video diffusion or multimodal models
* **Remote & LAN:** Access your local models from any device on [LAN](https://unsloth.ai/docs/basics/lan) or remotely through secure [Cloudflare](https://unsloth.ai/docs/basics/how-to-serve-local-llms-anywhere-secure-remote-access-with-cloudflare-and-unsloth) HTTPS.
* **Connect:** Serve models through an [OpenAI compatible API](https://unsloth.ai/docs/basics/api). Also connect your ChatGPT/Codex subscription and [cloud providers](https://unsloth.ai/docs/integrations/connections)


### Train & Deploy
* **Fine-tuning:** Train LLMs, diffusion, TTS, and embedding models 2× faster with 70% less VRAM with [no accuracy loss](https://unsloth.ai/blog#training)
* **Complete support:** Supports [reinforcement learning](https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide), LoRA, QLoRA, full fine tuning, pretraining, RL, GRPO, DPO, and FP8.
* **Export & Deploy:** [Export](https://unsloth.ai/docs/new/studio/export) or Deploy models with including [GGUF](https://unsloth.ai/docs/basics/inference-and-deployment/saving-to-gguf), NVFP4, FP8 and more formats.
* **Datasets:** Build datasets from PDFs, CSVs, DOCX files, and more with [Data Recipes](https://unsloth.ai/docs/new/studio/data-recipe).
  
## 🚀 Unsloth Start

[Unsloth Start](https://unsloth.ai/docs/integrations/unsloth-start) connects [Claude Code](https://unsloth.ai/docs/basics/claude-code), [Codex](https://unsloth.ai/docs/basics/codex) and other agents to local models with one command.

```bash
unsloth start claude --model unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_XL
```

| Agent | Command |
| --- | --- |
| Claude Code | `unsloth start claude` |
| OpenAI Codex | `unsloth start codex` |
| Hermes Agent | `unsloth start hermes` |
| OpenClaw | `unsloth start openclaw` |
| OpenCode | `unsloth start opencode` |
| DeepSeek Harness | `unsloth start dsh` |

## 📥 Install
Unsloth can be used in three ways: **[Unsloth Desktop](https://unsloth.ai/download)**, the desktop app; **[Unsloth Studio](https://unsloth.ai/docs/new/studio/)**, the web UI; or **Unsloth Core**, the code based version.

### Upstream Unsloth Desktop (not a fork build)

<table>
  <tr>
    <td><b>Platform</b></td>
    <td><b>Link</b></td>
  </tr>
  <tr>
    <td><b>Windows</b></td>
    <td><a href='https://github.com/unslothai/unsloth/releases/latest/download/Unsloth-Desktop-Windows.exe'>Download</a></td>
  </tr>
  <tr>
    <td><b>macOS</b></td>
    <td><a href='https://github.com/unslothai/unsloth/releases/latest/download/Unsloth-Desktop-MacOS.dmg'>Download</a></td>
  </tr>
  <tr>
    <td><b>Linux / Ubuntu (deb)</b></td>
    <td><a href='https://github.com/unslothai/unsloth/releases/latest/download/Unsloth-Desktop-Ubuntu.deb'>Download</a></td>
  </tr>
  <tr>
    <td><b>Linux (AppImage)</b></td>
    <td><a href='https://github.com/unslothai/unsloth/releases/latest/download/Unsloth-Desktop-Linux.AppImage'>Download</a></td>
  </tr>
</table>

### Unsloth Studio (web UI)

#### macOS, Linux, WSL:
```bash
bash install.sh --local
```

#### Windows:
```powershell
.\install.ps1 --local
```

#### Launch
```bash
unsloth studio
```

#### HTTP Secure Deployment
```bash
unsloth studio --secure
```

#### Docker
Build matching fork images using [the Docker guide](docker/DOCKERHUB.md).
`unsloth/unsloth` on Docker Hub is upstream, not this fork. On Linux, set up GPU
access with `sudo -E bash docker/install_nvidia_toolkit.sh` (Windows: Docker Desktop
with WSL 2). After building `darbot-unsloth:studio`, run:
```bash
docker run -d --gpus all --ipc=host \
  -p 8000:8000 -p 8888:8888 \
  -e UNSLOTH_STUDIO_PASSWORD="mypassword" -e JUPYTER_PASSWORD="mypassword" \
  -v "$PWD":/workspace/host \
  darbot-unsloth:studio
```
Follow startup with `docker logs -f`. Studio is at `http://localhost:8000` (user `unsloth`), JupyterLab at `http://localhost:8888`. Use local `darbot-unsloth:core` for notebooks only. See the [fork Docker build and hardware policy](docker/DOCKERHUB.md); upstream Docker Hub images do not contain this migration.

#### Remote HTTPS & LAN Access
Server-side tools are on by default - so **be careful**! Keep your password safe, or use `--disable-tools` when exposing Unsloth.

**Global HTTPS Access**:
Creates a free Cloudflare link that serves Unsloth - you can access the link globally (even on your phone!)
```bash
unsloth studio --secure
```
`-H 0.0.0.0` and different ports also work:
```bash
unsloth studio -H 0.0.0.0 -p 8888
```
**LAN Access (home network)**: `Settings > API keys > LAN access`

#### Password management & headless starts
Headless starts:
```bash
UNSLOTH_STUDIO_PASSWORD='your-strong-password' unsloth studio --secure   # via env var
```
Reset your password:
```bash
unsloth studio reset-password
```

#### Developer, Nightly, Uninstall
To see developer, nightly and uninstallation etc. instructions, see [advanced installation](#-advanced-installation).

### Unsloth Core (code-based)
#### Linux, WSL:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv unsloth_env --python 3.14.7
source unsloth_env/bin/activate
uv pip install "torch==2.14.0" "torchvision==0.29.0" "torchaudio==2.11.0" --index-url https://download.pytorch.org/whl/cu130
python studio/install_zoo.py --python "$(pwd)/unsloth_env/bin/python"
uv pip install -e .
```
#### Windows:
```powershell
winget install -e --id Python.Python.3.14
winget install --id=astral-sh.uv  -e
uv venv unsloth_env --python 3.14.7
.\unsloth_env\Scripts\activate
uv pip install "torch==2.14.0" "torchvision==0.29.0" "torchaudio==2.11.0" --index-url https://download.pytorch.org/whl/cu130
python studio\install_zoo.py --python "$PWD\unsloth_env\Scripts\python.exe"
uv pip install -e .
```

#### AMD, Intel, DGX Spark, Blackwell:
See our [Blackwell guide](https://unsloth.ai/docs/blog/fine-tuning-llms-with-blackwell-rtx-50-series-and-unsloth) and [DGX Spark guide](https://unsloth.ai/docs/blog/fine-tuning-llms-with-nvidia-dgx-spark-and-unsloth). <br>
To install Unsloth on **AMD** and **Intel** GPUs, follow our [AMD Guide](https://unsloth.ai/docs/basics/amd) and [Intel Guide](https://unsloth.ai/docs/get-started/install/intel).

## 📒 Free Notebooks

Train for free with our notebooks.
Read our [guide](https://unsloth.ai/docs/get-started/fine-tuning-llms-guide). Add dataset, run, then deploy your trained model.

| Model | Free Notebooks | Performance | Memory use |
|-----------|---------|--------|----------|
| **Unsloth Studio**      | [▶️ Start for free](https://colab.research.google.com/github/unslothai/unsloth/blob/main/studio/Unsloth_Studio_Colab.ipynb)               |  |  |
| **Gemma 4 (E2B)**      | [▶️ Start for free](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Gemma4_(E2B)-Vision.ipynb)               | 1.5x faster | 50% less |
| **Qwen3.5 (4B)**      | [▶️ Start for free](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Qwen3_5_(4B)_Vision.ipynb)               | 1.5x faster | 60% less |
| **gpt-oss (20B)**      | [▶️ Start for free](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/gpt-oss-(20B)-Fine-tuning.ipynb)               | 2x faster | 70% less |
| **Qwen3.5 GSPO**      | [▶️ Start for free](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Qwen3_5_(4B)_Vision_GRPO.ipynb)               | 2x faster | 70% less |
| **gpt-oss (20B): GRPO**      | [▶️ Start for free](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/gpt-oss-(20B)-GRPO.ipynb)               | 2x faster | 80% less |
| **Qwen3: Advanced GRPO**      | [▶️ Start for free](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Qwen3_(4B)-GRPO.ipynb)               | 2x faster | 70% less |
| **embeddinggemma (300M)**    | [▶️ Start for free](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/EmbeddingGemma_(300M).ipynb)               | 2x faster | 20% less |
| **Llama 3.1 (8B) Alpaca**      | [▶️ Start for free](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Llama3.1_(8B)-Alpaca.ipynb)               | 2x faster | 70% less |
| **Llama 3.2 Conversational**      | [▶️ Start for free](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Llama3.2_(1B_and_3B)-Conversational.ipynb)               | 2x faster | 70% less |
| **Orpheus-TTS (3B)**     | [▶️ Start for free](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Orpheus_(3B)-TTS.ipynb)               | 1.5x faster | 50% less |

- See all our notebooks for: [Kaggle](https://github.com/unslothai/notebooks?tab=readme-ov-file#-kaggle-notebooks), [GRPO](https://unsloth.ai/docs/get-started/unsloth-notebooks#grpo-reasoning-rl-notebooks), [TTS](https://unsloth.ai/docs/get-started/unsloth-notebooks#text-to-speech-tts-notebooks), [embedding](https://unsloth.ai/docs/new/embedding-finetuning) & [Vision](https://unsloth.ai/docs/get-started/unsloth-notebooks#vision-multimodal-notebooks)
- See [all our models](https://unsloth.ai/docs/get-started/unsloth-model-catalog) and [all our notebooks](https://unsloth.ai/docs/get-started/unsloth-notebooks)
- See detailed documentation for Unsloth [here](https://unsloth.ai/docs)

## 🦥 Unsloth News
- **AMD training**: Train, run RL, chat and deploy on AMD GPUs across Windows, WSL and Linux. [Guide](https://unsloth.ai/docs/basics/amd)
- **Local models for any agent**: Use `unsloth start` with Claude Code, Codex, Hermes, OpenCode, OpenClaw, DeepSeek Harness and more through Unsloth's OpenAI- and Anthropic-compatible APIs. [Guide](https://unsloth.ai/docs/basics/api)
- **GLM-5.2**: Run Z.ai's 744B-parameter, 1M-context open model locally with Unsloth Dynamic GGUFs. [Guide](https://unsloth.ai/docs/models/glm-5.2)
- **DeepSeek-V4**: Run DeepSeek-V4-Flash locally with corrected multi-turn and tool-calling behavior. [Guide](https://unsloth.ai/docs/models/deepseek-v4)
- **Gemma 4**: Run and train Gemma 4 text, image and audio models with QAT, MTP, GGUF and MLX support. [Guide](https://unsloth.ai/docs/models/gemma-4)
- **MCP servers**: Connect local models to files, apps, databases and external tools through Model Context Protocol. [Guide](https://unsloth.ai/docs/basics/mcp)
- **New models**: [Qwen-AgentWorld](https://huggingface.co/unsloth/Qwen-AgentWorld-35B-A3B-GGUF), [Ornith](https://huggingface.co/unsloth/models?search=ornith), [Kimi K2.7 Code](https://unsloth.ai/docs/models/kimi-k2.7-code) and [MiniMax M3](https://unsloth.ai/docs/models/minimax-m3)

<details>
  <summary>More News</summary>

  - **Connections**: Mix local models with API providers (OpenAI, Anthropic) or servers (vLLM, Ollama) in the same interface. [Guide](https://unsloth.ai/docs/integrations/connections)
  - **Introducing Unsloth Studio**: our new web UI for running and training LLMs. [Blog](https://unsloth.ai/docs/new/studio)
  - **DiffusionGemma**: Run and fine-tune Google's diffusion language model with 1.8x faster inference in Unsloth Studio. [Guide](https://unsloth.ai/docs/models/diffusiongemma)
  - **Qwen3.6**: Run and train Qwen3.6 with MTP for 1.4-2.2x faster inference and NVFP4 quants for supported GPUs. [Guide](https://unsloth.ai/docs/models/qwen3.6)
  - Train **MoE LLMs 12x faster** with 35% less VRAM - DeepSeek, GLM, Qwen and gpt-oss. [Blog](https://unsloth.ai/docs/new/faster-moe)
  - **Embedding models**: Unsloth now supports ~1.8-3.3x faster embedding fine-tuning. [Blog](https://unsloth.ai/docs/new/embedding-finetuning) • [Notebooks](https://unsloth.ai/docs/get-started/unsloth-notebooks#embedding-models)
  - New **7x longer context RL** vs. all other setups, via our new batching algorithms. [Blog](https://unsloth.ai/docs/new/grpo-long-context)
  - New RoPE & MLP **Triton Kernels** & **Padding Free + Packing**: 3x faster training & 30% less VRAM. [Blog](https://unsloth.ai/docs/new/3x-faster-training-packing)
  - **500K Context**: Training a 20B model with >500K context is now possible on an 80GB GPU. [Blog](https://unsloth.ai/docs/blog/500k-context-length-fine-tuning)
  - **FP8 & Vision RL**: You can now do FP8 & VLM GRPO on consumer GPUs. [FP8 Blog](https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide/fp8-reinforcement-learning) • [Vision RL](https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide/vision-reinforcement-learning-vlm-rl)

</details>

## 📥 Advanced Installation
The below advanced instructions are for Unsloth Studio. For Unsloth Core advanced installation, [view our docs](https://unsloth.ai/docs/get-started/install/pip-install#advanced-pip-installation).

#### Developer / Nightly / Experimental installs: macOS, Linux, WSL:
The developer install builds from the `main` branch, which is the latest (nightly) source.
```bash
git clone https://github.com/darbotlabs/darbot-unsloth unsloth
cd unsloth
./install.sh --local
unsloth studio -p 8888
```
To install into an isolated location, set `UNSLOTH_STUDIO_HOME`:
```bash
UNSLOTH_STUDIO_HOME="$PWD/.studio" ./install.sh --local
UNSLOTH_STUDIO_HOME="$PWD/.studio" unsloth studio -p 8888
```
Then to update:
```bash
cd unsloth && git pull
./install.sh --local
unsloth studio -p 8888
```

#### Developer / Nightly / Experimental installs: Windows PowerShell:
The developer install builds from the `main` branch, which is the latest (nightly) source.
```powershell
git clone https://github.com/darbotlabs/darbot-unsloth.git unsloth
cd unsloth
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install.ps1 --local
unsloth studio -p 8888
```
To install into an isolated location, set `UNSLOTH_STUDIO_HOME`:
```powershell
$env:UNSLOTH_STUDIO_HOME="$PWD\.studio"; .\install.ps1 --local
$env:UNSLOTH_STUDIO_HOME="$PWD\.studio"; unsloth studio -p 8888
```
Then to update:
```powershell
cd unsloth; git pull
.\install.ps1 --local
unsloth studio -p 8888
```

#### Advanced launch options

Skip PyTorch (GGUF-only mode):
```bash
UNSLOTH_NO_TORCH=1 bash install.sh --local
```
```powershell
$env:UNSLOTH_NO_TORCH=1; .\install.ps1 --local
```

Skip the post-install prompt that starts Unsloth (useful for automated installs):
```bash
UNSLOTH_SKIP_AUTOSTART=1 bash install.sh --local
```
```powershell
$env:UNSLOTH_SKIP_AUTOSTART=1; .\install.ps1 --local
```

Keep the install-time package cache under the Studio directory instead of reusing an existing uv cache. Downloads are slower the first time, and an explicit `UV_CACHE_DIR` still wins over this:
```bash
UNSLOTH_ISOLATE_UV_CACHE=1 bash install.sh --local
```
```powershell
$env:UNSLOTH_ISOLATE_UV_CACHE=1; .\install.ps1 --local
```
For a local run the flag is `--isolated-uv-cache`:
```bash
./install.sh --local --isolated-uv-cache
```
```powershell
.\install.ps1 --local --isolated-uv-cache
```

Pinning the Python version:
```bash
UNSLOTH_PYTHON=3.14.7 bash install.sh --local
```
```powershell
$env:UNSLOTH_PYTHON='3.14.7'; .\install.ps1 --local
```

Install to a custom location with `UNSLOTH_STUDIO_HOME`:
```bash
UNSLOTH_STUDIO_HOME=/abs/path bash install.sh --local
```
```powershell
$env:UNSLOTH_STUDIO_HOME='C:\path'; .\install.ps1 --local
```

Point the frontend build at a corporate npm mirror/proxy with `UNSLOTH_NPM_REGISTRY`:
```bash
UNSLOTH_NPM_REGISTRY=https://artifactory.example.com/api/npm/npm/ ./install.sh --local
```
```powershell
$env:UNSLOTH_NPM_REGISTRY='https://artifactory.example.com/api/npm/npm/'; .\install.ps1 --local
```

Cap Unsloth's native CPU thread pools on high-core hosts: `UNSLOTH_CPU_THREADS=8 unsloth studio -p 8888`.

#### Vulkan, custom llama.cpp backends:

You can force the backend during installation: 
```bash
export UNSLOTH_LLAMA_CPP_BACKEND=vulkan   # or cpu, cuda, rocm, auto
bash install.sh --local
```
```powershell
$env:UNSLOTH_LLAMA_CPP_BACKEND="vulkan"   # or cpu, cuda, rocm, auto
.\install.ps1 --local
```

#### Uninstall

**MacOS, WSL, Linux:** `bash scripts/uninstall.sh`

**Windows (PowerShell):** `.\scripts\uninstall.ps1`

The uninstall helpers remove the managed Studio installation, not a separately
configured `UNSLOTH_ENV_DIR`. Preserve that external environment until its data and
rollback requirements have been reviewed; it is not implicitly deleted.

For more info, [see our docs](https://unsloth.ai/docs/new/studio/install#uninstall).

#### Migration and rollback

Do not upgrade an old environment in place with ad-hoc dependency overrides.
Stop Studio/training processes, record `pip freeze` and the source commit, and
back up the environment **and** Studio data before rebuilding. The Python minor
changes the ABI; do not copy old `site-packages`, compiled kernels or DLL/SO links.

`UNSLOTH_ENV_DIR` selects the dedicated Python environment independently of
`UNSLOTH_STUDIO_HOME` (data, models and settings). Keep it set for installation
and CLI use. Use direct updates for external environments, not desktop staging.

An existing external environment must contain `pyvenv.cfg` and the
`.unsloth-studio-owned` marker; arbitrary environments are not silently adopted.
For a fresh install, select an empty or absent dedicated directory. A successful
external rebuild retains its previous environment in a sibling rollback directory.

```powershell
$env:UNSLOTH_ENV_DIR='D:\darbot\unsloth-env'
$env:UNSLOTH_PYTHON='3.14.7'
.\install.ps1 --local
```

This rebuilds the intended **same path**, not a second live environment. Preserve
a separately named backup first. On POSIX the override must be absolute, e.g.
`UNSLOTH_ENV_DIR="$HOME/unsloth-env" bash install.sh --local`.
The desktop `--tauri` lifecycle does not support an external environment path.

Verify the interpreter, `python -m pip check`, `unsloth --help`, Studio health and
the actual model/backend workload before retiring the backup. If validation fails,
stop new processes and restore the original environment to its original path,
matching source commit and Studio data backup. An old Python backup is a rollback
to the old installation, **not** a supported runtime for this fork.

#### Source updates and repair

The environment's `.unsloth-studio-source.json` separates its immutable Core/Zoo
repair snapshot from optional `main` tracking. Package versions alone cannot
detect a newer commit. Legacy archive installations without recorded tracking
remain pinned: an immutable archive does not reveal whether its original intent
was a branch or an explicit commit. Git provenance requesting `main` or the
implicit fork default branch can supply that intent; an explicit commit/tag or
recorded `pinned` policy does not opt into branch tracking.

For a maintained fork archive installation, opt into tracking `main` once:

```bash
UNSLOTH_CORE_TRACKING_REF=main unsloth studio update
```

PowerShell, restoring the caller's environment afterward:

```powershell
$previousTracking = $env:UNSLOTH_CORE_TRACKING_REF
try {
    $env:UNSLOTH_CORE_TRACKING_REF = 'main'
    unsloth studio update
} finally {
    $env:UNSLOTH_CORE_TRACKING_REF = $previousTracking
}
```

The successful managed-source update records the tracking intent. Use `pinned`
instead to request a fixed-source operation. Explicit local/CI and editable
checkouts stay fixed to their selected source even if `main` is inherited.
Tracked updates resolve one immutable commit and prepare matching Core/Zoo
payloads before replacement; repair remains tied to the retained snapshot.
This source-update policy does not enable desktop signing or publication.

#### Deleting model files

You can delete old model files either from the bin icon in model search or by removing the relevant cached model folder from the default Hugging Face cache directory. By default, HF uses:

**MacOS, Linux, WSL:** `~/.cache/huggingface/hub/`

**Windows:** `%USERPROFILE%\.cache\huggingface\hub\`

## 💚 Community and Links
| Type                                                                                                                                      | Links                                                                          |
| ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| <img width="16" src="https://cdn.prod.website-files.com/6257adef93867e50d84d30e2/66e3d80db9971f10a9757c99_Symbol.svg" />  **Discord**                       | [Join Discord server](https://discord.com/invite/unsloth)                          |
| <img width="15" src="https://redditinc.com/hs-fs/hubfs/Reddit%20Inc/Brand/Reddit_Logo.png" />  **r/unsloth Reddit**                       | [Join Reddit community](https://reddit.com/r/unsloth)                          |
| 📚 **Documentation & Wiki**                                                                                                               | [Read Our Docs](https://unsloth.ai/docs)                                       |
| <img width="13" src="https://upload.wikimedia.org/wikipedia/commons/0/09/X_(formerly_Twitter)_logo_late_2025.svg" />  **Twitter (aka X)** | [Follow us on X](https://twitter.com/unslothai)                                |
| 🔮 **Our Models**                                                                                                                         | [Unsloth Catalog](https://unsloth.ai/docs/get-started/unsloth-model-catalog)   |
| ✍️ **Blog**                                                                                                                               | [Read our Blogs](https://unsloth.ai/blog)                                      |

### Citation

You can cite the Unsloth repo as follows:
```bibtex
@software{unsloth,
  author = {Daniel Han, Michael Han and Unsloth team},
  title = {Unsloth},
  url = {https://github.com/unslothai/unsloth},
  year = {2023}
}
```
If you trained a model with 🦥Unsloth, you can use this cool sticker!   <img src="https://raw.githubusercontent.com/unslothai/unsloth/main/images/made with unsloth.png" width="200" align="center" />

### License
Unsloth uses a dual-licensing model of Apache 2.0 and AGPL-3.0. The core Unsloth package remains licensed under **[Apache 2.0](https://github.com/unslothai/unsloth?tab=Apache-2.0-1-ov-file)**, while certain optional components, such as the Unsloth Studio UI are licensed under the open-source license **[AGPL-3.0](https://github.com/unslothai/unsloth?tab=AGPL-3.0-2-ov-file)**.

This structure helps support ongoing Unsloth development while keeping the project open source and enabling the broader ecosystem to continue growing.

### Thank You to
- The [llama.cpp library](https://github.com/ggml-org/llama.cpp) that lets users run and save models with Unsloth
- The Hugging Face team and their libraries: [transformers](https://github.com/huggingface/transformers) and [TRL](https://github.com/huggingface/trl)
- The Pytorch and [Torch AO](https://github.com/unslothai/unsloth/pull/3391) team for their contributions
- NVIDIA for their [NeMo DataDesigner](https://github.com/NVIDIA-NeMo/DataDesigner) library and their contributions
- And of course for every single person who has contributed or has used Unsloth!
