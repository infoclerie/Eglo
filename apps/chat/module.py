MANIFEST = {
    "code": "chat",
    "name": "Canlı Sohbet",
    "version": "0.1.0",
    "depends": ["core", "partners"],
    "urls": "apps.chat.urls",
    "icon": "users",
    "color": "#16a34a",
    "menu": [],
    "reset_data": [{'label': 'Sohbet mesajları', 'desc': 'Tüm sohbetler ve mesajlar.', 'models': ['chat.Message', 'chat.Participant', 'chat.Conversation']}],
}
