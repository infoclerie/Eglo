import json
from unittest import mock

from django.contrib.auth.models import Group, User
from django.test import TestCase

from apps.assistant.models import AssistantMessage
from apps.assistant.tools import run_tool, tools_for
from apps.core.roles import ROLES  # noqa: F401
from apps.core.testing.fixtures import ErpFixture
from apps.integrations.models import IntegrationAccount
from apps.integrations.providers.ai import ClaudeClient, OpenAIClient
from apps.sales import services as sales


def resp(body, status=200):
    return mock.Mock(status_code=status, json=lambda: body, text=json.dumps(body))


class AssistantTests(ErpFixture, TestCase):
    def setUp(self):
        self.setup_erp()
        sales.confirm(sales.create_order(self.web, [(self.serum, 3)]))
        self.acc = IntegrationAccount(provider="ai_claude", name="Claude", config={"model": "claude-sonnet-5-5", "kvkk_ok": True, "daily_limit": 3})
        self.acc.set_secrets({"api_key": "sk-test"})
        self.acc.save()
        self.client.force_login(self.boss)

    def claude_flow(self, *a, **k):
        url, body = a[0], k["json"]
        self.calls.append(json.loads(json.dumps(body)))
        if len(self.calls) == 1:  # yapay zekâ veri ister
            return resp({"content": [{"type": "text", "text": "Bakıyorum."},
                                     {"type": "tool_use", "id": "t1", "name": "sales_summary", "input": {"start": "2020-01-01"}}],
                         "stop_reason": "tool_use", "usage": {"input_tokens": 100, "output_tokens": 20}})
        return resp({"content": [{"type": "text", "text": "Bu dönem **1 sipariş** var."}], "stop_reason": "end_turn",
                     "usage": {"input_tokens": 300, "output_tokens": 30}})

    def test_ask_with_tool_call_claude(self):
        self.calls = []
        with mock.patch("apps.integrations.providers.ai.requests.post", side_effect=self.claude_flow) as p:
            r = self.client.post("/assistant/api/sor/", json.dumps({"q": "Bu ay kaç sipariş var?"}), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        ans = r.json()["answer"]
        self.assertEqual((ans["content"], ans["tools"]), ("Bu dönem **1 sipariş** var.", ["satış özeti"]))
        self.assertEqual(p.call_args.kwargs["headers"]["x-api-key"], "sk-test")
        second = self.calls[1]["messages"]
        tool_result = second[-1]["content"][0]
        self.assertEqual(tool_result["type"], "tool_result")
        data = json.loads(tool_result["content"])
        self.assertEqual(data["orders"], 1)
        self.assertNotIn("phone", tool_result["content"])
        m = AssistantMessage.objects.get(role="assistant")
        self.assertEqual((m.tokens_in, m.tokens_out), (400, 50))
        self.assertContains(self.client.get("/assistant/"), "1 sipariş")
        self.assertContains(self.client.get("/"), "Asistana sorun")

    def test_limit_kvkk_and_missing(self):
        self.acc.config["kvkk_ok"] = False
        self.acc.save()
        r = self.client.post("/assistant/api/sor/", json.dumps({"q": "x"}), content_type="application/json")
        self.assertIn("onayı", r.json()["error"])
        self.acc.config["kvkk_ok"] = True
        self.acc.save()
        for _ in range(3):
            AssistantMessage.objects.create(user=self.boss, role="user", content="x")
        r = self.client.post("/assistant/api/sor/", json.dumps({"q": "x"}), content_type="application/json")
        self.assertIn("sınırınız", r.json()["error"])
        self.acc.delete()
        r = self.client.post("/assistant/api/sor/", json.dumps({"q": "x"}), content_type="application/json")
        self.assertIn("kurulmamış", r.json()["error"])

    def test_permissions_limit_tools(self):
        u = User.objects.create_user("depo", password="x" * 12)
        g, _ = Group.objects.get_or_create(name="Depo personeli")
        from django.contrib.auth.models import Permission
        g.permissions.add(Permission.objects.get(codename="view_quant"), Permission.objects.get(codename="add_assistantmessage"))
        u.groups.add(g)
        names = {t["name"] for t in tools_for(u)}
        self.assertIn("product_stock", names)
        self.assertNotIn("receivables", names)
        self.assertIn("yetkiniz yok", run_tool(u, "receivables", {})["error"])
        stock = run_tool(u, "product_stock", {"query": "SRM"})
        self.assertEqual(stock["products"][0]["available"], 97.0)
        self.assertEqual(self.client.get("/assistant/").status_code, 200)

    def test_openai_client_format(self):
        c = OpenAIClient("k", "gpt-5.5", "https://api.openai.com/v1")
        c.start([{"role": "user", "content": "selam"}])
        body = {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "stock_alerts", "arguments": "{\"expiry_days\": 30}"}}]}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
        with mock.patch("apps.integrations.providers.ai.requests.post", return_value=resp(body)) as p:
            res = c.chat("sistem", [{"name": "stock_alerts", "description": "d", "schema": {"type": "object", "properties": {}}}])
        self.assertEqual(p.call_args.args[0], "https://api.openai.com/v1/chat/completions")
        self.assertEqual(res.tool_calls, [{"id": "c1", "name": "stock_alerts", "input": {"expiry_days": 30}}])
        c.add_tool_results([{"id": "c1", "content": "{}"}])
        self.assertEqual(c.history[-1], {"role": "tool", "tool_call_id": "c1", "content": "{}"})
        with mock.patch("apps.integrations.providers.ai.requests.post", return_value=resp({"error": "x"}, 401)):
            from apps.integrations.providers.ai import AIError
            with self.assertRaises(AIError):
                ClaudeClient("k", "m").chat("s", [])

    def test_wizard_requires_kvkk_and_lists_models(self):
        from apps.integrations.providers import get_provider
        p = get_provider("ai_claude")
        with mock.patch.object(ClaudeClient, "models", return_value=["claude-haiku-5-5"]):
            ok, msg = p.test_connection({"model": "claude-sonnet-5-5"}, {"api_key": "k"}, "live")
        self.assertFalse(ok)
        self.assertIn("claude-haiku-5-5", msg)
        r = self.client.post("/integrations/new/ai_claude/settings/?reset=1", {"daily_limit": 10, "max_tokens": 1500})
        self.assertContains(r, "Devam etmek için bu kutuyu işaretleyin")
