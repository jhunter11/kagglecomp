# Linux self-play environment for the cg engine.
# cg ships as a native Linux lib (libcg.so via ctypes) and will NOT load on macOS,
# so we run it in a Linux container on the Mac. Build for amd64 (the lib's arch);
# on Apple Silicon this runs under emulation (correct, just slower than a native VM).
#
#   docker build --platform linux/amd64 -t ptcg-selfplay -f loop/Dockerfile .
#   docker run --platform linux/amd64 --rm -v "$PWD":/work -w /work ptcg-selfplay \
#       python scripts/run_official_simulations.py --agent agents/lucario --opponent random --games 200
#
# Place the downloaded engine at ./cg/ (libcg.so, api.py, game.py, sim.py, ...) first.
FROM --platform=linux/amd64 python:3.11-slim-bookworm

# runtime deps the native engine links against
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 libgomp1 ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# the repo is bind-mounted at run time (-v "$PWD":/work), so code edits are live
CMD ["python", "-c", "import cg; print('cg loaded OK:', cg.__file__)"]
