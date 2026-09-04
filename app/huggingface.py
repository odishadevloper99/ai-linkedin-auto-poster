from .http import request
class HuggingFace:
    """Optional secondary NLP provider. It is isolated so model changes do not touch business logic."""
    def __init__(self,c):self.c=c
    def classify(self,text):
        if not self.c.hf_key or not self.c.hf_model:return None
        url=f"https://router.huggingface.co/hf-inference/models/{self.c.hf_model}"
        r=request("POST",url,headers={"Authorization":f"Bearer {self.c.hf_key}","Content-Type":"application/json"},json={"inputs":text[:12000]},timeout=self.c.timeout,retries=self.c.retries)
        if not r.ok:raise RuntimeError(f"Hugging Face HTTP {r.status_code}: {r.text[:500]}")
        return r.json()
