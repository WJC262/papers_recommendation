# 1. 在服务器上新建一个脚本 convert_m3e_to_sbert.py
from sentence_transformers import SentenceTransformer, models
from pathlib import Path

src = "./pre_train_model/m3e-large"          # 你的 transformers 模型
dst = "./pre_train_model/m3e-large-sbert"    # 转好的新目录

bert = models.Transformer(src)               # 加载原始 transformers 模型
pooling = models.Pooling(
    bert.get_word_embedding_dimension(),
    pooling_mode="mean"
)

sbert = SentenceTransformer(modules=[bert, pooling])
Path(dst).mkdir(parents=True, exist_ok=True)
sbert.save(dst)
print("✅ 已保存到", dst)
