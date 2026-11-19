"""
Yapay zekâ sağlayıcıları (asistan modülü kullanır). Ortak arayüz: AIClient.chat(system, messages, tools) → AIResult.
- Claude (Anthropic): POST {base}/v1/messages  başlık: x-api-key, anthropic-version: 2023-06-01
    araç: tools=[{name, description, input_schema}] → yanıt içerik blokları text / tool_use{id,name,input}
    araç sonucu: user mesajı [{type:"tool_result", tool_use_id, content}]
- OpenAI ve OpenAI uyumlu servisler: POST {base}/v1/chat/completions  başlık: Authorization: Bearer
    araç: tools=[{type:"function", function:{name, description, parameters}}] → message.tool_calls[{id, function{name, arguments}}]
    araç sonucu: {role:"tool", tool_call_id, content}
Model adları sık değişir: bağlantı testi hesabınızdaki modelleri listeler (GET /v1/models).
"""
import json
from dataclasses import dataclass, field

import requests

from . import Field, Provider


class AIError(Exception):
    pass


@dataclass
class AIResult:
    text: str = ""
    tool_calls: list = field(default_factory=list)  # [{"id", "name", "input"}]
    usage: dict = field(default_factory=dict)


def _post(url, headers, body, timeout=90):
    try:
        r = requests.post(url, headers=headers, json=body, timeout=timeout)
    except requests.RequestException as exc:
        raise AIError(f"Yapay zekâ servisine bağlanılamadı: {exc}") from exc
    if r.status_code in (401, 403):
        raise AIError("API anahtarı geçersiz veya yetkisiz (401/403).")
    if r.status_code == 404:
        raise AIError("Model veya adres bulunamadı (404). Ayarlardaki model adını kontrol edin.")
    if r.status_code == 429:
        raise AIError("Yapay zekâ servisi istek / kredi sınırına ulaştı (429). Biraz sonra tekrar deneyin veya bakiyenizi kontrol edin.")
    if r.status_code >= 400:
        raise AIError(f"Yapay zekâ servisi hata verdi (HTTP {r.status_code}): {r.text[:300]}")
    return r.json()


class ClaudeClient:
    def __init__(self, api_key, model, base_url="https://api.anthropic.com", max_tokens=1500):
        self.key, self.model, self.base, self.max_tokens = api_key, model, (base_url or "https://api.anthropic.com").rstrip("/"), max_tokens
        self.history = []

    def _headers(self):
        return {"x-api-key": self.key, "anthropic-version": "2023-06-01", "content-type": "application/json"}

    def start(self, messages):
        self.history = [{"role": m["role"], "content": m["content"]} for m in messages]

    def chat(self, system, tools):
        body = {"model": self.model, "max_tokens": self.max_tokens, "system": system, "messages": self.history,
                "tools": [{"name": t["name"], "description": t["description"], "input_schema": t["schema"]} for t in tools]}
        data = _post(self.base + "/v1/messages", self._headers(), body)
        blocks = data.get("content") or []
        self.history.append({"role": "assistant", "content": blocks})
        res = AIResult(usage={"input": (data.get("usage") or {}).get("input_tokens", 0),
                              "output": (data.get("usage") or {}).get("output_tokens", 0)})
        res.text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        res.tool_calls = [{"id": b["id"], "name": b["name"], "input": b.get("input") or {}} for b in blocks if b.get("type") == "tool_use"]
        return res

    def add_tool_results(self, results):
        self.history.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": r["id"], "content": r["content"]} for r in results]})

    def models(self):
        try:
            r = requests.get(self.base + "/v1/models", headers=self._headers(), timeout=20, params={"limit": 100})
        except requests.RequestException as exc:
            raise AIError(f"Bağlanılamadı: {exc}") from exc
        if r.status_code in (401, 403):
            raise AIError("API anahtarı geçersiz (401/403).")
        if r.status_code >= 400:
            raise AIError(f"HTTP {r.status_code}: {r.text[:200]}")
        return [m.get("id") for m in r.json().get("data", [])]


class OpenAIClient:
    def __init__(self, api_key, model, base_url="https://api.openai.com", max_tokens=1500):
        self.key, self.model, self.base = api_key, model, (base_url or "https://api.openai.com").rstrip("/")
        if self.base.endswith("/v1"):
            self.base = self.base[:-3]
        self.history = []

    def _headers(self):
        return {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

    def start(self, messages):
        self.history = [{"role": m["role"], "content": m["content"]} for m in messages]

    def chat(self, system, tools):
        body = {"model": self.model, "messages": [{"role": "system", "content": system}] + self.history,
                "tools": [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["schema"]}}
                          for t in tools]}
        data = _post(self.base + "/v1/chat/completions", self._headers(), body)
        msg = ((data.get("choices") or [{}])[0]).get("message") or {}
        self.history.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")} | {"role": "assistant"})
        calls = []
        for c in msg.get("tool_calls") or []:
            try:
                args = json.loads(c["function"].get("arguments") or "{}")
            except ValueError:
                args = {}
            calls.append({"id": c["id"], "name": c["function"]["name"], "input": args})
        u = data.get("usage") or {}
        return AIResult(text=(msg.get("content") or "").strip(), tool_calls=calls,
                        usage={"input": u.get("prompt_tokens", 0), "output": u.get("completion_tokens", 0)})

    def add_tool_results(self, results):
        for r in results:
            self.history.append({"role": "tool", "tool_call_id": r["id"], "content": r["content"]})

    def models(self):
        try:
            r = requests.get(self.base + "/v1/models", headers=self._headers(), timeout=20)
        except requests.RequestException as exc:
            raise AIError(f"Bağlanılamadı: {exc}") from exc
        if r.status_code in (401, 403):
            raise AIError("API anahtarı geçersiz (401/403).")
        if r.status_code >= 400:
            raise AIError(f"HTTP {r.status_code}: {r.text[:200]}")
        return sorted(m.get("id") for m in r.json().get("data", []))


