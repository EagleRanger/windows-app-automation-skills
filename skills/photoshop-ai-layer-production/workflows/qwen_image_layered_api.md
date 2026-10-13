# Qwen-Image-Layered API 工作流

`scripts/run_qwen_layered.py` 在运行时生成 ComfyUI API 图，不依赖界面坐标。图中使用固定核心节点：加载图像、最长边缩放、Qwen 2.5 VL 文本编码器、Layered VAE、FP8 diffusion model、AuraFlow sampling、Qwen layered latent、KSampler、LatentCut、LatentCutToBatch、RGBA VAE 解码与 SaveImage。

脚本保存两类结果：

- `full/`：模型重新生成的完整图，用于复合误差检查；
- `layers/`：删除完整图后的逐层 RGBA 批次。

默认参数来自本机成功试验：1024 长边、8 层、20 steps、CFG 2.5、Euler/simple、seed 777。官方原始采样建议为 50 steps、CFG 4.0，时间至少翻倍。输出层没有语义名和 z-index，必须逐图目视映射。
