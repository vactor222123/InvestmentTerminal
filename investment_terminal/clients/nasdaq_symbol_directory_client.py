"""Bounded HTTP client for official Nasdaq Trader symbol directories."""
from urllib.request import Request, urlopen

class NasdaqSymbolDirectoryClient:
    URLS={"NASDAQ_LISTED":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
          "OTHER_LISTED":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"}
    def __init__(self,*,timeout_seconds:float=30.0,opener=None):
        if timeout_seconds<=0:raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds=float(timeout_seconds);self.opener=opener or urlopen
    def fetch(self)->dict[str,bytes]:
        result={}
        for key,url in self.URLS.items():
            request=Request(url,headers={"User-Agent":"InvestmentTerminal/1.0 symbol-directory qualification"})
            try:
                with self.opener(request,timeout=self.timeout_seconds) as response:data=response.read()
            except Exception as exc:raise RuntimeError(f"Nasdaq symbol-directory request failed for {key}") from exc
            if not isinstance(data,bytes) or not data:raise RuntimeError("Nasdaq symbol-directory response is empty")
            result[key]=data
        return result
