import time,requests
RETRY={408,425,429,500,502,503,504}
def request(method,url,**kw):
    retries=kw.pop("retries",3); last=None
    for i in range(retries):
        try:
            r=requests.request(method,url,**kw)
            if r.status_code not in RETRY:return r
            last=RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
        except requests.RequestException as e:last=e
        if i<retries-1:time.sleep(min(30,2**i))
    raise last or RuntimeError("request failed")
