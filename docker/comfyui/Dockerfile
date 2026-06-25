FROM pytorch/pytorch:2.7.1-cuda12.6-cudnn9-runtime
ARG COMFYUI_REF=2d4970ff677970fbca9f9f562296eda46de8aa4c
ARG KJNODES_REF=588badc5252c2b483c8b37110f155973cf39e325
ARG WANVIDEO_REF=088128b224242e110d3906c6750e9a3a348a659b
ARG TRIPOSR_REF=a0c94ac60a7cc062604f61aeeea6d0d493521de3
ARG EASYUSE_REF=54d080bf6a4f52da287e984f305243c10db097f5
ARG VHS_REF=4ee72c065db22c9d96c2427954dc69e7b908444b
ARG SF3D_REF=ff21fc491b4dc5314bf6734c7c0dabd86b5f5bb2
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /opt
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && cd ComfyUI && git checkout "$COMFYUI_REF" && pip install --no-cache-dir -r requirements.txt
WORKDIR /opt/ComfyUI/custom_nodes
RUN apt-get update && apt-get install -y --no-install-recommends build-essential ninja-build && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/ltdrdata/ComfyUI-Manager.git && git clone https://github.com/kijai/ComfyUI-KJNodes.git && git -C ComfyUI-KJNodes checkout "$KJNODES_REF" && git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && git -C ComfyUI-WanVideoWrapper checkout "$WANVIDEO_REF" && git clone https://github.com/flowtyone/ComfyUI-Flowty-TripoSR.git && git -C ComfyUI-Flowty-TripoSR checkout "$TRIPOSR_REF" && git clone https://github.com/yolain/ComfyUI-Easy-Use.git && git -C ComfyUI-Easy-Use checkout "$EASYUSE_REF" && git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && git -C ComfyUI-VideoHelperSuite checkout "$VHS_REF" && git clone https://github.com/Stability-AI/stable-fast-3d.git && git -C stable-fast-3d checkout "$SF3D_REF" && git -C stable-fast-3d submodule update --init --recursive && for dir in */; do if [ -f "$dir/requirements.txt" ]; then (cd "$dir" && pip install --no-cache-dir -r requirements.txt); fi; done
RUN pip install --no-cache-dir huggingface-hub==0.36.2 onnxruntime-gpu==1.20.1
COPY workflows/comfyui /opt/ComfyUI/user/default/workflows
WORKDIR /opt/ComfyUI
EXPOSE 8188
CMD ["python","main.py","--listen","0.0.0.0","--port","8188","--enable-manager"]
