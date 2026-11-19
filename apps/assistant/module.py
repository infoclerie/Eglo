MANIFEST = {
    "code": "assistant",
    "name": "Yapay Zekâ Asistanı",
    "version": "0.1.0",
    "depends": ["core", "integrations"],
    "urls": "apps.assistant.urls",
    "icon": "chart",
    "color": "#c96442",
    "menu": [("Asistana sor", "assistant:index", "chart")],
    "reset_data": [{"label": "Asistan konuşmaları", "desc": "Yapay zekâ asistanına sorulan sorular ve cevaplar.", "models": ["assistant.AssistantMessage"]}],
}