COMMON_SETTINGS = [
    Field("daily_limit", "Kişi başı günlük soru sınırı", step="settings", kind="int", default=50,
          help="Maliyeti kontrol etmek için. Her soru servis sağlayıcıya ücretlendirilir."),
    Field("max_tokens", "Cevap uzunluğu sınırı (token)", step="settings", kind="int", default=1500, required=False,
          help="Yaklaşık 1 token ≈ 3-4 karakter. Uzun raporlar için artırabilirsiniz."),
    Field("kvkk_ok", "Soruların ve cevap için gereken iş verilerinin bu yapay zekâ servisine (yurt dışı) gönderileceğini biliyorum",
          step="settings", kind="bool", default=False, required=True,
          help="Müşteri telefon, e-posta ve adresleri hiçbir zaman gönderilmez. KVKK aydınlatma metninizde yurt dışı aktarımı belirtin."),
]


class _AIProvider(Provider):
    category = "ai"
    icon = "chart"
    steps = [("credentials", "Bağlantı bilgileri"), ("test", "Bağlantı testi"), ("settings", "Kullanım ayarları"),
             ("summary", "Özet ve etkinleştir")]
    client_cls = None
    default_base = ""

    def client(self, account=None, config=None, secrets=None):
        if account is not None:
            config, secrets = account.config, account.get_secrets()
        return self.client_cls(secrets.get("api_key", ""), config.get("model", ""), config.get("base_url") or self.default_base,
                               int(config.get("max_tokens") or 1500))

    def test_connection(self, config, secrets, environment):
        try:
            c = self.client(config=config, secrets=secrets)
            ids = c.models()
        except AIError as exc:
            return False, str(exc)
        model = config.get("model", "")
        if ids and model not in ids:
            near = [i for i in ids if any(k in i for k in ("claude", "gpt", "gemini", "llama", "mistral"))][:12] or ids[:12]
            return False, f"Bağlanıldı ama '{model}' modeli hesabınızda yok. Kullanılabilir modeller: {', '.join(near)}"
        return True, f"Bağlanıldı. '{model}' modeli kullanılabilir ({len(ids)} model listelendi)."

    def handle(self, account, job):
        raise ValueError("Yapay zekâ bağlantısı kuyruk işi çalıştırmaz.")


class ClaudeAI(_AIProvider):
    code = "ai_claude"
    name = "Claude (Anthropic)"
    description = "Ana panelde ve asistan ekranında iş verilerinize Türkçe soru sorarsınız: satış, stok, SKT, cari, rapor."
    color = "#c96442"
    client_cls = ClaudeClient
    default_base = "https://api.anthropic.com"
    fields = [
        Field("api_key", "API anahtarı", kind="password", secret=True,
              help="console.anthropic.com › API Keys › Create Key. Hesapta kredi/ödeme tanımlı olmalı."),
        Field("model", "Model", default="claude-sonnet-5-5",
              help="Önerilen: claude-sonnet-5-5 (dengeli). Daha ucuz ve hızlı: claude-haiku-5-5. Bağlantı testi hesabınızdaki modelleri listeler."),
        Field("base_url", "API adresi", default="https://api.anthropic.com", required=False, help="Değiştirmeyin (kurumsal vekil sunucu yoksa)."),
    ] + COMMON_SETTINGS


class OpenAIAI(_AIProvider):
    code = "ai_openai"
    name = "OpenAI (ChatGPT) / uyumlu servis"
    description = "OpenAI veya OpenAI uyumlu bir servisle (ör. Gemini uyumlu uç nokta, kurum içi model) asistan."
    color = "#10a37f"
    client_cls = OpenAIClient
    default_base = "https://api.openai.com"
    fields = [
        Field("api_key", "API anahtarı", kind="password", secret=True, help="platform.openai.com › API keys. Hesapta kredi tanımlı olmalı."),
        Field("model", "Model", default="gpt-5.5",
              help="OpenAI'nin üretim için önerdiği güncel modeli yazın. Bağlantı testi hesabınızdaki modelleri listeler."),
        Field("base_url", "API adresi", default="https://api.openai.com", required=False,
              help="OpenAI için değiştirmeyin. Uyumlu başka servis kullanıyorsanız onun adresini yazın."),
    ] + COMMON_SETTINGS
