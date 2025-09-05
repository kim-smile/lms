from app import create_app

app = create_app()
with app.app_context():
    for r in app.url_map.iter_rules():
        print(f"{r.endpoint:30} -> {r.rule}")