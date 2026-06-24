FROM pytorch/pytorch:2.7.1-cuda12.6-cudnn9-runtime
ARG COMFYUI_REF=2d4970ff677970fbca9f9f562296eda46de8aa4c
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /opt
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && cd ComfyUI && git checkout "$COMFYUI_REF" && pip install --no-cache-dir -r requirements.txt -r manager_requirements.txt
WORKDIR /opt/ComfyUI/custom_nodes
RUN apt-get update && apt-get install -y --no-install-recommends build-essential ninja-build && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/kijai/ComfyUI-KJNodes.git && git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && git clone https://github.com/flowtyone/ComfyUI-Flowty-TripoSR.git && git clone https://github.com/yolain/ComfyUI-Easy-Use.git && git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && git clone --recurse-submodules https://github.com/Stability-AI/stable-fast-3d.git && for dir in */; do if [ -f "$dir/requirements.txt" ]; then (cd "$dir" && pip install --no-cache-dir -r requirements.txt); fi; done
RUN pip install --no-cache-dir huggingface-hub==0.36.2 onnxruntime-gpu==1.20.1
COPY workflows/comfyui /opt/ComfyUI/user/default/workflows
WORKDIR /opt/ComfyUI
EXPOSE 8188
CMD ["python","main.py","--listen","0.0.0.0","--port","8188","--enable-manager"]
